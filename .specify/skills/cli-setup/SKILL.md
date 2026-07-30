---
name: agent-setup
description: |
  Configure AI agent CLI tools (Claude Code, Codex, Qwen Code, Qoder CLI, iFlow, OpenCode)
  from a single, unified set of environment variables. Export AGENT_API_KEY, AGENT_MODEL,
  AGENT_BASE_URL (and AGENT_ANTHROPIC_BASE_URL for claude); the skill validates them
  (config_agent_env_validate), secondary-assigns them into each tool's native fields, and
  persists each tool's own config file (config_agent_env_apply). Also provides a legacy
  four-tuple model plus install/start helpers.
  Use this when the user mentions: "配置agent", "配置AI工具", "切换模型", "切换provider",
  "config agent", "agent setup", "install codex", "install claude", "install qwen",
  "configure agent", "switch model", "agent four-tuple", "四元组配置", "互斥配置",
  "统一环境变量", "unified env", "AGENT_API_KEY"
skill_id: "<SKILL:.specify/skills/agent-setup/SKILL.md>"
---

# agent-setup

## Overview

Configure the six API-key AI-tool CLIs — `claude`, `codex`, `qwen`, `qoder`, `iflow`,
`opencode` — from **one unified set of environment variables**. You export the three core
inputs once; the skill validates them, performs a **secondary assignment** into each tool's
native variable names, and persists the result into each tool's **own configuration file**.

> **Scope**: GitHub Copilot (IDE/subscription/OAuth) and Hermes Agent (OAuth portal) do NOT
> use an API-key/URL/model model and are **out of scope** for the unified env-var flow.

A legacy **four-tuple** abstraction (`tool, model, provider_url, provider_key`) and the
install/start helpers remain available (see [Legacy four-tuple flow](#legacy-four-tuple-flow)).

## Unified Environment-Variable Configuration (Recommended)

### Unified variables

| Variable | Required | Rule |
|----------|----------|------|
| `AGENT_API_KEY` | Yes | Non-empty (after trim). Applies to every targeted tool. |
| `AGENT_MODEL` | Yes | Non-empty (after trim). Applies to every targeted tool. |
| `AGENT_BASE_URL` | Yes | Non-empty; must start with `http(s)://`. OpenAI-compatible endpoint. |
| `AGENT_ANTHROPIC_BASE_URL` | Conditional | Required when `claude` is **explicitly** targeted; must start with `http(s)://`. |

Environment variables are the **only** input channel — no prompts, no config-file inputs. See
[unified-variables.md](${SKILL_HOME}/references/unified-variables.md) for the full rules and
per-tool secondary-assignment map.

### Three-step flow: check → read → write

```bash
source ${SKILL_HOME}/scripts/config-agent.sh

# 1. Check — validate the unified variables (writes nothing)
config_agent_env_validate --all

# 2 + 3. Read + write — secondary-assign and persist each tool's own config file
config_agent_env_apply --all          # all six tools
config_agent_env_apply qwen           # a single named tool
```

- **`config_agent_env_validate [--all | <tool>...]`** — verifies presence, non-emptiness, and
  URL scheme for every required variable; reports **every** offender grouped as
  `Missing` / `Malformed`; exit `1` on any offender; writes nothing. Exit `3` for an unknown tool.
- **`config_agent_env_apply [--all | <tool>...]`** — validates first (fail-fast, no partial
  writes), then for each target: secondary-assigns the unified values, creates missing
  directories, merge-writes the tool's config file (preserving unrelated keys), and prints a
  secret-free per-tool report (`configured` / `skipped` / `failed`). Exit `2` if any tool fails.

### Per-tool persistence targets

| Tool | Protocol | URL source | Config file |
|------|----------|------------|-------------|
| `claude` | anthropic | `AGENT_ANTHROPIC_BASE_URL` | `~/.claude/settings.json` |
| `codex` | openai | `AGENT_BASE_URL` | `~/.codex/config.toml` (+ `~/.codex/auth.json` for the key) |
| `qwen` | openai | `AGENT_BASE_URL` | `~/.qwen/.env` |
| `qoder` | openai | `AGENT_BASE_URL` | `~/.qoder/config.json` |
| `iflow` | openai | `AGENT_BASE_URL` | `~/.iflow/settings.json` |
| `opencode` | openai | `AGENT_BASE_URL` | `~/.config/opencode/config.json` |

### Guarantees

- **Fail-fast, no partial writes** — invalid input aborts before any file is touched.
- **Idempotent** — re-running with unchanged inputs yields identical config.
- **Non-destructive** — unrelated existing settings in JSON/dotenv files are preserved.
- **Secret-free output** — the API key value is never printed in any log, summary, or error.
- **`--all` leniency** — if `AGENT_ANTHROPIC_BASE_URL` is unset under `--all`, `claude` is
  reported `skipped` and the other five still configure. Naming `claude` explicitly requires it.

## Legacy four-tuple flow

Manage AI agent CLI tool configurations through a **four-tuple** abstraction:

```
(tool, model, provider_url, provider_key)
```

- **tool** — CLI binary name: `claude`, `codex`, `qwen`, `qoder` (Qoder CLI), `iflow`, `opencode`
- **model** — LLM model identifier: `glm-5.2`, `qwen3-coder-plus`, `claude-opus-4-8`, etc.
- **provider_url** — API endpoint URL (resolved from provider: `idealab` or `bailian`)
- **provider_key** — API authentication key (resolved from provider credential files)

### Mutual Exclusion Rule

At any given time, **one tool can only bind one (model, provider) pair**. Configuring a new pair for an already-configured tool replaces the previous binding atomically.

## Four-Tuple Compatibility

Not all combinations are valid. Compatibility is determined by API protocol and provider capabilities:

| Tool | API Protocol | Compatible Providers | Supported Models |
|------|-------------|---------------------|-------------------|
| `claude` | Anthropic-compatible | idealab (claude-opus-4-8 only), bailian (dual-protocol models only) | claude-opus-4-8, qwen3.7-max, qwen3.7-plus, deepseek-v4-pro, deepseek-v4-flash, glm-5.2, kimi-k2.7-code |
| `codex` | OpenAI-compatible (responses) | bailian | qwen3-coder-plus, qwen3.7-max, qwen3.7-plus, deepseek-v4-pro, deepseek-v4-flash, glm-5.2, kimi-k2.7-code |
| `qwen` | OpenAI-compatible | bailian | (same as codex) |
| `qoder` | OpenAI-compatible | bailian | (same as codex) |
| `iflow` | OpenAI-compatible | bailian | (same as codex) |
| `opencode` | OpenAI-compatible | bailian | (same as codex) |

> **Note**: `claude-opus-*` models are NOT available on bailian. `claude-opus-4-8` is idealab-only; `claude-opus-4-7` has no provider and is excluded. Bailian dual-protocol models (qwen3.7-max, qwen3.7-plus, deepseek-v4-pro, deepseek-v4-flash, glm-5.2, kimi-k2.7-code) support **both** Anthropic and OpenAI protocols simultaneously, making them usable by all tools including claude.

For the full supported and available four-tuple lists, see:
- [Supported Tuples](${SKILL_HOME}/references/supported-tuples.md) — all valid combinations (42 tuples)
- [Available Tuples](${SKILL_HOME}/references/available-tuples.md) — tuples actionable with current credentials

## Workflow

### 1. List — Discover available configurations

```bash
# List all supported four-tuples
config_agent_list

# Show currently active configuration for all tools
config_agent_show

# Show active configuration for a specific tool
config_agent_show claude
```

### 2. Validate — Check if a four-tuple is supported

```bash
# Validate before configuring
config_agent_validate <tool> <model> <provider>
# Example: config_agent_validate codex glm-5.2 bailian
```

Validation checks:
1. Tool exists in the supported list
2. Model is compatible with the tool's API protocol
3. Provider offers the correct URL type (Anthropic vs OpenAI)
4. Provider credentials are available in the environment

### 3. Install — Install the CLI binary

```bash
config_agent_install <tool>
# Example: config_agent_install codex
```

Installation methods per tool:
- `claude` — `npm install -g @anthropic-ai/claude-code`
- `codex` — `npm install -g @openai/codex`
- `qwen` — `npm install -g @qwen-code/qwen-code`
- `qoder` — `curl -fsSL https://qoder.com/install \| bash`
- `iflow` — `npm install -g @iflow-ai/iflow-cli`
- `opencode` — `brew install opencode` or `go install github.com/sst/opencode@latest`

### 4. Configure — Bind a four-tuple to a tool

```bash
config_agent_configure <tool> <model> <provider>
# Example: config_agent_configure codex glm-5.2 bailian
```

This function:
1. Validates the four-tuple (calls `config_agent_validate`)
2. Resolves `provider_url` and `provider_key` from provider credentials
3. Enforces mutual exclusion — replaces any existing binding for `<tool>`
4. Writes tool-specific configuration files:
   - `claude` → `${HOME}/.claude/settings.json`
   - `codex` → `${HOME}/.codex/config.toml`
   - `qwen` → env vars `OPENAI_API_KEY` / `OPENAI_BASE_URL`
   - `qoder` → `${HOME}/.qoder/config.json`
   - `iflow` → `${HOME}/.iflow/settings.json`
   - `opencode` → `${HOME}/.config/opencode/config.json`
5. Records the active binding in `${SKILL_WORKDIR}/.agent-config/active.json`

### 5. Start — Launch the tool with a permission mode

```bash
config_agent_start <tool> [dev|yolo]
# Example: config_agent_start codex yolo
```

Permission modes:
- `dev` (default) — basic edit permissions, modifications require confirmation
- `yolo` — skip all permission checks, full auto-execution

Mode flags per tool — see [Permission Mode Reference](${SKILL_HOME}/references/permission-modes.md).

## Path Conventions

This Skill follows the canonical path conventions:

- Use `${SKILL_HOME}/<relative-path>` for Skill-owned resources (scripts, references).
- Use `${SKILL_WORKDIR}/<relative-path>` for runtime/user-facing paths (active config state).

## Resources

### Scripts (`${SKILL_HOME}/scripts/`)
- `agent-setup.sh` — Main configuration management script providing all functions

### References (`${SKILL_HOME}/references/`)
- `unified-variables.md` — unified `AGENT_*` env-var model, rules, and per-tool mapping
- `supported-tuples.md` — All supported four-tuple combinations (legacy flow)
- `available-tuples.md` — Available tuples based on current credentials (legacy flow)
- `permission-modes.md` — Permission mode flags per tool

### Assets (`${SKILL_HOME}/assets/`)
- No static assets currently.

## Usage Examples

```bash
# Full workflow: install codex, configure with glm-5.2 via bailian, start in yolo mode
config_agent_install codex
config_agent_configure codex glm-5.2 bailian
config_agent_start codex yolo

# Switch claude from idealab to bailian (mutual exclusion — old config replaced)
config_agent_configure claude claude-opus-4-8 bailian

# List all supported tuples
config_agent_list

# Show what's currently configured
config_agent_show
```

## Resource ID
- Canonical ID: `<SKILL:.specify/skills/agent-setup/SKILL.md>`
- Canonical Path: `.specify/skills/agent-setup/SKILL.md`

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At the end of a substantial run of this skill, perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this run reached a meaningful wrap-up. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against this skill's declared purpose and produce a short review plus ≥1 concrete, skill-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this skill's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id`; if a parent flow already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "skill:cli-setup" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
