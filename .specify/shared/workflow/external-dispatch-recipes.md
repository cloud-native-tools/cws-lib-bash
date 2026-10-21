# External Dispatch Recipes (外部子代理派发配方) — 远端 ssh+su 与本地直驱拓扑

Operational recipes for driving an **external subagent** (Mode 3 in [`subagent-definitions.md`](../definitions/subagent-definitions.md)) through a second agent CLI — most commonly a remote host reached via `ssh`, switching to the project's run user with `su`, and running `qodercli` (or any supported agent CLI) inside the project directory. The local topology — the CLI driven directly against a local working directory — is the degenerate case of the same recipe.

**Division of labor (one source of truth)**: [`subagent-definitions.md`](../definitions/subagent-definitions.md) owns *what* an external dispatch is and the **External Dispatch Visibility Contract** it MUST satisfy; the **Unattended Loop Pattern** ([`unattended-loop-pattern.md`](../patterns/unattended-loop-pattern.md)) owns *when* a multi-stage progression is orchestrated as a loop and its stage protocol. This document owns only the *how* — the concrete, validated command shapes. Every parameter (login alias, user, path, CLI, stage name) is entry-level; nothing here hardcodes a workspace naming rule.

## Two Topologies

| Topology | Shape | When |
|----------|-------|------|
| **Remote (ssh + su + CLI)** | orchestrator machine → `ssh <alias>` → `su <run-user>` → agent CLI inside the project dir | project lives on a remote host; long unattended runs that must outlive local sessions |
| **Local (direct)** | orchestrator session drives the agent CLI directly with the local project as working directory | project lives on the same machine |

Both topologies support parallel lines: one connection/process per line, each line tracked with its own task entry (e.g. TaskCreate/TaskUpdate) so the orchestrator never conflates their states.

## Recipe 1 — Breakpoint Probe (断点探测)

Before dispatching, detect which SDD stage the target project is currently at, so the entry can resume from the breakpoint instead of restarting:

```bash
ssh -o RemoteCommand=none <alias> \
  "cd <project-dir> && git branch --show-current; git log --oneline -3; ls .specify/specs/ 2>/dev/null"
```

Read the three signals together (branch name, recent commits, spec directory contents) against the project's terminal-state authority document (e.g. `docs/design/target-state.md`) to decide the resume stage. The probe MUST also cover the terminal case: after `/speckit.review`, the only remaining step is merging the feature branch — treat that as a stage too.

## Recipe 2 — Stage Prompt File (阶段化 prompt 文件)

Each stage gets a complete instruction file written to the remote host via heredoc, one file per line and stage:

```bash
ssh <alias> "cat > /home/<run-user>/prompt-<line>-<stage>.md" <<'EOF'
<prompt body>
EOF
```

Fixed skeleton for the prompt body:

1. **Background & authority** — the project's terminal-state document, the constitution, and the previous stage's commit hash.
2. **Execution requirements** (discipline defaults; each line has a framework owner — reference, never re-derive):
   - execute directly, do not ask for confirmation; interview-style questions are decided by the subagent itself **with the assumption recorded** (see `.specify/shared/guidelines/fast-fail.md`);
   - commit only this feature's artifacts; leave pre-existing dirty files untouched and uncommitted (see `.specify/shared/workflow/artifact-commit-step.md`);
   - do **not** push — remote push stays a destructive-class gate requiring explicit authorization (see `.specify/shared/guidelines/confirmation-gates.md`).
3. **Completion sentinel** — the last line of output MUST be the stage sentinel `<STAGE>-DONE` (e.g. `PLAN-DONE`); it is a *necessary* condition only, never sufficient on its own (see the pattern doc's verification rule).

## Recipe 3 — Runner Script & Derivation (runner 脚本与派生)

Wrap the CLI invocation in a per-line, per-stage runner script so the loop never re-types commands:

```bash
# /home/<run-user>/run-<line>-<stage>.sh
cd <project-dir> && qodercli -w <project-dir> --permission-mode auto \
  -p "$(cat /home/<run-user>/prompt-<line>-<stage>.md)"
```

Derive the next stage's runner from the previous one with a one-line `sed` filename substitution instead of re-authoring — the runner shape is identical across stages; only the prompt filename changes.

## Recipe 4 — Background Execution, Log Return & Polling (后台执行 + 日志回传 + 轮询)

Run the stage in the background with its output streamed to a local log, then poll:

```bash
ssh <alias> "su - <run-user> -c 'bash /home/<run-user>/run-<line>-<stage>.sh'" \
  > /tmp/<line>-<stage>.log 2>&1 &     # background; one ssh stream per line

tail -N /tmp/<line>-<stage>.log        # poll until the sentinel line appears
```

On seeing `<STAGE>-DONE`, write the next stage's prompt file and continue the loop — this polling step **is** the loop's engine (see the pattern doc). On seeing the sentinel missing past the stage timeout, treat it as a stall, not a silence (pattern doc's stall handling).

**Observation surface — honest limits**: `qodercli -p` (print mode) buffers output until process exit, so this recipe observes the run at **stage granularity only** — the log stays quiet until the stage ends. The External Dispatch Visibility Contract in [`subagent-definitions.md`](../definitions/subagent-definitions.md) requires stream-level observability (`--output-format stream-json` + compacted live log) whenever mid-run progress, stall detection, or debugging surface is needed. Rule of thumb: sentinel-granular polling suffices for short, bounded stages where stage-boundary detection is the only need; switch the runner to stream-json output (or reuse `.specify/skills/internal/create-team/scripts/dispatch.sh`) for long stages, hard stall thresholds, or anything a human may need to debug mid-flight.

## Recipe 5 — Local Variant: Brief File First (本地简报先行)

For the local topology with a large requirement context, write the context to a brief file first (e.g. `/tmp/<topic>-sdd-brief.md`) and keep the subagent prompt minimal: "read the brief in full, then run `/speckit.requirements`". A file-backed brief is more stable than inlining the whole context in the prompt.

When multiple specs progress in parallel on one project, the prompt MUST declare the concurrency isolation explicitly (which pre-existing uncommitted areas are not read/modified/committed by this line) and the "main session commits after review" boundary. An isolated item that later needs access is unblocked only by an explicit, per-item, bounded **narrow-read authorization** — never implicitly.

## Recipe 6 — Role-Split Variant (构建固化分线)

On one host, split by role into parallel lines: one run user solidifies infrastructure in the host-side project, another solidifies build configuration in the workspace project. Same recipes, two `(user, dir)` parameter sets running concurrently.

## Boundary

- **What this document is not**: the contract that makes a dispatch observable lives in [`subagent-definitions.md`](../definitions/subagent-definitions.md); the decision of *whether* a progression should run as an unattended loop lives in [`unattended-loop-pattern.md`](../patterns/unattended-loop-pattern.md). If a recipe here and the contract disagree, the contract wins — fix the recipe.
- **Not a team substitute**: these recipes drive raw agent CLIs; structured multi-member runs with verifier seats and stall protocols belong to teams (`/speckit.team`), whose dispatch goes through the reference wrapper `.specify/skills/internal/create-team/scripts/dispatch.sh`.
