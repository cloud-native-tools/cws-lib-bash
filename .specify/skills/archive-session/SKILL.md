---
name: archive-session
description: 把当前 AI agent CLI 会话导出为用户命名的目录(含主记录、子代理日志、状态目录、超大工具结果、requestId),并附带会话描述文档(session-meta.json 元信息 + SESSION.md 总结骨架)。支持恰好六家工具:`claude-code` / `codex-cli` / `qoder-cli` / `copilot` / `opencode` / `hermes`(后两家为探测式适配,会话存储未探测到时诚实声明)。
version: 2.0.0
user-invocable: true
argument-hint: "--name <bundle-name> [--session <id>] [--tool <name>] [--verify <text>]"
disable-model-invocation: true
metadata:
  short-description: 导出当前会话为用户命名目录 + 描述文档
---

# 调用

脚本是本 SKILL.md 同目录的 `scripts/export.py`。按**当前能执行的 shell**(不是按操作系统)选下面一组整段执行:Windows 上的 Agent 常经 Git Bash 执行命令,此时用 bash 那组。

bash(macOS / Linux / Windows 的 Git Bash):

```bash
SCRIPT="<本SKILL.md所在目录>/scripts/export.py"
if [ ! -f "$SCRIPT" ]; then
  SCRIPT=""
  for d in "${CLAUDE_SKILL_DIR:-}" ~/.qoder/skills/archive-session ~/.claude/skills/archive-session ~/.codex/skills/archive-session ~/.config/opencode/skills/archive-session; do
    [ -n "$d" ] && [ -f "$d/scripts/export.py" ] && SCRIPT="$d/scripts/export.py" && break
  done
fi
[ -z "$SCRIPT" ] && { echo "archive-session: scripts/export.py not found" >&2; exit 4; }
PY=""; for c in python3 python py; do "$c" -V >/dev/null 2>&1 && PY="$c" && break; done
[ -z "$PY" ] && { echo "archive-session: python not found" >&2; exit 4; }
"$PY" "$SCRIPT" --name "<bundle-name>" --verify "用户最近一句内容"
```

PowerShell(Windows):

```powershell
$SCRIPT = "<本SKILL.md所在目录>\scripts\export.py"
if (-not (Test-Path -LiteralPath $SCRIPT)) {
  $dirs = @($env:CLAUDE_SKILL_DIR) + ('.qoder','.claude','.codex','.config\opencode' | ForEach-Object { Join-Path $env:USERPROFILE "$_\skills\archive-session" })
  $SCRIPT = $dirs | Where-Object { $_ } | ForEach-Object { Join-Path $_ 'scripts\export.py' } | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $SCRIPT) { Write-Error 'archive-session: scripts/export.py not found'; exit 4 }
$PY = 'python','py','python3' | Where-Object { try { & $_ -V *>$null; $LASTEXITCODE -eq 0 } catch { $false } } | Select-Object -First 1
if (-not $PY) { Write-Error 'archive-session: python not found'; exit 4 }
& $PY $SCRIPT --name "<bundle-name>" --verify "用户最近一句内容"
exit $LASTEXITCODE
```

末行 `exit $LASTEXITCODE` 不能省:PowerShell 不会自动把原生命令的退出码当作脚本退出码。bash 侧天然传出,无需此行。

解释器名不要写死:bash 段候选 `python3 python py`,PowerShell 段 `python py python3`,均用 `-V` 实跑一次来挑。

# 参数

| 参数 | 必填 | 何时用 | 示例 |
|------|------|--------|------|
| `--name <bundle-name>` | 是 | 导出目录名——命名是本技能的目的本身,缺省即退出码 2;文法为安全路径段(首字符字母/数字,其余 `[A-Za-z0-9_.-]`,不得为 `.`/`..`) | `--name arena-run-01` |
| `--verify <text>` | 建议 | 始终传。填本轮对话中用户最近一句内容,用于确认选中的 session 正确;未命中时自动跨工具重定位。模型自行填写,用户无需提供 | `--verify "用户最近一句内容"` |
| `--session <id>` | 否 | 用户明确给出具体 sessionId(uuid 形式)时,在当前项目下查找该会话 | `--session 4f8e...` |
| `--tool <name>` | 否 | 显式指定工具、跳过自动识别(取值见下方支持矩阵) | `--tool codex-cli` |

# 输出

成功后 stdout 末行打印**导出目录的绝对路径**:`<项目根>/.session-export/<bundle-name>/`,目录内容:

```text
.session-export/<bundle-name>/
├── main.<原生扩展名>      # 会话主记录(宿主原生形态,逐字节复制)
├── subagents/             # 子代理日志(宿主有则导出)
├── state/                 # 状态目录与段日志(宿主有则导出)
├── large-results/         # 超大工具结果(宿主有则导出)
├── request-ids.jsonl      # 仅可提取 requestId 的工具附带
├── session-meta.json      # 元信息(机读,脚本确定性提取)
└── SESSION.md             # 会话描述文档(元信息节 + 总结占位节)
```

同名目录已存在 → 退出码 2 拒绝(不提供任何覆盖旁路标志;覆盖由调用方命令的交互式门禁处置)。

转述给用户时,**必须按以下格式**(版本取本文件 frontmatter 的 `version`;工具取 stderr `exported ... [tool] ...` 方括号里的 tool;路径取 stdout 末行):

```
✅ 会话已导出
- 版本:archive-session v{version}
- 工具:{tool}
- 目录:{导出目录绝对路径}
- 描述文档:{目录}/SESSION.md
```

# 支持矩阵(恰好六家)

| 工具 | 会话存储形态 | 可导出性 | requestId |
|------|--------------|----------|-----------|
| `claude-code` | `~/.claude/projects/**.jsonl` | ✅ | ✅ |
| `codex-cli` | `~/.codex/sessions/**` + state db | ✅ | 按记录可提取性 |
| `qoder-cli` | `~/.qoder/projects/**.jsonl` + workspace db | ✅ | 按记录可提取性 |
| `opencode` | `~/.local/share/opencode/opencode.db`(SQLite) | ✅ | 按记录可提取性 |
| `copilot` | **会话存储未探测到**(候选路径均不存在) | ⚠ 探测式适配:退出码 4 + 诚实声明 | — |
| `hermes` | **会话存储未探测到**(候选路径均不存在) | ⚠ 探测式适配:退出码 4 + 诚实声明 | — |

探测式适配器:候选路径全部不存在时,`--tool copilot|hermes` 返回退出码 4 并声明「该平台会话存储未探测到」;不臆造导出行为。未来探测到真实落盘再升级为完整适配器。

# 描述文档流程

1. 脚本确定性输出 `session-meta.json`(tool / session_id / model / workspace / 时间窗 / 规模计数 / snapshot / over_summary_budget)与 `SESSION.md` 的**元信息节**(两形态逐字段一致,null 字段标注「记录未含」),并留下固定的**结构化总结占位节**。
2. 执行导出的 agent 读取导出的原始记录,**补写**总结节为三段:任务脉络 / 关键决策 / 产物清单——忠实于记录,不虚构;不得改动元信息节。
3. 预算纪律:`over_summary_budget: true`(主记录行数 > 50,000 或字节 > 32 MB)→ 写骨架总结并显式声明降级原因与触发阈值;未超限 → 全量总结。
4. 运行中会话(`snapshot: true`):总结限定为「截至快照时点」并声明。

# 退出码

| 码 | 含义 | 怎么办 |
|----|------|--------|
| 0 | 成功 | 把导出目录路径告诉用户 |
| 2 | 参数无效(缺/非法 `--name`、`--session` 为空、同名目录冲突) | 把 stderr 显示给用户 |
| 3 | 当前项目没有匹配会话 | 告知用户「没找到」 |
| 4 | 没有任何支持的工具可用;或探测式适配(copilot/hermes)会话存储未探测到;或前置检查失败(脚本/解释器缺失) | 把 stderr 显示给用户 |
| 5 | IO 或 SQLite 错 | 把 stderr 显示给用户 |

# 约束

- 对宿主会话存储**只读**——记录被复制,从不被移动或修改。
- `.session-export/` 已由框架所有者裁定加入 `.gitignore`(2026-08-15):导出物默认不入库;用户确要入库时自行改回。
- 无网络调用、无外部凭证;支持 macOS / Linux / Windows,平台差异全部由脚本内部处理,调用方只需选对 shell。

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:archive-session" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
