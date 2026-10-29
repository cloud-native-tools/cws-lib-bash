#!/usr/bin/env bash
# ============================================================
# git-delta-review.sh — git-delta 驱动的命令行 Code Review 工作流
#
# 目的: 将 "看(diff) → 批(review) → 记(note) → 报(report)" 四步闭环
#       封装为可重复调用的确定性脚本。审查判断由人/LLM 完成,
#       本脚本只负责渲染、记录、汇总等确定性工作。
#
# 依赖: git 必需; delta 仅 diff/review 子命令需要
#       (note/report 无 delta 也可运行, 供 CI/Agent 环境使用)
#
# 输入: 子命令 + 选项 (见 --help)
# 输出: stdout 渲染结果; Review 记录写入 ${REVIEW_DIR}/<branch>-<ts>.md
# ============================================================
set -euo pipefail

SKILL_HOME="${SKILL_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd -P)}"
SKILL_WORKDIR="${SKILL_WORKDIR:-$(pwd -P)}"

REVIEW_DIR="${REVIEW_DIR:-${SKILL_WORKDIR}/.specify/review}"
DELTA_BIN="${DELTA_BIN:-delta}"
GIT_BASE="${GIT_BASE:-main}"
GIT_HEAD="${GIT_HEAD:-HEAD}"
INTERACTIVE=true
WORKTREE=false
DIFF_RANGE="${GIT_BASE}..${GIT_HEAD}"

SEVERITY_LEVELS=(blocking important suggestion nitpick question praise)

RED='\033[0;31m'; YEL='\033[0;33m'; GRN='\033[0;32m'
BLU='\033[0;34m'; CYN='\033[0;36m'; RST='\033[0m'; BLD='\033[1m'

die()  { echo -e "${RED}✗ $*${RST}" >&2; exit 1; }
info() { echo -e "${BLU}ℹ $*${RST}"; }
ok()   { echo -e "${GRN}✓ $*${RST}"; }
warn() { echo -e "${YEL}⚠ $*${RST}"; }

need_git() {
    command -v git >/dev/null || die "git not found"
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "Not a git repository"
}

need_delta() {
    command -v "$DELTA_BIN" >/dev/null || die \
        "delta not found. Install: https://github.com/dandavison/delta (安装与配置见 references/delta-setup.md)"
}

validate_refs() {
    git rev-parse --verify "$GIT_BASE" >/dev/null 2>&1 || die "基准引用不存在: $GIT_BASE (用 --since 指定)"
    git rev-parse --verify "$GIT_HEAD" >/dev/null 2>&1 || die "目标引用不存在: $GIT_HEAD"
}

# 在参数解析后调用: 确定 diff 范围 (ref..ref 或 --worktree 工作区模式)
setup_diff_range() {
    if [[ "$WORKTREE" == "true" ]]; then
        git rev-parse --verify HEAD >/dev/null 2>&1 || die "仓库尚无提交, 无法使用 --worktree"
        DIFF_RANGE="HEAD"
        GIT_BASE="HEAD"
        GIT_HEAD="(working tree)"
    else
        validate_refs
        DIFF_RANGE="${GIT_BASE}..${GIT_HEAD}"
    fi
}

get_changed_files() { git diff --name-only "$DIFF_RANGE" -- "$@"; }
get_diff_stat()     { git diff --stat "$DIFF_RANGE" -- "$@"; }
current_branch()    { git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "detached"; }

changed_line_count() {
    git diff --numstat "$DIFF_RANGE" | awk '{a+=$1; d+=$2} END {print a+d+0}'
}

# 工作区模式下的未跟踪文件 (git diff HEAD 看不到; 排除 .specify/review/ 自身产出)
list_untracked() {
    git ls-files --others --exclude-standard | grep -v '^\.specify/review/' || true
}

warn_untracked() {
    [[ "$WORKTREE" == "true" ]] || return 0
    local untracked; untracked=$(list_untracked)
    [[ -z "$untracked" ]] && return 0
    local n; n=$(echo "$untracked" | wc -l)
    warn "存在 ${n} 个未跟踪文件不在 diff 中 (git diff HEAD 不覆盖):"
    echo "$untracked" | sed 's/^/    [untracked] /'
    info "如需纳入审查: 先 git add -N <file> (intent-to-add) 或提交后再审"
}

# Phase 1 提交粒度守门: >400 行警告, >800 行强烈建议拆分
size_guard() {
    local lines="$1"
    if [[ "$lines" -gt 800 ]]; then
        warn "变更 ${lines} 行 > 800 — Review 质量无法保证, 建议拆分后再审 (references/review-workflow.md §2.1)"
    elif [[ "$lines" -gt 400 ]]; then
        warn "变更 ${lines} 行 > 400 — 建议拆分; 若不可拆, 分多次聚焦单个模块审查"
    fi
}

review_file_path() {
    local branch="${1:-$(current_branch)}"
    local ts="${2:-$(date +%Y%m%d-%H%M%S)}"
    echo "${REVIEW_DIR}/${branch//\//-}-${ts}.md"
}

init_review_file() {
    local file="$1"
    mkdir -p "$REVIEW_DIR"

    # note/report 可在未解析 diff 范围时创建报告 (如无 main 分支):
    # 基准/目标引用不可解析则跳过 diff 概览, 避免 'fatal: bad revision' 噪音
    local stat_block files_block
    if git rev-parse --verify "$GIT_BASE" >/dev/null 2>&1 \
        && git rev-parse --verify "$GIT_HEAD" >/dev/null 2>&1; then
        stat_block=$(get_diff_stat)
        files_block=$(get_changed_files | sed 's/^/- `/;s/$/`/')
    else
        stat_block="(基准 ${GIT_BASE} 或目标 ${GIT_HEAD} 不可解析 — 用 GIT_BASE=<ref> 指定后可重建概览)"
        files_block="$stat_block"
    fi

    cat > "$file" << EOF
# Code Review Report

| 属性 | 值 |
|------|-----|
| **分支** | $(current_branch) |
| **基准** | \`$GIT_BASE\` ($(git rev-parse --short "$GIT_BASE" 2>/dev/null || echo 'N/A')) |
| **目标** | \`$GIT_HEAD\` ($(git rev-parse --short "$GIT_HEAD" 2>/dev/null || echo 'N/A')) |
| **Reviewer** | $(git config user.name 2>/dev/null || echo 'unknown') |
| **日期** | $(date '+%Y-%m-%d %H:%M') |

## 变更概览

\`\`\`
${stat_block}
\`\`\`

## 变更文件

${files_block}

---

## Review 意见

EOF
    ok "Review 文件已创建: $file"
}

severity_icon() {
    case "$1" in
        blocking)   echo "🔴" ;;
        important)  echo "🟠" ;;
        suggestion) echo "🟢" ;;
        nitpick)    echo "⚪" ;;
        question)   echo "❓" ;;
        praise)     echo "👍" ;;
        *)          echo "💡" ;;
    esac
}

is_valid_severity() {
    local s
    for s in "${SEVERITY_LEVELS[@]}"; do [[ "$1" == "$s" ]] && return 0; done
    return 1
}

append_note() {
    local file="$1" severity="$2" filepath="$3" line="${4:-}" comment="$5"
    local icon; icon=$(severity_icon "$severity")

    {
        echo ""
        echo "### ${icon} [${severity^^}] ${filepath}${line:+ (Line ${line})}"
        echo ""
        echo "> ${comment}"
        echo ""
        echo "<sub>$(date '+%H:%M:%S')</sub>"
        echo ""
    } >> "$file"
}

# ─── diff: 渲染人类友好的代码对比 ───────────────────────────
cmd_diff() {
    local mode="full" focus=""
    local extra_args=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --side-by-side|-s) extra_args+=(--side-by-side); shift ;;
            --files|-f)        mode="files"; shift ;;
            --stat)            mode="stat"; shift ;;
            --focus)           focus="$2"; shift 2 ;;
            --since|--base)    GIT_BASE="$2"; shift 2 ;;
            --head)            GIT_HEAD="$2"; shift 2 ;;
            --worktree|-w)     WORKTREE=true; shift ;;
            *)                 extra_args+=("$1"); shift ;;
        esac
    done

    need_git; setup_diff_range
    local paths=(); [[ -n "$focus" ]] && paths=("$focus")
    size_guard "$(changed_line_count)"
    warn_untracked

    case "$mode" in
        files)
            echo -e "${BLD}变更文件列表 (基准: ${GIT_BASE} → ${GIT_HEAD}):${RST}"
            echo ""
            get_changed_files "${paths[@]}" | while read -r f; do
                local adds dels
                adds=$(git diff --numstat "$DIFF_RANGE" -- "$f" | awk '{print $1}')
                dels=$(git diff --numstat "$DIFF_RANGE" -- "$f" | awk '{print $2}')
                printf "  ${GRN}+%-4s${RST} ${RED}-%-4s${RST} %s\n" "$adds" "$dels" "$f"
            done
            ;;
        stat)
            get_diff_stat "${paths[@]}"
            ;;
        full)
            need_delta
            echo -e "${BLD}━━━ Diff: ${GIT_BASE} → ${GIT_HEAD} ${focus:+(聚焦: $focus)} ━━━${RST}"
            echo ""
            git diff "$DIFF_RANGE" -- "${paths[@]}" | "$DELTA_BIN" "${extra_args[@]}"
            ;;
    esac
}

# ─── review: 交互式逐文件 Review (测试文件优先) ─────────────
cmd_review() {
    local focus="" tests_first=true

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --focus)           focus="$2"; shift 2 ;;
            --since|--base)    GIT_BASE="$2"; shift 2 ;;
            --head)            GIT_HEAD="$2"; shift 2 ;;
            --worktree|-w)     WORKTREE=true; shift ;;
            --no-tests-first)  tests_first=false; shift ;;
            --yes|-y)          INTERACTIVE=false; shift ;;
            *)                 shift ;;
        esac
    done

    need_git; need_delta; setup_diff_range
    local paths=(); [[ -n "$focus" ]] && paths=("$focus")
    warn_untracked

    local -a files=()
    mapfile -t files < <(get_changed_files "${paths[@]}")
    [[ ${#files[@]} -eq 0 ]] && { ok "无变更文件，无需 Review"; return; }

    # 审查顺序: 测试代码优先 (测试即规格说明), 见 references/review-workflow.md §3.2
    if [[ "$tests_first" == "true" ]]; then
        local -a test_files=() other_files=()
        local f
        for f in "${files[@]}"; do
            if [[ "$f" =~ (^|/)(tests?|__tests__|spec)/ || "$f" =~ (_test|_spec|Tests?|Spec)\.[^.]+$ || "$f" =~ ^test_ ]]; then
                test_files+=("$f")
            else
                other_files+=("$f")
            fi
        done
        files=(${test_files[@]+"${test_files[@]}"} ${other_files[@]+"${other_files[@]}"})
    fi

    local total=${#files[@]}
    size_guard "$(changed_line_count)"
    info "共 ${total} 个文件待 Review${focus:+ (聚焦: $focus)}"
    echo ""

    local rfile; rfile=$(review_file_path)
    init_review_file "$rfile"

    local idx=0 approved=0 commented=0 filepath
    for filepath in "${files[@]}"; do
        idx=$((idx + 1))
        echo ""
        echo -e "${BLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RST}"
        echo -e "${BLD}  [${idx}/${total}] ${CYN}${filepath}${RST}"
        echo -e "${BLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RST}"
        echo ""

        git diff "$DIFF_RANGE" -- "$filepath" \
            | "$DELTA_BIN" --side-by-side --line-numbers 2>/dev/null \
            || git diff "$DIFF_RANGE" -- "$filepath" | "$DELTA_BIN"

        echo ""

        if [[ "$INTERACTIVE" == "true" ]]; then
            while true; do
                echo -ne "${YEL}  操作 [${RST}a${YEL}]通过 [${RST}c${YEL}]评论 [${RST}s${YEL}]跳过 [${RST}q${YEL}]结束: ${RST}"
                local action
                if ! read -r action; then echo; action="q"; fi

                case "$action" in
                    a|A)
                        approved=$((approved + 1))
                        ok "  已通过"
                        break
                        ;;
                    c|C)
                        echo -ne "  级别 [${RED}b${RST}]locking [${YEL}i${RST}]mportant [${GRN}s${RST}]uggestion [n]itpick [q]uestion [p]raise: "
                        local sev_input severity
                        read -r sev_input || sev_input=""
                        case "$sev_input" in
                            b|B) severity="blocking" ;;
                            i|I) severity="important" ;;
                            s|S) severity="suggestion" ;;
                            n|N) severity="nitpick" ;;
                            q|Q) severity="question" ;;
                            p|P) severity="praise" ;;
                            *)   severity="suggestion" ;;
                        esac

                        echo -ne "  行号 (可选, 回车跳过): "
                        local line_no; read -r line_no || line_no=""
                        echo -ne "  意见: "
                        local comment; read -r comment || comment=""

                        [[ -z "$comment" ]] && { warn "  意见为空，跳过"; continue; }

                        append_note "$rfile" "$severity" "$filepath" "$line_no" "$comment"
                        commented=$((commented + 1))
                        ok "  已记录: [${severity}] ${filepath}${line_no:+:$line_no}"
                        ;;
                    s|S)
                        warn "  已跳过"
                        break
                        ;;
                    q|Q)
                        info "提前结束 Review"
                        break 2
                        ;;
                    *)
                        warn "  无效输入"
                        ;;
                esac
            done
        else
            echo -e "  ${GRN}[auto-approved]${RST}"
            approved=$((approved + 1))
        fi
    done

    {
        echo ""
        echo "---"
        echo ""
        echo "## 统计"
        echo ""
        echo "| 指标 | 数量 |"
        echo "|------|------|"
        echo "| 总文件数 | $total |"
        echo "| 已通过 | $approved |"
        echo "| 有评论 | $commented |"
        echo "| 跳过 | $((total - approved - commented)) |"
        echo ""
        echo "---"
        echo "*Generated by git-delta-review at $(date '+%Y-%m-%d %H:%M:%S')*"
    } >> "$rfile"

    echo ""
    echo -e "${BLD}━━━ Review 完成 ━━━${RST}"
    ok "报告: $rfile"
    info "通过: $approved | 评论: $commented | 总计: $total"
    info "合入门禁: $0 report --summary"
}

# ─── note: 非交互追加一条意见 (供 Agent/CI 调用, 无需 delta) ──
cmd_note() {
    local severity="suggestion" filepath="" line="" comment="" rfile=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --severity|-s) severity="$2"; shift 2 ;;
            --file|-f)     filepath="$2"; shift 2 ;;
            --line|-l)     line="$2"; shift 2 ;;
            --comment|-c)  comment="$2"; shift 2 ;;
            --review-file) rfile="$2"; shift 2 ;;
            *)             shift ;;
        esac
    done

    [[ -z "$comment" ]] && die "--comment is required"
    is_valid_severity "$severity" || die "无效级别: $severity (可选: ${SEVERITY_LEVELS[*]})"
    [[ -z "$filepath" ]] && filepath="(global)"

    if [[ -z "$rfile" ]]; then
        rfile=$(ls -t "$REVIEW_DIR"/*.md 2>/dev/null | head -1 || true)
        if [[ -z "$rfile" ]]; then
            need_git
            rfile=$(review_file_path)
            init_review_file "$rfile"
        fi
    fi

    append_note "$rfile" "$severity" "$filepath" "$line" "$comment"
    ok "已追加: [${severity}] ${filepath}${line:+:$line}"
}

# ─── report: 查看/汇总 Review 报告 ──────────────────────────
#
# 合入门禁判决的唯一来源 (C-26 / FR-023)。判决以显式记录文件为输入:
# `--summary --file <code-review.md>` 的退出码字母表关闭于 0 允许 / 1 拒绝
# (当前记录的 blocking 计数) / 2 输入错误。省略 `--file` 是历史模式,
# 它自标 implicit 且组合路径一律不使用 — 同一特性目录里 `review.md` 与
# `code-review.md` 并存, 隐式选取会把过程报告读成代码段记录并给出假通过。
cmd_report() {
    local action="list" target="" target_explicit=false format="text"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --latest)     action="latest"; shift ;;
            --summary)    action="summary"; shift ;;
            --cat)        action="cat"; target="$2"; target_explicit=true; shift 2 ;;
            --file|-f)    target="$2"; target_explicit=true; shift 2 ;;
            --format)     format="$2"; shift 2 ;;
            *)            shift ;;
        esac
    done
    [[ "$format" == "text" || "$format" == "json" ]] || \
        die2 "无效 --format: $format (可选: text | json)"

    if [[ "$action" == "summary" ]]; then
        local record=""
        if [[ "$target_explicit" == "true" ]]; then
            [[ -f "$target" ]] || die2 "记录不存在: $target (判决要显式记录路径, C-27)"
            record="$target"
        else
            local -a candidates=()
            mapfile -t candidates < <(ls -t "$REVIEW_DIR"/*.md 2>/dev/null || true)
            [[ ${#candidates[@]} -eq 0 ]] && die2 \
                "无可汇总的 Review 记录 (目录: $REVIEW_DIR); 用 --file <path> 指定记录"
            record="${candidates[0]}"
            warn "implicit selection: ${record} (legacy newest-file mode; the composed path always passes --file)"
        fi

        local sev count blocking_count=0 important_count=0
        local -A sev_count=()
        for sev in "${SEVERITY_LEVELS[@]}"; do
            count=$(grep -c "^### .* \[${sev^^}\]" "$record" 2>/dev/null || true)
            count=${count:-0}
            sev_count[$sev]="$count"
            [[ "$sev" == "blocking" ]]  && blocking_count="$count"
            [[ "$sev" == "important" ]] && important_count="$count"
        done

        # C-17 (072): opt-in machine-readable form — record path, the six counts
        # (zeros included), the blocking count and the gate verdict. The text
        # form below and the 0/1/2 exit alphabet are untouched by this branch.
        if [[ "$format" == "json" ]]; then
            printf '{"record":"%s","counts":{"blocking":%s,"important":%s,"suggestion":%s,"nitpick":%s,"question":%s,"praise":%s},"blocking_entries":%s,"gate":"%s"}\n' \
                "$record" \
                "${sev_count[blocking]}" "${sev_count[important]}" "${sev_count[suggestion]}" \
                "${sev_count[nitpick]}" "${sev_count[question]}" "${sev_count[praise]}" \
                "$blocking_count" \
                "$([[ "$blocking_count" -gt 0 ]] && printf 'deny' || printf 'allow')"
        else
            echo -e "${BLD}━━━ Review 汇总: ${record} ━━━${RST}"
            echo ""
            for sev in "${SEVERITY_LEVELS[@]}"; do
                printf "  %s %-12s %s\n" "$(severity_icon "$sev")" "[$sev]" "${sev_count[$sev]}"
            done
            echo ""
            echo "record=$record"
            echo "blocking_entries=${blocking_count}"
        fi
        if [[ "$blocking_count" -gt 0 ]]; then
            [[ "$format" != "json" ]] && echo "gate=deny"
            [[ "$format" != "json" ]] && \
                echo -e "  ${RED}✗ 合入门禁: 存在 ${blocking_count} 条 [blocking] — 必须解决后方可合入${RST}"
            exit 1
        elif [[ "$important_count" -gt 0 ]]; then
            [[ "$format" != "json" ]] && echo "gate=allow"
            [[ "$format" != "json" ]] && \
                echo -e "  ${YEL}⚠ 合入门禁: 存在 ${important_count} 条 [important] — 需逐条回应 (同意/不同意+理由) 后方可合入${RST}"
            return 0
        else
            [[ "$format" != "json" ]] && echo "gate=allow"
            [[ "$format" != "json" ]] && \
                echo -e "  ${GRN}✓ 合入门禁: 无未决 blocking/important — 满足收敛条件${RST}"
            return 0
        fi
    fi

    local -a files=()
    mapfile -t files < <(ls -t "$REVIEW_DIR"/*.md 2>/dev/null || true)
    [[ ${#files[@]} -eq 0 ]] && { warn "无 Review 记录 (目录: $REVIEW_DIR)"; return; }

    case "$action" in
        list)
            echo -e "${BLD}Review 记录列表:${RST}"
            echo ""
            local f notes
            for f in "${files[@]}"; do
                notes=$(grep -c "^### " "$f" 2>/dev/null || true)
                printf "  %s  ${YEL}(%s 条意见)${RST}\n" "$f" "$notes"
            done
            ;;
        latest)
            cat "${files[0]}"
            ;;
        cat)
            [[ -f "$target" ]] || die "文件不存在: $target"
            cat "$target"
            ;;
    esac
    return 0
}

# ══════════════════════════════════════════════════════════════
# 代码段确定性内核: base / triage / start
#
# 三个子命令落在本脚本这一既有实体上 (contracts/code-review-skill.md C-30),
# 不引入新引擎、常驻进程或依赖。它们构成非交互评审路径的前三步
# (第四步 receipt 与汇总裁决由覆盖率回执承担), 见 --help 的 FOUR-STEP 段。
# ══════════════════════════════════════════════════════════════

SPEC_DIR=""             # --spec <feature-dir>
BASE_EXPLICIT=""        # --since / --base
HEAD_EXPLICIT=""        # --head
GIT_TRUNK=""            # --trunk
CODE_PATHS_OVERRIDE=()  # --code-paths <glob[,glob...]>

RESOLVED_BASE=""
RESOLVED_HEAD=""
RESOLVED_BASE_SOURCE=""
RESOLVE_FAIL_REASON=""

# 闭合的默认代码路径集 — 唯一 owner (命令模板只引用, 不复制)。
# "什么算代码路径" 由本集合判定; 调用方可用 --code-paths 整体覆盖。
CODE_PATH_PATTERNS=(
    '*.py' '*.pyi' '*.sh' '*.bash' '*.zsh' '*.js' '*.mjs' '*.cjs' '*.jsx' '*.ts' '*.tsx'
    '*.go' '*.rs' '*.java' '*.kt' '*.kts' '*.rb' '*.php' '*.c' '*.h' '*.cc' '*.cpp' '*.hpp'
    '*.cs' '*.swift' '*.m' '*.mm' '*.scala' '*.ex' '*.exs' '*.lua' '*.pl' '*.sql' '*.proto'
    '*.vue' '*.svelte' '*.dart' '*.zig' '*.nim' '*.hs' '*.ml' '*.clj' '*.cljs'
    'Dockerfile' 'Makefile' 'CMakeLists.txt' '*.cmake' '*.gradle' '*.tf' '*.toml'
)

# 明确不算代码的路径: 规格、文档、记忆与评审产出
NON_CODE_PATH_PATTERNS=(
    '*.md' '*.markdown' '*.txt' '*.rst' '*.adoc'
    'docs/*' '.specify/specs/*' '.specify/memory/*' '.specify/history/*'
    '.specify/templates/*' '.specify/review/*' '.specify/feedback/*'
)

die2() { echo "✗ $*" >&2; exit 2; }

# 运行时间戳: UTC 秒级, 形式 YYYYMMDDTHHMMSSZ (FR-010)。REVIEW_RUN_TIMESTAMP
# 可固定时间戳以确定性驱动 "同秒冲突" 分支 (与 DELTA_BIN 同样是只读替换)。
run_timestamp() { printf '%s' "${REVIEW_RUN_TIMESTAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"; }

git_has_ref() { git rev-parse --verify --quiet "$1" >/dev/null 2>&1; }

# 渲染模式: 两条件规则 (FR-013 / C-22) — 渲染器可用 且 stdout 是交互终端。
# 其余一切情形 (agent / 非交互 / 重定向输出) 取文本模式, 即使渲染器存在。
renderer_marker() {
    local override="${1:-}"
    if [[ -n "$override" ]]; then
        case "$override" in
            delta|rendered)  echo "renderer: delta" ;;
            text|plain)      echo "renderer: text" ;;
            *)               die "无效 renderer: $override (可选: delta | text)" ;;
        esac
        return 0
    fi
    if command -v "$DELTA_BIN" >/dev/null 2>&1 && [[ -t 1 ]]; then
        echo "renderer: delta"
    else
        echo "renderer: text"
    fi
}

# 主干识别: 一条闭合顺序 (FR-004 / C-18), 顺序之外不做猜测。
resolve_trunk() {
    if [[ -n "$GIT_TRUNK" ]]; then
        git_has_ref "$GIT_TRUNK" && { printf '%s' "$GIT_TRUNK"; return 0; }
        return 1
    fi
    if git_has_ref refs/remotes/origin/HEAD; then
        printf '%s' "refs/remotes/origin/HEAD"; return 0
    fi
    local branch
    for branch in main master; do
        git_has_ref "refs/heads/$branch" && { printf '%s' "$branch"; return 0; }
    done
    return 1
}

# 特性切片档的仪器: 首次提交 (C-19) — git log --diff-filter=A -- <spec>/requirements.md,
# 绝不使用 git log -1 over the directory。
resolve_feature_commit() {
    local spec="${1:-}" found
    [[ -n "$spec" ]] || return 1
    found=$(git log --diff-filter=A --format=%H -- "${spec%/}/requirements.md" 2>/dev/null | tail -1)
    [[ -n "$found" ]] || return 1
    printf '%s' "$found"
}

# 解析评审区间并写入 RESOLVED_* ; 无档可解时返回 2 (not-evaluated), 绝不退回猜测。
resolve_range() {
    RESOLVED_BASE=""; RESOLVED_HEAD=""; RESOLVED_BASE_SOURCE=""; RESOLVE_FAIL_REASON=""

    local head
    head=$(resolve_head) || { RESOLVE_FAIL_REASON="head 不可解析 (仓库无提交或 --head 无效)"; return 2; }
    RESOLVED_HEAD="$head"

    if [[ -n "$BASE_EXPLICIT" ]]; then
        if git_has_ref "$BASE_EXPLICIT"; then
            RESOLVED_BASE=$(git rev-parse "$BASE_EXPLICIT")
            RESOLVED_BASE_SOURCE="explicit"
            return 0
        fi
        RESOLVE_FAIL_REASON="显式基准不可解析: $BASE_EXPLICIT"
        RESOLVED_BASE_SOURCE="not-evaluated"
        return 2
    fi

    local feature
    if feature=$(resolve_feature_commit "$SPEC_DIR"); then
        if git_has_ref "${feature}^"; then
            RESOLVED_BASE=$(git rev-parse "${feature}^")
            RESOLVED_BASE_SOURCE="feature-first-commit"
            return 0
        fi
    fi

    local trunk merge
    if trunk=$(resolve_trunk); then
        merge=$(git merge-base "$trunk" "$RESOLVED_HEAD" 2>/dev/null || true)
        if [[ -n "$merge" ]]; then
            RESOLVED_BASE="$merge"
            RESOLVED_BASE_SOURCE="trunk-merge-base"
            return 0
        fi
    fi

    RESOLVED_BASE_SOURCE="not-evaluated"
    RESOLVE_FAIL_REASON="no base tier resolved: no explicit --since, no first-add commit for ${SPEC_DIR:-<spec>}/requirements.md, and no trunk (--trunk / refs/remotes/origin/HEAD / main / master)"
    return 2
}

# head: 显式 --head, 否则运行开始时读一次的 HEAD — 该值在整次运行内不再变 (C-18)。
resolve_head() {
    if [[ -n "$HEAD_EXPLICIT" ]]; then
        git_has_ref "$HEAD_EXPLICIT" || return 1
        git rev-parse "$HEAD_EXPLICIT"
        return 0
    fi
    git rev-parse HEAD 2>/dev/null
}

resolve_command_line() {
    echo "git log --diff-filter=A --format=%H -- ${SPEC_DIR:-<spec-dir>}/requirements.md ; git rev-parse ${HEAD_EXPLICIT:-HEAD} ; git merge-base <trunk> ${HEAD_EXPLICIT:-HEAD}"
}

print_unresolved() {
    echo "base_source=not-evaluated"
    echo "reason=${RESOLVE_FAIL_REASON:-base unresolvable}"
    echo "resolve_command=$(resolve_command_line)"
    exit 2
}

is_code_path() {
    local path="$1" pattern
    if [[ ${#CODE_PATHS_OVERRIDE[@]} -gt 0 ]]; then
        for pattern in "${CODE_PATHS_OVERRIDE[@]}"; do
            [[ "$path" == $pattern ]] && return 0
        done
        return 1
    fi
    for pattern in "${NON_CODE_PATH_PATTERNS[@]}"; do
        [[ "$path" == $pattern ]] && return 1
    done
    for pattern in "${CODE_PATH_PATTERNS[@]}"; do
        [[ "$path" == $pattern ]] && return 0
    done
    return 1
}

changed_files_between() {
    local base="$1" head="$2"
    git diff --name-only "${base}..${head}" 2>/dev/null | while read -r line; do
        [[ -n "$line" ]] && echo "$line"
    done
}

parse_common_opts() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --spec)         SPEC_DIR="$2"; shift 2 ;;
            --since|--base) BASE_EXPLICIT="$2"; shift 2 ;;
            --trunk)        GIT_TRUNK="$2"; shift 2 ;;
            --head)         HEAD_EXPLICIT="$2"; shift 2 ;;
            --code-paths)
                local list="${2//,/ }"
                read -r -a CODE_PATHS_OVERRIDE <<< "$list"
                shift 2
                ;;
            *) die2 "未知选项: $1" ;;
        esac
    done
}

# ─── base: 解析 base / head / base_source ───────────────────
cmd_base() {
    local json=false
    local -a rest=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --json) json=true; shift ;;
            *) rest+=("$1"); shift ;;
        esac
    done
    [[ ${#rest[@]} -gt 0 ]] && parse_common_opts "${rest[@]}"

    need_git
    local rc=0
    resolve_range || rc=$?
    [[ "$rc" -ne 0 ]] && print_unresolved

    if [[ "$json" == "true" ]]; then
        printf '{"base":"%s","head":"%s","base_source":"%s"}\n' \
            "$RESOLVED_BASE" "$RESOLVED_HEAD" "$RESOLVED_BASE_SOURCE"
    else
        echo "base=$RESOLVED_BASE"
        echo "head=$RESOLVED_HEAD"
        echo "base_source=$RESOLVED_BASE_SOURCE"
    fi
}

# ─── triage: 代码段适用性 (三值封闭, 空 delta 先答) ──────────
cmd_triage() {
    parse_common_opts "$@"
    need_git

    local rc=0
    resolve_range || rc=$?
    if [[ "$rc" -ne 0 ]]; then
        echo "triage=not-evaluated"
        echo "reason=${RESOLVE_FAIL_REASON:-base unresolvable}"
        echo "resolve_command=$(resolve_command_line)"
        exit 2
    fi

    local -a files=()
    mapfile -t files < <(changed_files_between "$RESOLVED_BASE" "$RESOLVED_HEAD")

    echo "base=$RESOLVED_BASE"
    echo "head=$RESOLVED_HEAD"
    echo "base_source=$RESOLVED_BASE_SOURCE"
    echo "changed_files=${#files[@]}"

    # 空 delta 在回执运行之前就答 (V30): 0/0/0 的回执永远不是干净评审
    if [[ ${#files[@]} -eq 0 ]]; then
        echo "triage=not-applicable"
        echo "basis=no committed code delta"
        return 0
    fi

    local -a code=()
    local file
    for file in "${files[@]}"; do
        is_code_path "$file" && code+=("$file")
    done

    if [[ ${#code[@]} -eq 0 ]]; then
        echo "triage=not-applicable"
        echo "basis=no code deliverable: the committed delta contains no code path"
        return 0
    fi

    echo "triage=run"
    echo "basis=code path in the committed delta: ${code[*]}"
}

# ─── start: 记录创建与轮转 (单一表头形态) ────────────────────
write_code_segment_record() {
    local record="$1" marker="$2" stamp="$3"
    local base_short head_short reviewer branch run_date
    base_short=$(git rev-parse --short "$RESOLVED_BASE" 2>/dev/null || echo 'N/A')
    head_short=$(git rev-parse --short "$RESOLVED_HEAD" 2>/dev/null || echo 'N/A')
    reviewer=$(git config user.name 2>/dev/null || echo 'unknown')
    branch=$(current_branch)
    run_date="${stamp:0:4}-${stamp:4:2}-${stamp:6:2}T${stamp:9:2}:${stamp:11:2}:${stamp:13:2}Z"

    cat > "$record" << EOF
# Code Review Report — 代码段 (code segment)

| 属性 | 值 |
|------|-----|
| **分支** | \`${branch}\` |
| **基准** | \`${RESOLVED_BASE}\` (\`${base_short}\`) |
| **目标** | \`${RESOLVED_HEAD}\` (\`${head_short}\`) |
| **基准来源** | \`${RESOLVED_BASE_SOURCE}\` |
| **渲染模式** | \`${marker}\` |
| **Reviewer** | \`${reviewer}\` |
| **日期** | \`${run_date}\` |

## 变更概览

\`\`\`
$(git diff --stat "${RESOLVED_BASE}..${RESOLVED_HEAD}" 2>/dev/null || echo '(range unusable)')
\`\`\`

---

## Review 意见

EOF
}

cmd_start() {
    local triage_value="run" renderer_override=""
    local -a rest=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --triage)   triage_value="$2"; shift 2 ;;
            --renderer) renderer_override="$2"; shift 2 ;;
            *) rest+=("$1"); shift ;;
        esac
    done
    [[ ${#rest[@]} -gt 0 ]] && parse_common_opts "${rest[@]}"

    need_git
    [[ -n "$SPEC_DIR" ]] || die "start 需要 --spec <feature-dir>"

    # 记录存在性按适用性分工 (C-11 / V29): 只有 run 写记录
    if [[ "$triage_value" != "run" ]]; then
        echo "refused: triage=$triage_value" >&2
        echo "no record is created for a triage value other than run (C-11 / data-model V29)" >&2
        exit 2
    fi

    local rc=0
    resolve_range || rc=$?
    [[ "$rc" -ne 0 ]] && print_unresolved

    local marker stamp record archive="none" archive_target
    marker=$(renderer_marker "$renderer_override")
    stamp=$(run_timestamp)
    record="${SPEC_DIR%/}/code-review.md"
    mkdir -p "${SPEC_DIR%/}"

    if [[ -f "$record" ]]; then
        archive_target="${SPEC_DIR%/}/code-review-${stamp}.md"
        if [[ -e "$archive_target" ]]; then
            echo "refused: archive collision at $archive_target" >&2
            echo "an existing archive is never overwritten; wait for the next second or re-run (V12)" >&2
            exit 2
        fi
        mv "$record" "$archive_target"
        archive="$archive_target"
    fi

    write_code_segment_record "$record" "$marker" "$stamp"
    ok "代码段记录已创建: $record"
    echo "record=$record"
    echo "archive=$archive"
    echo "base=$RESOLVED_BASE"
    echo "head=$RESOLVED_HEAD"
    echo "base_source=$RESOLVED_BASE_SOURCE"
    echo "renderer=${marker#renderer: }"
}

# ══════════════════════════════════════════════════════════════
# receipt: 覆盖率回执与段裁决 (非交互路径第 4 步)
#
# 回执是"已读全 diff"的唯一证据形态 (FR-015 / C-25), 也是四项计数
# (changed / judged / skipped / gap) 的唯一来源 (C-74): 过程报告的代码段
# 小节与特性详情评审记录条目逐字段抄它, 不重算、不再聚合。
#
# 退出码字母表在 0/1/2 处封闭 (FR-014 / C-34 / C-35), 每个码只有一个含义:
#   0 = 完整 (文件集相等且逐文件都有裁决, 含带理由跳过)
#   1 = 覆盖缺口 (有文件缺裁决、两文件集不等, 或跳过了不被识别的理由)
#   2 = 不可评估 (base/head 不可解析、记录缺失、仓库状态不可用) — 不写块
# 1 与 2 MUST NOT 互换: 前者是"评审有缺口", 后者是"这次没法评"。
# ══════════════════════════════════════════════════════════════

RECEIPT_BEGIN_LITERAL='<!-- coverage-receipt:begin -->'
RECEIPT_END_LITERAL='<!-- coverage-receipt:end -->'
RECEIPT_VERSION=1

# 闭合法定跳过理由集 — 唯一 owner: requirements.md FR-014。
# 本脚本是执行者; 契约测试从 owner 逐值读取并驱动本脚本, 因此两份清单
# 的漂移会在测试里变红, 而不是在评审里静默放行 (C-36)。
SKIP_REASONS_LEGAL=(
    non-code-file
    generated
    binary
    out-of-scope-per-explicit-user-ruling
    size-guard-focus-not-reviewed
)

is_legal_skip_reason() {
    local candidate
    for candidate in "${SKIP_REASONS_LEGAL[@]}"; do
        [[ "$1" == "$candidate" ]] && return 0
    done
    return 1
}

# 读回记录里已有回执块携带的逐文件裁决 (verdict<TAB>path<TAB>reason)。
# 逐文件裁决是"携带"而非"重算": 已有块里的条目就是已评审集, 因此删掉一条
# 再跑, 该文件就是缺口 (SC-002 的 gap drill); 而首次写入前没有块, 本次调用
# 本身即"已读"的断言, 变更集整体成为已评审集。
read_carried_entries() {
    local file="$1"
    [[ -f "$file" ]] || return 0
    awk -v begin="$RECEIPT_BEGIN_LITERAL" -v end="$RECEIPT_END_LITERAL" '
        $0 == begin { inb = 1; next }
        $0 == end   { inb = 0; next }
        inb && /^file\.[0-9]+\.path=/ {
            v = $0; sub(/^file\.[0-9]+\.path=/, "", v)
            split($0, parts, ".")
            path[parts[2]] = v; next
        }
        inb && /^file\.[0-9]+\.verdict=/ {
            v = $0; sub(/^file\.[0-9]+\.verdict=/, "", v)
            split($0, parts, "."); verdict[parts[2]] = v; next
        }
        inb && /^file\.[0-9]+\.reason=/ {
            v = $0; sub(/^file\.[0-9]+\.reason=/, "", v)
            split($0, parts, "."); reason[parts[2]] = v; next
        }
        END {
            for (key in path) printf "%s\t%s\t%s\n", verdict[key], path[key], reason[key]
        }
    ' "$file"
}

# 把记录头部的渲染模式标记改成本次运行实际使用的模式 (C-40 / V15):
# 标记与块由同一次调用写出, 两者不可能漂成不一致。
set_record_renderer() {
    local file="$1" mode="$2" tmp
    [[ -f "$file" ]] || return 0
    tmp="$(mktemp "${file}.renderer.XXXXXX")"
    awk -v marker="renderer: $mode" '
        done == 0 && ($0 ~ /渲染模式/ || $0 ~ /[Rr]enderer mode/) {
            n = split($0, cells, "|")
            if (n >= 4) {
                $0 = cells[1] "|" cells[2] "| `" marker "` |"
                done = 1
            }
        }
        { print }
    ' "$file" > "$tmp"
    mv "$tmp" "$file"
}

# 用新块替换旧块 (旧块整段删除, 新块追加在末尾), 并同时替换未提交范围披露行。
# 同一仓库状态跑两次得到同一个块 — 定界与逐文件行都是确定性的 (C-33)。
write_receipt_block() {
    local file="$1" block="$2" disclosure="${3:-}" tmp
    tmp="$(mktemp "${file}.receipt.XXXXXX")"
    awk -v begin="$RECEIPT_BEGIN_LITERAL" -v end="$RECEIPT_END_LITERAL" '
        $0 == begin { inb = 1; next }
        $0 == end   { inb = 0; next }
        inb { next }
        /^> \*\*未提交范围/ { next }
        { print }
    ' "$file" > "$tmp"
    if [[ -n "$disclosure" ]]; then
        printf '\n%s\n' "$disclosure" >> "$tmp"
    fi
    printf '\n%s\n' "$block" >> "$tmp"
    mv "$tmp" "$file"
}

# 未提交范围: 运行自身的产物不算评审对象, 因此排除本流程写出的记录/归档与
# `.specify/review/`; 其余一切未提交改动都要披露 (C-44 / FR-005)。
uncommitted_scope() {
    git status --porcelain 2>/dev/null \
        | grep -vE '^\?\? \.specify/review/|code-review(-[0-9]{8}T[0-9]{6}Z)?\.md$' \
        || true
}

cmd_receipt() {
    local review_file="" renderer_override="" block=""
    local -a skip_globs=() skip_reasons=() rest=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --review-file)      review_file="$2"; shift 2 ;;
            --renderer)         renderer_override="$2"; shift 2 ;;
            --skip-with-reason) skip_globs+=("$2"); skip_reasons+=(""); shift 2 ;;
            --reason)
                [[ ${#skip_globs[@]} -gt 0 ]] || \
                    die2 "--reason 必须跟在它的 --skip-with-reason 选择器之后"
                skip_reasons[$(( ${#skip_globs[@]} - 1 ))]="$2"
                shift 2
                ;;
            *) rest+=("$1"); shift ;;
        esac
    done
    [[ ${#rest[@]} -gt 0 ]] && parse_common_opts "${rest[@]}"

    if [[ -n "$renderer_override" ]]; then
        case "$renderer_override" in
            delta|rendered|text|plain) ;;
            *) die2 "无效 renderer: $renderer_override (可选: delta | text)" ;;
        esac
    fi

    need_git
    [[ -n "$review_file" ]] || \
        die2 "receipt 需要 --review-file <code-review.md>: 不按目录内最新文件隐式选取 (C-27 / FR-023)"
    [[ -f "$review_file" ]] || \
        die2 "记录不存在: $review_file (先跑 start 创建/轮转记录)"

    local rc=0
    resolve_range || rc=$?
    [[ "$rc" -ne 0 ]] && print_unresolved          # 退出 2, 不写块

    local -a changed=()
    mapfile -t changed < <(changed_files_between "$RESOLVED_BASE" "$RESOLVED_HEAD")

    # 空 delta 在回执之前就由 triage 答为 not-applicable (FR-003 / V30 / C-38):
    # 一块 0/0/0 的回执永远不是"干净的评审"。
    if [[ ${#changed[@]} -eq 0 ]]; then
        echo "receipt=refused" >&2
        echo "empty delta: base 与 head 指向同一提交、零变更文件 — 适用性在回执之前判为 not-applicable (STR-001), 回执不写块 (FR-003 / V30)" >&2
        exit 2
    fi

    mapfile -t changed < <(printf '%s\n' "${changed[@]}" | LC_ALL=C sort)

    # 行数是量测值: 测不出来就不写块, 绝不写 0 也不估算 (C-41 / V16)
    local lines_added=0 lines_deleted=0 stat_a stat_d stat_rest
    while IFS=$'\t' read -r stat_a stat_d stat_rest; do
        [[ -z "${stat_a:-}" ]] && continue
        if [[ "$stat_a" == "-" || "$stat_d" == "-" ]]; then
            echo "行数无法测量 (binary): ${stat_rest:-?}" >&2
            echo "不可量测的数字字段意味着不写块 (C-41 / V16)" >&2
            exit 2
        fi
        lines_added=$(( lines_added + stat_a ))
        lines_deleted=$(( lines_deleted + stat_d ))
    done < <(git diff --numstat "${RESOLVED_BASE}..${RESOLVED_HEAD}")

    local has_block=false
    if grep -qxF "$RECEIPT_BEGIN_LITERAL" "$review_file" 2>/dev/null; then
        has_block=true
    fi

    local -A carried_verdict=() carried_reason=()
    if [[ "$has_block" == "true" ]]; then
        local carried_v carried_p carried_r
        while IFS=$'\t' read -r carried_v carried_p carried_r; do
            [[ -z "$carried_p" ]] && continue
            carried_verdict["$carried_p"]="$carried_v"
            carried_reason["$carried_p"]="$carried_r"
        done < <(read_carried_entries "$review_file")
    fi

    local -a row_path=() row_verdict=() row_reason=()
    local path index selector verdict reason selected
    for path in "${changed[@]}"; do
        verdict=""; reason=""; selected=false
        for index in "${!skip_globs[@]}"; do
            selector="${skip_globs[$index]}"
            [[ -z "$selector" ]] && continue
            # shellcheck disable=SC2053  # 选择器是调用方给的 glob, 故意不加引号
            if [[ "$path" == $selector ]]; then
                selected=true
                reason="${skip_reasons[$index]}"
                # 未识别的理由不是合法跳过, 而是覆盖缺口 (FR-014 / C-36 / V34)
                if is_legal_skip_reason "$reason"; then
                    verdict="skipped"
                fi
                break
            fi
        done
        if [[ "$selected" != "true" ]]; then
            if [[ -n "${carried_verdict[$path]:-}" ]]; then
                if [[ "${carried_verdict[$path]}" == "skipped" ]]; then
                    if is_legal_skip_reason "${carried_reason[$path]:-}"; then
                        verdict="skipped"
                        reason="${carried_reason[$path]}"
                    fi
                else
                    verdict="reviewed"
                fi
            elif [[ "$has_block" == "false" ]]; then
                verdict="reviewed"      # 首次写入: 本次调用即"已读"的断言
            fi
        fi
        if [[ -n "$verdict" ]]; then
            row_path+=("$path")
            row_verdict+=("$verdict")
            row_reason+=("$reason")
        fi
    done

    local changed_files=${#changed[@]} judged_files=0 skipped_files=0 gap_files
    for index in "${!row_path[@]}"; do
        case "${row_verdict[$index]}" in
            reviewed) judged_files=$(( judged_files + 1 )) ;;
            skipped)  skipped_files=$(( skipped_files + 1 )) ;;
        esac
    done
    gap_files=$(( changed_files - judged_files - skipped_files ))

    # 渲染模式: 两条件规则 (渲染器可用 且 stdout 是交互终端), 否则文本模式 (C-22)
    local marker mode
    marker=$(renderer_marker "$renderer_override")
    mode="${marker#renderer: }"
    set_record_renderer "$review_file" "$mode"

    # 第三个信号是存在性判定: 只读当前记录里的 blocking 标题, 没有"已清除"状态 (C-38 / V35)
    local blocking_entries
    blocking_entries=$(grep -cE '^### .*\[BLOCKING\]' "$review_file" 2>/dev/null || true)
    blocking_entries=${blocking_entries:-0}

    local segment_verdict
    if [[ "$gap_files" -gt 0 ]]; then
        segment_verdict="not-evaluated"          # 缺口不是结论 (E9)
    elif [[ "$blocking_entries" -gt 0 ]]; then
        segment_verdict="blocked"
    elif [[ "$skipped_files" -gt 0 ]]; then
        segment_verdict="not-evaluated"          # 跳过不计覆盖信用 (C-37)
    else
        segment_verdict="pass"
    fi

    local -a dirty=()
    mapfile -t dirty < <(uncommitted_scope)
    local dirty_count=${#dirty[@]}
    local disclosure=""
    if [[ "$dirty_count" -gt 0 ]]; then
        local dirty_list="" entry
        for entry in "${dirty[@]}"; do
            [[ -z "$entry" ]] && continue
            if [[ -n "$dirty_list" ]]; then dirty_list+=", "; fi
            dirty_list+="${entry:3}"
        done
        disclosure="> **未提交范围（未评审）**: ${dirty_count} 个未提交路径未计入本次评审对象（${dirty_list}）；本回执不对该范围给出任何结论。"
    fi

    local width=${#row_path[@]}
    width=${#width}
    if [[ "$width" -lt 2 ]]; then width=2; fi

    block=$(
        echo "$RECEIPT_BEGIN_LITERAL"
        echo "receipt_version=${RECEIPT_VERSION}"
        echo "base=${RESOLVED_BASE}"
        echo "head=${RESOLVED_HEAD}"
        echo "base_source=${RESOLVED_BASE_SOURCE}"
        echo "renderer=${mode}"
        echo "changed_files=${changed_files}"
        echo "judged_files=${judged_files}"
        echo "skipped_files=${skipped_files}"
        echo "gap_files=${gap_files}"
        echo "lines_added=${lines_added}"
        echo "lines_deleted=${lines_deleted}"
        local index ordinal token
        for index in "${!row_path[@]}"; do
            ordinal=$(( index + 1 ))
            token=$(printf "%0${width}d" "$ordinal")
            echo "file.${token}.path=${row_path[$index]}"
            echo "file.${token}.verdict=${row_verdict[$index]}"
            if [[ "${row_verdict[$index]}" == "skipped" ]]; then
                echo "file.${token}.reason=${row_reason[$index]}"
            fi
        done
        echo "$RECEIPT_END_LITERAL"
    )

    write_receipt_block "$review_file" "$block" "$disclosure"

    ok "覆盖率回执已写入: $review_file"
    echo "base=$RESOLVED_BASE"
    echo "head=$RESOLVED_HEAD"
    echo "base_source=$RESOLVED_BASE_SOURCE"
    echo "renderer=$mode"
    echo "changed_files=$changed_files"
    echo "judged_files=$judged_files"
    echo "skipped_files=$skipped_files"
    echo "gap_files=$gap_files"
    echo "lines_added=$lines_added"
    echo "lines_deleted=$lines_deleted"
    echo "blocking_entries=$blocking_entries"
    echo "verdict=$segment_verdict"
    [[ "$dirty_count" -gt 0 ]] && echo "uncommitted_scope=$dirty_count"
    echo "record=$review_file"
    echo ""
    printf '%s\n' "$block"

    if [[ "$gap_files" -gt 0 ]]; then
        exit 1
    fi
    return 0
}


# ══════════════════════════════════════════════════════════════
# capture: 客户采集 (非交互路径第 5 步, capture-step 契约 C-11…C-24)
#
# 触发是合取 (C-12): 帽子判据判本仓为客户项目 (owner 判据只读, C-13), 且
# 适用性取值为 run。每一情形恰好一行结论 (C-22), 状态符取自五值闭集
# (client-channel-armed / client-channel-unarmed / client-unit-ambiguous /
# no-capture-object / counts-unavailable); 框架帽走 skipped 行, 不混五值。
# 三条不变量 (C-19): 幂等 ((unit, run) 键交给引擎答重复)、非阻断 (本步恒
# 退出 0)、不越权 (不改记录、不改回执块、不触发传输)。非采集情形零条目
# (C-23), 不以"本次无发现"替代具名原因。
#
# 武装态解析 (本特性唯一解析器, C-9/C-62): 只从探针引擎机读输出解析一次,
# 全程复用 (C-2)。解析顺序: 调用方显式单元 > 唯一外部探针 > 其余 (C-2);
# 显式单元只消解歧义, 不豁免探针存在性检查 (C-3)。零探针 / 显式单元无探针 /
# 注册表不可用三情形归未武装且完全不发起 record 调用 (C-3/C-4); 多探针未
# 指定归歧义, 不猜不轮流不取最近使用 (C-5)。畸形 --unit 值产出一条具名
# skip 行 (指名期望语法) 后照常评审, 零条目 (C-6); /speckit.* 与 skill:
# 词族同样在该语法门被拒, 永不到达引擎 (C-7)。
# ══════════════════════════════════════════════════════════════

FRAMEWORK_HAT_DIRS=(templates skills shared scripts src/specify_cli)
HAT_OWNER=".specify/shared/definitions/dogfooding-definitions.md § 2.1"
CAPTURE_POINT="pointer payload assembled from 'report --summary --format json'; no review bodies, per-file verdict lists, or file counts (C-15)"

#: 客户单元值语法, 与反馈/探针引擎的 _CUSTOM_UNIT_RE 同源闭合 (C-6/C-7)。
CUSTOM_UNIT_GRAMMAR="custom:<owner>/<name>"

repo_root_dir() {
    git rev-parse --show-toplevel 2>/dev/null || pwd -P
}

# 帽子判定: 只读 owner 判据 (dogfooding-definitions § 2.1 的五个框架源目录,
# feedback/ 不参与)。客户仓 vendored 框架源同样判 framework (C-13)。
hat_of_root() {
    local root="$1" d
    for d in "${FRAMEWORK_HAT_DIRS[@]}"; do
        [[ -d "$root/$d" ]] && { printf 'framework'; return 0; }
    done
    printf 'client'
}

# 运行标识: 记录头日期戳 (ISO-8601 UTC 秒级, 与归档名同源的 stamp);
# 头部缺行时退回本脚本既有的 REVIEW_RUN_TIMESTAMP 环境变量覆写 (C-18)。
run_id_from_record() {
    local file="$1" stamp
    stamp=$(sed -n 's/^| \*\*日期\*\* | `\([^`]*\)` |$/\1/p' "$file" 2>/dev/null | head -1)
    printf '%s' "${stamp:-$(run_timestamp)}"
}

# 外部探针事实: 只从探针引擎机读输出解析 (C-9)。输出三态首行:
#   unavailable            — 注册表不可用 (引擎缺失或 available=false)
#   0                      — 注册表可用, 零外部探针
#   <n> + 后续行 = 单元名  — n 个外部探针对象及其单元
probe_facts() {
    local root="$1" putils="$root/.specify/scripts/python/probe-utils.py"
    [[ -f "$putils" ]] || { echo "unavailable"; return 0; }
    python3 "$putils" --action probes --format json 2>/dev/null | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print("unavailable"); raise SystemExit(0)
if not d.get("available"):
    print("unavailable"); raise SystemExit(0)
units = sorted(str(o.get("unit", "")) for o in d.get("objects", [])
               if str(o.get("object_id", "")).startswith("ext-"))
print(len(units))
for u in units:
    print(u)
' || echo "unavailable"
}

capture_payload() {
    local record="$1" triage_value="$2" run_id="$3" unit="$4"
    shift 4
    printf 'record=%s\ntriage=%s\n%s\nrun=%s\nunit=%s' \
        "$record" "$triage_value" "$1" "$run_id" "$unit"
}

cmd_capture() {
    local review_file="" triage_value="" unit=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --review-file) review_file="$2"; shift 2 ;;
            --triage)      triage_value="$2"; shift 2 ;;
            --unit)        unit="$2"; shift 2 ;;
            *)             die2 "未知选项: $1" ;;
        esac
    done
    if [[ -z "$review_file" || -z "$triage_value" ]]; then
        die2 "capture 需要 --review-file <code-review.md> --triage <run|not-applicable|not-evaluated> [--unit <custom:owner/name>]"
    fi

    local root; root=$(repo_root_dir)

    # C-13: 框架帽不采集, 披露不混入五值闭集。
    local hat; hat=$(hat_of_root "$root")
    if [[ "$hat" == "framework" ]]; then
        echo "capture: skipped hat=framework basis=root owns framework source directories (.specify/templates/skills/shared/scripts/src/specify_cli); owner=${HAT_OWNER}; triage=${triage_value}"
        return 0
    fi

    # C-14/C-23: 非 run 适用性没有记录可指向 — 具名披露, 零条目。
    if [[ "$triage_value" != "run" ]]; then
        echo "capture: no-capture-object triage=${triage_value} reason=no record exists for applicability '${triage_value}' — nothing to point at (C-14); zero entries"
        return 0
    fi

    # C-6/C-7: 值语法闭合于 custom:<owner>/<name> (与引擎 _CUSTOM_UNIT_RE 同源
    # 的字符集, owner/name 均非空)。畸形值与 /speckit.*、skill: 词族产出
    # 一条具名 skip 行, 零条目, 不阻断评审。
    if [[ -n "$unit" ]]; then
        if [[ ! "$unit" =~ ^custom:[a-z0-9._-]+/[a-z0-9._-]+$ ]]; then
            echo "capture: skipped unit='${unit}' reason=malformed client unit — expected grammar '${CUSTOM_UNIT_GRAMMAR}' (C-6); /speckit.<command> and skill:<name> families are rejected for client findings (C-7); triage=${triage_value}; zero entries"
            return 0
        fi
    fi

    # C-9/C-2: 武装态唯一解析器 — 探针机读输出只解析一次, 全程复用。
    local -a facts=()
    mapfile -t facts < <(probe_facts "$root")
    local registry_state="${facts[0]:-unavailable}"
    local ext_count=0
    [[ "$registry_state" != "unavailable" ]] && ext_count="$registry_state"

    local unit_source=""
    if [[ -n "$unit" ]]; then
        # C-2/C-3: 显式单元优先, 但只消解歧义、不豁免探针存在性检查。
        unit_source="explicit"
        if [[ "$registry_state" == "unavailable" ]]; then
            echo "capture: client-channel-unarmed triage=${triage_value} unit=${unit} reason=probe registry unavailable (un-upgraded .specify/ runtime); guidance=re-initialize/upgrade .specify/ (C-4); zero entries"
            return 0
        fi
        local probe_unit matched=false
        for probe_unit in "${facts[@]:1}"; do
            [[ "$probe_unit" == "$unit" ]] && matched=true
        done
        if [[ "$matched" != "true" ]]; then
            echo "capture: client-channel-unarmed triage=${triage_value} unit=${unit} reason=specified unit has no external probe object in this client project; guidance=arm the channel via 'probe-utils.py --action probe-inject --unit ${unit}' for that unit (C-3); zero entries"
            return 0
        fi
    else
        if [[ "$registry_state" == "unavailable" ]]; then
            echo "capture: client-channel-unarmed triage=${triage_value} reason=probe registry unavailable (un-upgraded .specify/ runtime); guidance=re-initialize/upgrade .specify/ (C-4); zero entries"
            return 0
        fi
        if [[ "$ext_count" == "0" ]]; then
            echo "capture: client-channel-unarmed triage=${triage_value} reason=no external probe object in this client project; guidance=arm the channel via 'probe-utils.py --action probe-inject --unit ${CUSTOM_UNIT_GRAMMAR}'; zero entries"
            return 0
        fi
        if [[ "$ext_count" != "1" ]]; then
            echo "capture: client-unit-ambiguous triage=${triage_value} reason=${ext_count} external probe objects and no explicit --unit — no guessing, no rotation, no most-recently-used (C-5); zero entries"
            return 0
        fi
        unit="${facts[1]}"
        unit_source="auto:unique-external-probe"
    fi

    # C-17/C-21: 计数只从汇总命令的机读形态取; 退出 2 = 输入不可解析。
    local summary_json summary_rc=0
    summary_json=$("$0" report --summary --file "$review_file" --format json 2>/dev/null) || summary_rc=$?
    if [[ "$summary_rc" -eq 2 || -z "$summary_json" ]]; then
        echo "capture: counts-unavailable triage=${triage_value} reason=summary exited ${summary_rc} for ${review_file} (input unparseable — counts never zero-filled, C-21); zero entries"
        return 0
    fi

    # C-16: 六项计数逐项抄录, 含零值, 不重算不估算。
    local counts
    counts=$(printf '%s\n' "$summary_json" | python3 -c '
import json, sys
d = json.load(sys.stdin)
c = d["counts"]
order = ("blocking", "important", "suggestion", "nitpick", "question", "praise")
print("\n".join(f"{k}={c[k]}" for k in order))
' 2>/dev/null) || counts=""
    if [[ -z "$counts" ]]; then
        echo "capture: counts-unavailable triage=${triage_value} reason=summary JSON not machine-readable for ${review_file} (C-21); zero entries"
        return 0
    fi

    # C-18: 运行标识 = 记录头日期戳。
    local run_id; run_id=$(run_id_from_record "$review_file")

    # C-11/C-15: 单条指针条目, 字段集封闭; 引擎的 (unit, run) 键答重复 (C-18)。
    local futils="$root/.specify/scripts/python/feedback-utils.py"
    if [[ ! -f "$futils" ]]; then
        echo "capture: counts-unavailable triage=${triage_value} reason=feedback engine not installed at $futils; zero entries"
        return 0
    fi
    local payload record_out record_rc=0 entry_id
    payload=$(capture_payload "$review_file" "$triage_value" "$run_id" "$unit" "$counts")
    record_out=$(python3 "$futils" --action record \
        --unit-id "$unit" --unit-type custom-unit --run-id "$run_id" \
        --review "$payload" --points "$CAPTURE_POINT" --format json 2>/dev/null) || record_rc=$?
    if [[ "$record_rc" -ne 0 || -z "$record_out" ]]; then
        echo "capture: counts-unavailable triage=${triage_value} reason=feedback engine refused the write (rc=${record_rc}) — review run not blocked, the optionality red line outranks capture (C-21); zero entries"
        return 0
    fi
    entry_id=$(printf '%s\n' "$record_out" | python3 -c \
        'import json, sys; print(json.load(sys.stdin).get("id", ""))' 2>/dev/null || true)

    echo "capture: client-channel-armed triage=${triage_value} unit=${unit} run=${run_id} entry=${entry_id} unit_source=${unit_source}"
    return 0
}


usage() {
    cat << 'EOF'

  git-delta-review — git-delta 驱动的命令行 Code Review 工作流
  (看 → 批 → 记 → 报 四步闭环; 方法论见 references/review-workflow.md)

  USAGE:
    git-delta-review.sh <command> [options]

  COMMANDS:
    diff      渲染人类友好的代码对比 (git-delta 核心能力)
              --side-by-side | --files | --stat | --focus <path> | --since <ref> | --head <ref>
              --worktree/-w: 审查未提交改动 (HEAD vs 工作区, 含已暂存+未暂存)
    review    交互式逐文件 Review (测试文件优先; --yes 非交互; --no-tests-first 关闭排序)
    note      非交互追加一条 Review 意见 (供 Agent/CI 调用, 无需 delta)
              -s <severity> -f <file> [-l <line>] -c <comment> [--review-file <path>]
              severity: blocking | important | suggestion | nitpick | question | praise
    report    查看/汇总 Review 报告
              --list (默认) | --latest | --summary | --cat <file> | --file <record>
              --summary --file <code-review.md>: 合入门禁判决的唯一来源
              退出码关闭于 0/1/2: 0 允许, 1 拒绝 (当前记录的 blocking 计数), 2 输入错误
              省略 --file 是历史模式: 自标 implicit, 组合路径一律显式给路径
    base      解析评审基准 (非交互路径第 1 步)
              --spec <dir> | --since/--base <ref> | --trunk <ref> | --head <ref> | --json
              输出 base= head= base_source=; 无档可解时 base_source=not-evaluated 并退出 2
    triage    判定代码段适用性 (run | not-applicable | not-evaluated)
              --spec <dir> | --since <ref> | --head <ref> | --trunk <ref> | --code-paths <glob[,glob]>
              输出 triage= basis= changed_files=; 空 delta 在任何回执之前判定
    start     创建代码段记录, 并把上一次记录轮转归档 (非交互路径第 2 步)
              --spec <dir> | --since <ref> | --head <ref> | --trunk <ref> | --renderer <delta|text>
              --triage <value>: 非 run 的适用性拒绝创建记录; 归档名 code-review-<YYYYMMDDTHHMMSSZ>.md
    receipt   覆盖率回执与段裁决 (非交互路径第 4 步)
              --review-file <code-review.md> (必需, 不做目录内最新文件隐式选取)
              --spec <dir> | --since <ref> | --head <ref> | --trunk <ref> | --renderer <delta|text>
              --skip-with-reason <glob> --reason <reason>  (可重复; 理由取自法定五值)
              写出记录内定界的 name=value 块并打印同一块; 四项计数只由它产出
              退出码关闭于 0/1/2: 0 完整, 1 覆盖缺口, 2 不可评估 (不写块)

  NON-INTERACTIVE PATH (four steps, in this order — four, never three):
    1. base      resolve the range: base= head= base_source=
    2. start     record creation and rotation (required from the second run on)
    3. note      append opinions (repeatable, one call per opinion)
    4. receipt   coverage receipt and the summary verdict
  No step prompts; no step needs a terminal. Step 2 is a step of its own: skipping
  it turns the unattended path into an agent hand-writing the record.

  EXAMPLES:
    git-delta-review.sh diff --stat --since main          # Phase 1: 提交粒度自检
    git-delta-review.sh diff --worktree                   # 审查未提交改动 (dogfooding/提交前)
    git-delta-review.sh diff --side-by-side               # 左右分栏对比 (GitHub PR 视图)
    git-delta-review.sh review --since main               # Phase 2: 结构化审查
    git-delta-review.sh note -s blocking -f src/a.rs -l 45 -c "空指针风险"
    git-delta-review.sh report --summary                  # Phase 3/4: 收敛判定
    git-delta-review.sh base --spec .specify/specs/<key>  # 代码段: 解析本次评审区间
    git-delta-review.sh triage --spec .specify/specs/<key>  # 代码段: 适用性判定
    git-delta-review.sh start --spec .specify/specs/<key>   # 代码段: 创建/轮转记录

  ENVIRONMENT:
    REVIEW_DIR    Review 文件存储目录 (默认: ${SKILL_WORKDIR}/.specify/review)
    GIT_BASE      默认对比基准 (默认: main; base/triage/start 不使用该默认)
    GIT_HEAD      默认对比目标 (默认: HEAD)
    DELTA_BIN     delta 二进制路径 (默认: delta)
    REVIEW_RUN_TIMESTAMP  固定运行时间戳 YYYYMMDDTHHMMSSZ (默认: 当前 UTC 时间)

EOF
}

main() {
    [[ $# -eq 0 ]] && { usage; exit 0; }
    local cmd="$1"; shift

    case "$cmd" in
        diff)    cmd_diff "$@" ;;
        review)  cmd_review "$@" ;;
        note)    cmd_note "$@" ;;
        report)  cmd_report "$@" ;;
        base)    cmd_base "$@" ;;
        triage)  cmd_triage "$@" ;;
        start)   cmd_start "$@" ;;
        receipt) cmd_receipt "$@" ;;
        capture) cmd_capture "$@" ;;
        help|-h|--help) usage ;;
        *)       die "未知命令: $cmd (使用 --help 查看用法)" ;;
    esac
}

main "$@"
