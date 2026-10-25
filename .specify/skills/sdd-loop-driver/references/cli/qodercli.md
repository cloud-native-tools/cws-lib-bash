# qodercli — CLI Capability Profile

> Profile owner: `index.md`. Facts below were observed on 2026-10-20; a different version/platform is a new observation, not an extension of these rows.

## Dimensions

| dimension | status | value | observed_at | cli_version | evidence_ptr |
|-----------|--------|-------|-------------|-------------|--------------|
| invocation | known | `qodercli -w <project> --permission-mode auto -p "<prompt>"`; the prompt file is passed by command substitution | 2026-10-20 | qodercli 1.1.73 | `qodercli --version` → 1.1.73 (2026-10-20); `notes/source-requirement.md` §2; `references/dispatch-recipes.md` Recipe 2 |
| output_mode | known | `-p` mode buffers (缓冲) the final answer until exit; `--output-format stream-json` is supported and yields live events (the throughput default of stream-json is owned by 063, not by this profile) | 2026-10-20 | qodercli 1.1.73 | `notes/source-requirement.md` §2/§3C; 063 baseline record |
| timeouts | known | `BASH_DEFAULT_TIMEOUT_MS` and `BASH_MAX_TIMEOUT_MS` override the bash tool timeouts; positive override semantics; **default max is 600,000 ms**; the stage deadline is a separate driver-side concept. 0/负值 semantics: unknown (not measured; MUST NOT guess) | 2026-10-20 | qodercli 1.1.73 | `notes/source-requirement.md` §2; this profile's provenance row |
| sentinel | known | The completion sentinel is the log's last non-empty line (`<STAGE>-DONE`); `-p` buffering means intermediate output is not visible, so the status/exit record is the early terminal event and the sentinel remains the necessary completion evidence | 2026-10-20 | qodercli 1.1.73 | 058/063 runner observations; `references/watch-model.md` §2 |
| buffering | known | `-p` buffers output until process exit; the log stays silent during the run (expected, not a stall); stream-json is the live-visibility shape | 2026-10-20 | qodercli 1.1.73 | `notes/source-requirement.md` §2; 063 stream-json record |
| session_logs | known | session/run logs live under `~/.qoder/logs/` (observed root; a run's concrete file is resolved under that tree) | 2026-10-20 | qodercli 1.1.73 | `notes/source-requirement.md` §2 |
| detach_signals | known | 脱离（detached）runner 是子代理在主会话故障后存活的必要条件；a detached runner is required for the subagent to survive main-session failure; local hosts without `setsid` use `nohup` + `disown` with stdio redirected to a log or `/dev/null`; orphan detection uses the registered PID + start token, never a broad process scan | 2026-10-20 | qodercli 1.1.73 | `notes/source-requirement.md` §2; `references/dispatch-recipes.md` detached runner block |
| defects_versions | known | no confirmed defect for the observed **版本** as of 2026-10-20; 缺陷 history is retained and a fix records `fixed_in`; version applicability and **证据** are required for each future entry | 2026-10-20 | qodercli 1.1.73 | this profile's `## Defects` table |

## Recommended Baseline Settings

> Portable recommendation, not a capability observation: it neither extends nor
> alters the eight-dimension rows above. Key names were cross-checked against
> qodercli 1.1.76 on 2026-10-22; re-verify after an upgrade.
>
> **Portability boundary**: this baseline is shared across hosts. Never add
> host- or account-specific material here — absolute trust paths, hook script
> paths, MCP endpoints/credentials, installed plugin lists, or private model
> aliases. Keep those in the per-host config root or a per-dispatch
> `--settings` overlay.

Core requirements: `model=DeepSeek-Flash`, `reasoning.enabled=true`,
`reasoning.effort=max`, `contextWindow=1000000`.

Location: `<config-root>/settings.json` — `~/.qoder-cli/settings.json` by
default, or the root selected by `--config-dir`.

```json
{
  "model": {
    "name": "DeepSeek-Flash",
    "preferences": {
      "DeepSeek-Flash": {
        "contextWindow": 1000000,
        "reasoning": {
          "enabled": true,
          "effort": "max"
        }
      }
    }
  },
  "security": {
    "auth": {
      "selectedType": "qoder-browser"
    }
  },
  "permissions": {
    "additionalDirectories": [],
    "trustDirectories": []
  },
  "securityScan": {
    "l1StaticCheck": true,
    "l2LightweightScan": true,
    "l3DeepScan": true
  }
}
```

| choice | rationale |
|--------|-----------|
| only `DeepSeek-Flash` under `preferences` | pins the three core requirements without carrying account-specific aliases; add another model only after verifying its name on the target account |
| empty `permissions` arrays | trust is host-local: add the target project's directory in each host's config root (or rely on `--permission-mode auto`), never in the shared baseline |
| `qoder-browser` auth | portable auth selector used by both reference configs; credentials stay in the config root and are established by `qodercli login` |
| all three `securityScan` tiers `true` | the CLI treats L1/L2/L3 as enabled unless explicitly set to `false`, so this states the effective default; `gitPushScanHook` stays omitted (default `false`) to avoid altering git push behaviour |
| hooks / MCP / plugins / statistics omitted | per-host or account state; inject the SDD `Stop` hook per dispatch via `--settings` (see `references/watch-model.md` §12), and manage the rest with `qodercli mcp add` / `qodercli plugins install` |

Equivalent per-invocation flags when a dispatch does not read the user-level
file:

```bash
qodercli --model DeepSeek-Flash --thinking enabled --reasoning-effort max \
  --context-window 1000000 ...
```

## Qoder Desktop Host Adapter

> Observed 2026-10-22/23 in the Qoder Desktop app on macOS with qodercli
> **1.1.76**. This is a host-adapter fact, not a change to the capability rows
> above; re-verify after an app or CLI upgrade.

The Qoder **Desktop app** injects four SDK-runtime variables into every child
process. A headless `-p` invocation started from inside the app fails at
argument parsing with
`sdk_invalid_args: Agent SDK entrypoint env is set but required flags are missing`
unless all four are removed from the child environment:

| variable | observed | required action |
|----------|----------|-----------------|
| `QODER_AGENT_SDK_ENTRYPOINT` | `sdk-ts` | unset |
| `QODER_AGENT_SDK_VERSION` | app version | unset |
| `QODER_SDK_AUTH_PAYLOAD_FILE` | path | unset |
| `QODER_SDK_CUSTOM_BASE_URL_BYOK` | value | unset |

Canonical launcher (compose it with the detached/runner form; the unset must be
outside `stage-runner.sh` so the cleared environment reaches the CLI child):

```bash
env -u QODER_AGENT_SDK_ENTRYPOINT -u QODER_AGENT_SDK_VERSION \
    -u QODER_SDK_AUTH_PAYLOAD_FILE -u QODER_SDK_CUSTOM_BASE_URL_BYOK \
  qodercli -w <project> --permission-mode auto -p "$(cat <prompt>)"
```

Additional 1.1.76 observations:

| fact | value | evidence |
|------|-------|----------|
| output formats | `--output-format` accepts exactly `text`, `json`, `stream-json` | `qodercli -p --output-format bogus x` → `Choices: "text", "json", "stream-json"` (2026-10-22, 1.1.76) |
| buffering | `-p` still buffers the whole answer until exit; stream-json is the live shape | 2026-10-22 run: live log stayed 0 bytes until process exit |
| project-skill loading | Desktop loads skills from `<repo>/.qoder/skills` (symlink to `.specify/skills`); the CLI config root `~/.qoder-cli` stays empty by R0 | `kangaroo-xuanji/.qoder/skills → ../.specify/skills`; no `~/.qoder-cli/skills/sdd-loop-driver` |
| liveness signal | `~/.qoder/logs/latest` can lag behind the live run; judge liveness by `kill -0 <pid>` plus child processes, not by log mtime alone | 2026-10-22 implement stage: log mtime 36 min stale while jest children were active |
| permission mode | `--permission-mode auto` is mandatory for SDD stages; `accept_edits` denies git/build commands | 2026-10-22 UI requirements run: 6 git commands denied under the default mode |

## Defects

| id | status | fixed_in | evidence |
|----|--------|----------|----------|
| QD-000 | none confirmed | — | host probe 2026-10-20; 058/063 observations |

## Provenance

| date | trigger | observation | change | feedback_id |
|------|---------|-------------|--------|-------------|
| 2026-10-20 | U2 | initial profile seeded from the authoritative brief and 063's observed stream-json/nohup work; no new feedback (initial seed) | created eight-dimension profile | — |
| 2026-10-20 | U5 | 0/负值 timeout semantics have not been measured | recorded as `unknown`; no feedback (no new verified fact) | — |
| 2026-10-22 | U2 | Qoder Desktop injects four SDK-runtime variables; 1.1.76 output formats are `text/json/stream-json`; `accept_edits` denies git | added "Qoder Desktop Host Adapter" (wrapper + facts) and a dispatch-recipe variant | — |
