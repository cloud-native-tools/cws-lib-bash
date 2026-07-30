# Permission Mode Reference

Permission mode flags per tool for `config_agent_start <tool> [dev|yolo]`.

## Mode Semantics

| Mode | Description |
|---|---|
| `dev` | Basic edit permissions. File modifications require user confirmation. |
| `yolo` | "You Only Live Once" — skip all permission checks, full auto-execution. |

## Per-Tool Flags

### claude (Claude Code)

| Mode | Primary Flag | Fallback Flag |
|---|---|---|
| dev | `--permission-mode acceptEdits` | — |
| yolo | `--dangerously-skip-permissions` | `--permission-mode bypassPermissions` |

### codex (Codex CLI)

| Mode | Flag |
|---|---|
| dev | `--approval-mode suggest` |
| yolo | `--approval-mode full-auto` |

### qwen (Qwen Code)

| Mode | Primary Flag | Fallback Flag |
|---|---|---|
| dev | `--permission-mode acceptEdits` | — |
| yolo | `--dangerously-skip-permissions` | `--permission-mode bypassPermissions` |

### qoder (Qoder CLI)

| Mode | Primary Flag | Fallback Flag |
|---|---|---|
| dev | `--permission-mode acceptEdits` | — |
| yolo | `--dangerously-skip-permissions` | `--permission-mode bypassPermissions` |

### iflow (iFlow CLI)

| Mode | Primary Flag | Fallback Flag |
|---|---|---|
| dev | `--permission-mode acceptEdits` | — |
| yolo | `--dangerously-skip-permissions` | `--permission-mode bypassPermissions` |

### opencode (OpenCode)

| Mode | Primary Flag | Fallback Flag |
|---|---|---|
| dev | `--auto-approve` | — |
| yolo | `--yolo` | `--auto-approve` |

## Fallback Logic

For tools with a fallback flag (`||` operator), the primary flag is tried first. If the CLI exits with a non-zero status (indicating the flag is unsupported in the current version), the fallback flag is used automatically.

```bash
# Example: qwen_yolo fallback pattern
qwen --dangerously-skip-permissions "$@" || qwen --permission-mode bypassPermissions "$@"
```

## Related Scripts

The wrapper functions are defined in `cws-lib-bash/scripts/<tool>.sh`:
- `claude.sh` — `claude_dev`, `claude_yolo`
- `codex.sh` — `codex_dev`, `codex_yolo`
- `qwen.sh` — `qwen_dev`, `qwen_yolo`
- `qoder_cli.sh` — `qoder_cli_dev`, `qoder_cli_yolo`
- `iflow.sh` — `iflow_dev`, `iflow_yolo`
- `opencode.sh` — `opencode_dev`, `opencode_yolo`
