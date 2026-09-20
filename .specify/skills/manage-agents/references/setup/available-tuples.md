# Available Four-Tuples

> **Legacy input model.** Availability here is computed from the provider-specific
> four-tuple credential variables. The unified `AGENT_*` environment variables
> (see [unified-variables.md](./unified-variables.md)) supersede these on the
> **input** side; this document remains the reference for the legacy
> credential-availability check.

Available tuples are a subset of [Supported Tuples](./supported-tuples.md) where all required credentials are present in the current environment.

## Availability Check Criteria

A four-tuple is **available** when ALL of the following are true:

1. **Provider URL is set** — the corresponding URL environment variable is non-empty
2. **Provider Key is set** — the corresponding key environment variable is non-empty

## Dynamic Availability Matrix

The script `${SKILL_HOME}/scripts/agent-setup.sh` computes availability at runtime by checking environment variables. The table below documents the expected availability under normal credential loading.

### idealab Availability

| Variable | Source File | Status |
|---|---|---|
| `ANTHROPIC_AUTH_TOKEN` | `config/idealab/aistudio/key.rc` | Loaded by `20_claude.sh` |
| `CLAUDE_OFFICIAL_BASE_URL` | `config/idealab/aistudio/key.rc` | Loaded by `20_claude.sh` |

### bailian Availability

| Variable | Source File | Status |
|---|---|---|
| `ALIYUN_BAILIAN_API_KEY` | `config/aliyun/service/bailian/key.rc` | Loaded by `19_aliyun.sh` |
| `ALIYUN_OPENAI_COMPATIBLE_URL` | `config/aliyun/service/bailian/url.rc` | Loaded by `19_aliyun.sh` |
| `ALIYUN_ANTHROPIC_COMPATIBLE_URL` | `config/aliyun/service/bailian/url.rc` | Loaded by `19_aliyun.sh` |

## Available Tuples (when all credentials loaded)

When both idealab and bailian credentials are loaded, all 28 supported tuples are available.

### If only bailian credentials are available:

All 27 bailian tuples are available (tuples #2–#42 from the [Supported Tuples](./supported-tuples.md) list; the numbering keeps stable IDs and therefore has gaps where the dropped `qwen`/`iflow` tool tuples used to sit). This includes:

- **claude**: 6 models via Anthropic protocol (qwen3.7-max, qwen3.7-plus, deepseek-v4-pro, deepseek-v4-flash, glm-5.2, kimi-k2.7-code)
- **codex / qoder / opencode**: 7 models each via OpenAI protocol (qwen3-coder-plus, qwen3.7-max, qwen3.7-plus, deepseek-v4-pro, deepseek-v4-flash, glm-5.2, kimi-k2.7-code)

> `claude-opus-*` models are NOT available on bailian. Only idealab provides `claude-opus-4-8`.

### If only idealab credentials are available:

| # | Tool | Model | Provider |
|---|---|---|---|
| 1 | claude | claude-opus-4-8 | idealab |

> idealab only supports `claude` with `claude-opus-4-8` via Anthropic-compatible protocol. No other tools or models are available through idealab.

## Runtime Check

Use `config_agent_list` to see the dynamically computed available tuples at runtime:

```bash
config_agent_list           # Show available tuples only
config_agent_list --all     # Show all supported tuples (including unavailable)
```
