# Agent-Specific Configuration

This document provides agent detection and per-agent operational guidance for commands that need agent-aware behavior.

## Step 1: Identify Executing Agent

Before executing workflows that require agent-specific file operations, identify which AI agent is running:

| Agent | Detection Signals |
|-------|-------------------|
| **Claude Code** | System prompt contains "Claude Code"; tools include `Agent`, `Edit`, `Bash`, `Read`; `.claude/` directory exists |
| **GitHub Copilot** | Running in VS Code Copilot Chat context; `.github/copilot-instructions.md` loaded; tools include `workspace edit`, `@terminal` |
| **Qoder CLI** | `.qoder/` directory exists; `AGENTS.md` instructions loaded |
| **opencode** | `.opencode/` directory exists |
| **Codex CLI** | `.codex/` directory exists |
| **Hermes Agent** | `.hermes/` directory exists |

If you cannot identify your agent, skip agent-specific guidance and proceed with the standard workflow.

## Step 2: Per-Agent File Operation Guidance

### Claude Code

- **File creation**: Use `Write` tool for new files. Use `Edit` for modifications to existing files (preserves surrounding content).
- **Script execution**: Use `Bash` tool. Check exit code explicitly — scripts may exit 0 on partial failure.
- **YAML validation**: `python -c "import yaml; yaml.safe_load(open('file').read().split('---')[1])"`
- **Render verification**: `ls -la .github/agents/ .qoder/agents/ 2>/dev/null` (rendered real files, no symlinks expected)
- **Subagent delegation**: Use `Agent` tool with `subagent_type` to test newly created artifacts.

### GitHub Copilot

- **File operations**: Use workspace edit for creation and updates. For multi-file changes, make changes sequentially.
- **Script execution**: Use `@terminal` to run scripts. Copy JSON output from terminal to chat.
- **Render handling**: agent distribution happens via `specify init` rendering. Advise user to run `specify init` from terminal.
- **Model field**: Default to `GPT-5 (copilot)` for the `model` frontmatter field.

## Step 3: Capture Execution Feedback

If you encounter an agent-specific obstacle during execution, generate a feedback document at:

```
.specify/memory/feedback/<command>-<agent-slug>-<YYYY-MM-DDTHH-MM-SS>.md
```

Structure:

```markdown
# Agent Execution Feedback

**Source**: <command-name>
**Agent**: <agent-slug>
**Timestamp**: <ISO-8601>
**Outcome**: <success-with-workaround | partial-failure | full-failure>

## Obstacle
[Description of the agent-specific issue encountered]

## Workaround Applied
[What was done to work around the issue, if anything]

## Suggested Improvement
[Specific change to the command template that would prevent this issue]
```

Only generate feedback when a genuine agent-specific obstacle was encountered.
