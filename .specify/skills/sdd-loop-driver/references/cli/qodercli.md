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

## Defects

| id | status | fixed_in | evidence |
|----|--------|----------|----------|
| QD-000 | none confirmed | — | host probe 2026-10-20; 058/063 observations |

## Provenance

| date | trigger | observation | change | feedback_id |
|------|---------|-------------|--------|-------------|
| 2026-10-20 | U2 | initial profile seeded from the authoritative brief and 063's observed stream-json/nohup work; no new feedback (initial seed) | created eight-dimension profile | — |
| 2026-10-20 | U5 | 0/负值 timeout semantics have not been measured | recorded as `unknown`; no feedback (no new verified fact) | — |
