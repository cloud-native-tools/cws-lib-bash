# Supported Four-Tuples

> **Legacy input model.** The unified `AGENT_*` environment variables
> (`AGENT_API_KEY`, `AGENT_MODEL`, `AGENT_BASE_URL`, `AGENT_ANTHROPIC_BASE_URL` —
> see [unified-variables.md](./unified-variables.md)) are now the recommended
> input surface and **supersede** the provider-specific four-tuple input
> variables below (`ALIYUN_*`, `CLAUDE_OFFICIAL_BASE_URL`, etc.). This document
> is retained for the legacy `config_agent_configure` flow and for provider/model
> compatibility reference.

All valid (tool, model, provider_url, provider_key) combinations.

## Provider URL/Key Resolution

### idealab

| URL Variable | Value | Protocol |
|---|---|---|
| `CLAUDE_OFFICIAL_BASE_URL` | `https://idealab.alibaba-inc.com/api/anthropic` | Anthropic |

> idealab only supports Anthropic-compatible protocol. No OpenAI-compatible URL is available.

| Key Variable | Used By |
|---|---|
| `ANTHROPIC_AUTH_TOKEN` | claude (Anthropic protocol, claude-opus-4-8 only) |

### bailian

| URL Variable | Value | Protocol |
|---|---|---|
| `ALIYUN_ANTHROPIC_COMPATIBLE_URL` | `https://llm-*.maas.aliyuncs.com/apps/anthropic` | Anthropic |
| `ALIYUN_OPENAI_COMPATIBLE_URL` | `https://llm-*.maas.aliyuncs.com/compatible-mode/v1` | OpenAI |

| Key Variable | Used By |
|---|---|
| `ALIYUN_BAILIAN_API_KEY` | All tools (both protocols) |

## Supported Models

### Anthropic-Exclusive Models

| Model | Provider | Protocol |
|---|---|---|
| `claude-opus-4-8` | idealab | Anthropic |

> `claude-opus-*` models are NOT available on bailian. `claude-opus-4-8` is idealab-only; `claude-opus-4-7` has no provider and is excluded.

### Bailian Dual-Protocol Models

> The following models are provided by bailian and support **both** Anthropic-compatible and OpenAI-compatible protocols simultaneously. Source: `chatLanguageModels.json`.

| Model | Tool Calling | Vision | Thinking | Max Input Tokens | Max Output Tokens |
|---|---|---|---|---|---|
| `qwen3.7-max` | Yes | Yes | Yes | 991,000 | 64,000 |
| `qwen3.7-plus` | Yes | No | Yes | 991,000 | 64,000 |
| `deepseek-v4-pro` | Yes | No | Yes | 1,000,000 | 384,000 |
| `deepseek-v4-flash` | Yes | No | Yes | 1,000,000 | 384,000 |
| `glm-5.2` | Yes | No | Yes | 1,000,000 | 128,000 |
| `kimi-k2.7-code` | Yes | Yes | Yes | 224,000 | 16,000 |

### Other Models

| Model | Provider | Protocol |
|---|---|---|
| `qwen3-coder-plus` | bailian | OpenAI |

## Full Supported Tuple List

**42 tuples total**: 1 via idealab + 41 via bailian.

### claude (Claude Code) — Anthropic protocol

| # | Model | Provider | URL Variable | Key Variable |
|---|---|---|---|---|
| 1 | claude-opus-4-8 | idealab | CLAUDE_OFFICIAL_BASE_URL | ANTHROPIC_AUTH_TOKEN |
| 2 | qwen3.7-max | bailian | ALIYUN_ANTHROPIC_COMPATIBLE_URL | ALIYUN_BAILIAN_API_KEY |
| 3 | qwen3.7-plus | bailian | ALIYUN_ANTHROPIC_COMPATIBLE_URL | ALIYUN_BAILIAN_API_KEY |
| 4 | deepseek-v4-pro | bailian | ALIYUN_ANTHROPIC_COMPATIBLE_URL | ALIYUN_BAILIAN_API_KEY |
| 5 | deepseek-v4-flash | bailian | ALIYUN_ANTHROPIC_COMPATIBLE_URL | ALIYUN_BAILIAN_API_KEY |
| 6 | glm-5.2 | bailian | ALIYUN_ANTHROPIC_COMPATIBLE_URL | ALIYUN_BAILIAN_API_KEY |
| 7 | kimi-k2.7-code | bailian | ALIYUN_ANTHROPIC_COMPATIBLE_URL | ALIYUN_BAILIAN_API_KEY |

### OpenAI-Protocol Tools (codex / qoder / opencode)

All five tools share the same model list and use the same URL/Key variables:

- **URL Variable**: `ALIYUN_OPENAI_COMPATIBLE_URL`
- **Key Variable**: `ALIYUN_BAILIAN_API_KEY`
- **Provider**: bailian

| # | Tool | Model |
|---|---|---|
| 8 | codex | qwen3-coder-plus |
| 9 | codex | qwen3.7-max |
| 10 | codex | qwen3.7-plus |
| 11 | codex | deepseek-v4-pro |
| 12 | codex | deepseek-v4-flash |
| 13 | codex | glm-5.2 |
| 14 | codex | kimi-k2.7-code |
| 22 | qoder | qwen3-coder-plus |
| 23 | qoder | qwen3.7-max |
| 24 | qoder | qwen3.7-plus |
| 25 | qoder | deepseek-v4-pro |
| 26 | qoder | deepseek-v4-flash |
| 27 | qoder | glm-5.2 |
| 28 | qoder | kimi-k2.7-code |
| 36 | opencode | qwen3-coder-plus |
| 37 | opencode | qwen3.7-max |
| 38 | opencode | qwen3.7-plus |
| 39 | opencode | deepseek-v4-pro |
| 40 | opencode | deepseek-v4-flash |
| 41 | opencode | glm-5.2 |
| 42 | opencode | kimi-k2.7-code |

## Mutual Exclusion Rules

1. **Per-tool exclusivity**: Each tool can only have ONE active (model, provider) pair at any time.
2. **Cross-tool independence**: Different tools can use different (model, provider) pairs simultaneously.
3. **Atomic replacement**: Configuring a new pair for an already-configured tool replaces the old binding atomically — no partial states.

## Credential Source Files

| Provider | File | Variables |
|---|---|---|
| idealab | `config/idealab/aistudio/key.rc` | ANTHROPIC_AUTH_TOKEN |
| idealab | `config/idealab/aistudio/key.rc` | CLAUDE_OFFICIAL_BASE_URL |
| bailian | `config/aliyun/service/bailian/key.rc` | ALIYUN_BAILIAN_API_KEY |
| bailian | `config/aliyun/service/bailian/url.rc` | ALIYUN_OPENAI_COMPATIBLE_URL, ALIYUN_ANTHROPIC_COMPATIBLE_URL |
