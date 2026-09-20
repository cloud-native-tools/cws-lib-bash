# Unified Environment Variables

The `agent-setup` skill configures every supported AI-tool CLI from a single,
canonical set of **skill-layer** environment variables. You export these once;
the skill performs a **secondary assignment** into each tool's native variable
names and persists the result into each tool's own config file.

> Single source of truth for the variable names:
> (defined in the framework repo, spec 024 — unified-env-contract).

## The variables

| Variable | Required | Rule | Feeds |
|----------|----------|------|-------|
| `AGENT_API_KEY` | Yes | Non-empty after trim. | All six tools. |
| `AGENT_MODEL` | Yes | Non-empty after trim. | All six tools. |
| `AGENT_BASE_URL` | Yes | Non-empty; must match `^https?://`. | The three OpenAI-compatible tools (codex, qoder, opencode). |
| `AGENT_ANTHROPIC_BASE_URL` | Conditional | Required when `claude` is **explicitly** targeted; must match `^https?://`. | claude (Anthropic-compatible endpoint). |

### Why a separate Anthropic URL

Five of the six tools speak the OpenAI-compatible protocol and share one
endpoint form; `claude` speaks the Anthropic-compatible protocol whose endpoint
path differs. A single base URL cannot serve both without brittle,
provider-specific path derivation, so the Anthropic endpoint is exposed as an
explicit protocol variant of "URL" — not a new input concept.

### `--all` vs explicit `claude`

- `config_agent_env_apply --all` (or no argument) targets all six tools. If
  `AGENT_ANTHROPIC_BASE_URL` is unset, `claude` is reported **skipped** (with a
  reason) and the other five still configure.
- Naming `claude` explicitly (e.g. `config_agent_env_apply claude`) makes
  `AGENT_ANTHROPIC_BASE_URL` **required**: validation fails (exit 1, no writes)
  when it is missing.

## Validation rules

- A variable that is unset, empty, or whitespace-only is treated as **missing**.
- A URL variable that is present but lacks an `http(s)://` scheme is **malformed**.
- Validation collects **all** offenders before returning; it never stops at the
  first one.
- When validation fails, **zero** config files are written (no partial writes).

## Rules of use

- Environment variables are the **only** input channel — no interactive prompts,
  no config-file inputs.
- The same `AGENT_API_KEY` and `AGENT_MODEL` apply to every targeted tool
  (one-time convenient configuration).
- The API key value is **never** printed in any log line, summary, or error;
  logs reference variable names only.

## Secondary assignment (per tool)

The unified values are mapped onto each tool's native fields and persisted to
that tool's own file. See
the framework repo's tool-config-targets contract (spec 024) for the
exact per-tool mapping.

| Tool | Protocol | URL source | Config file |
|------|----------|------------|-------------|
| claude | anthropic | `AGENT_ANTHROPIC_BASE_URL` | `~/.claude/settings.json` |
| codex | openai | `AGENT_BASE_URL` | `~/.codex/config.toml` (+ `~/.codex/auth.json` for the key) |
| qoder | openai | `AGENT_BASE_URL` | `~/.qoder/config.json` |
| opencode | openai | `AGENT_BASE_URL` | `~/.config/opencode/config.json` |

## Example

```bash
export AGENT_API_KEY="sk-..."
export AGENT_MODEL="glm-5.2"
export AGENT_BASE_URL="https://<host>/compatible-mode/v1"
export AGENT_ANTHROPIC_BASE_URL="https://<host>/apps/anthropic"   # only if configuring claude

source .specify/skills/agent-setup/scripts/config-agent.sh
config_agent_env_validate --all   # no files written
config_agent_env_apply --all      # writes each tool's own config file
```
