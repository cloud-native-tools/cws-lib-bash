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
$(get_diff_stat)
\`\`\`

## 变更文件

$(get_changed_files | sed 's/^/- `/;s/$/`/')

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
cmd_report() {
    local action="list" target=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --latest)  action="latest"; shift ;;
            --summary) action="summary"; shift ;;
            --cat)     action="cat"; target="$2"; shift 2 ;;
            *)         shift ;;
        esac
    done

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
        summary)
            # 按级别汇总 + 合入门禁判定 (Phase 3 收敛条件 / Phase 4 合入前检查)
            local f="${files[0]}"
            [[ -n "$target" ]] && f="$target"
            echo -e "${BLD}━━━ Review 汇总: ${f} ━━━${RST}"
            echo ""
            local sev count blocking_count=0 important_count=0
            for sev in "${SEVERITY_LEVELS[@]}"; do
                count=$(grep -c "^### .* \[${sev^^}\]" "$f" 2>/dev/null || true)
                printf "  %s %-12s %s\n" "$(severity_icon "$sev")" "[$sev]" "$count"
                [[ "$sev" == "blocking" ]]  && blocking_count="$count"
                [[ "$sev" == "important" ]] && important_count="$count"
            done
            echo ""
            if [[ "$blocking_count" -gt 0 ]]; then
                echo -e "  ${RED}✗ 合入门禁: 存在 ${blocking_count} 条 [blocking] — 必须解决后方可合入${RST}"
            elif [[ "$important_count" -gt 0 ]]; then
                echo -e "  ${YEL}⚠ 合入门禁: 存在 ${important_count} 条 [important] — 需回应 (同意/不同意+理由) 后方可合入${RST}"
            else
                echo -e "  ${GRN}✓ 合入门禁: 无未决 blocking/important — 满足收敛条件${RST}"
            fi
            ;;
    esac
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
              --list (默认) | --latest | --summary (按级别汇总 + 合入门禁判定) | --cat <file>

  EXAMPLES:
    git-delta-review.sh diff --stat --since main          # Phase 1: 提交粒度自检
    git-delta-review.sh diff --worktree                   # 审查未提交改动 (dogfooding/提交前)
    git-delta-review.sh diff --side-by-side               # 左右分栏对比 (GitHub PR 视图)
    git-delta-review.sh review --since main               # Phase 2: 结构化审查
    git-delta-review.sh note -s blocking -f src/a.rs -l 45 -c "空指针风险"
    git-delta-review.sh report --summary                  # Phase 3/4: 收敛判定

  ENVIRONMENT:
    REVIEW_DIR    Review 文件存储目录 (默认: ${SKILL_WORKDIR}/.specify/review)
    GIT_BASE      默认对比基准 (默认: main)
    GIT_HEAD      默认对比目标 (默认: HEAD)
    DELTA_BIN     delta 二进制路径 (默认: delta)

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
        help|-h|--help) usage ;;
        *)       die "未知命令: $cmd (使用 --help 查看用法)" ;;
    esac
}

main "$@"
