# CLI Capability Profiles — Schema & Observation Program

> **Owner declaration**: this file is the single schema and observation-program owner for CLI behaviour knowledge. The per-CLI files in this directory are the only knowledge point; every other reference, prompt, or doc points here by path and never copies profile content.

## Profile Index

| CLI | Profile | Status |
|-----|---------|--------|
| qodercli | `qodercli.md` | observed (initial facts) |
| claude | `claude.md` | skeleton (all dimensions unknown) |
| codex | `codex.md` | skeleton (all dimensions unknown) |
| opencode | `opencode.md` | skeleton (all dimensions unknown) |
| hermes | `hermes.md` | skeleton (all dimensions unknown; `CAPABILITY_MATRIX` gap) |

A CLI without a profile MUST NOT be dispatched: first create the skeleton, record the gap, then dispatch under the safe default defined by the matrix. A profile never grants dispatch eligibility. Concretely, the safe default after a skeleton exists is: dispatch only if `CAPABILITY_MATRIX` accepts the CLI; if the matrix has no entry (e.g. `hermes`), do **not** dispatch — record the gap and leave the eligibility decision to the matrix owner.

## Eight Dimensions

Every profile carries exactly these rows, each with `known` or `unknown`:

| dimension | meaning |
|-----------|---------|
| `invocation` | 调用方式、关键参数、提示词/权限模式 |
| `output_mode` | 输出模式（`-p` 缓冲 vs `--output-format stream-json`）与事件形状 |
| `timeouts` | 后台/超时上限（`BASH_DEFAULT_TIMEOUT_MS` / `BASH_MAX_TIMEOUT_MS`、默认最大 600,000 ms、正值覆盖、0/负值语义）及与阶段 deadline 的区分 |
| `sentinel` | 哨兵可靠性与非终止回显 |
| `buffering` | 缓冲/可见性行为（日志何时可见、是否只能等退出） |
| `session_logs` | session/run 日志位置 |
| `detach_signals` | detach 行为（`nohup`/`setsid`/`disown`）、信号/退出与孤儿检测 |
| `defects_versions` | 已知缺陷、版本适用性与证据 |

## known / unknown Discipline

- Each row is `known` or `unknown`; missing a dimension is a contract failure.
- `known` MUST carry `observed_at`, `cli_version`, and `evidence_ptr` (command/log/commit pointer).
- `unknown` MUST NOT be filled with a guess; the value cell stays `-`.
- Version or platform differences are a new observation — never reuse an old conclusion.
- Defects keep history; a fix records `fixed_in`; conflicting observations coexist with evidence (no silent pick).

## Provenance Table

Each profile carries `## Provenance`:

```text
| date | trigger | observation | change | feedback_id |
```

`trigger` is one of `U2`, `U4`, `U5`. `feedback_id` may be backfilled after the feedback entry is recorded (the recorded entry is the durable evidence; the id is a convenience pointer).

## Observation Triggers

| trigger | action | feedback |
|---------|--------|----------|
| **U2 (before dispatch)** | Read-only consult of the target CLI profile; choose the timeout/detach shape from it; record `profile_id`, `profile_version`, `observed_cli_version` in the dispatch record. Do not edit the profile. | Matching profile + no new fact → **zero** feedback |
| **U4 (independent verification)** | Compare output mode/event shape, sentinel source, status/exit fields, runner rc vs watcher verdict, log/session location, and buffering. | A mismatch, an `unknown` gaining a verified value, or a first-seen version/platform behaviour → update + exactly one `cli-profile:<cli>` feedback |
| **U5 (stall handling)** | Compare known defects, timeout ceiling, detach/orphan behaviour. | Same event rule; one independent event = one feedback entry |

Write order is fixed: state-spine `cli_observations` → profile provenance → feedback. A single dispatch may produce multiple independent observation events; each produces its own feedback entry (never merged, never dropped). No new fact = zero feedback.

The executable counterpart of this chain is the framework test fixture `tests/fixtures/cli_observation.py` (driven by `test_clp_10_observation_fixture_cardinality`): one event → one spine record; on a changed value it also appends one provenance row and records exactly one `cli-profile:<cli>` feedback entry. `known` rows record the CLI's own observable version (`qodercli --version` → `1.1.73`, 2026-10-20) plus a reproducible evidence pointer, never a placeholder.

## Feedback Marker

Record through the existing engine (do not duplicate or replace it; never auto-transmit):

```bash
python3 .specify/scripts/python/feedback-utils.py --action record \
  --unit-id "skill:sdd-loop-driver" --unit-type skill \
  --review "cli-profile:<cli> ..." --points "..." 
python3 .specify/scripts/python/feedback-utils.py --action list --contains "cli-profile:<cli>"
```

Stable marker: `cli-profile:<cli>`. Probe Object: `skill-sdd-loop-driver-cli-profile` (`skill-wrapup` + `skill:sdd-loop-driver` + `wrap-up`).

## Non-Interference Boundary

- A profile update MUST NOT change sentinel semantics, the watcher 判定 state machine or 退出码 (exit codes), 确认门 (confirmation gates), stage deadlines, or the test budget（测试预算）。
- The current stage uses the shape recorded at U2; an update never retroactively changes it（不回溯、不改变当前阶段的形态）。 If the observed conflict makes the stage unsafe, use the existing U5 stall/retry path — never substitute a profile edit for a behaviour fix.
- Throughput default of the output mode (stream-json) is owned by `efficiency-model.md`; profiles record buffering/event facts only and MUST NOT rewrite that default (不改写该默认).

## Matrix Authority

Dispatch eligibility (accepted shapes, flags, support set) is owned by `CAPABILITY_MATRIX` in `.specify/scripts/python/execution-config.py` — the **唯一 owner**. Profiles record observed behaviour only. On conflict, eligibility follows the matrix while the profile records the observation and raises a feedback entry; matrix changes go through its owner process, never through a profile edit.

## Delivery

Profiles and this index live under `references/cli/` and ship through `.specify/scripts/python/sync-mirrors.py --only skills/external/sdd-loop-driver`; the docs entry `docs/reference/skills/sdd-loop-driver.md` points here without copying tables.
