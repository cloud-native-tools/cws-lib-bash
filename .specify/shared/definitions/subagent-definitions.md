# Subagent Definitions Reference

Canonical definition of a **Subagent**, its three execution modes, the mode-selection rules, and the visibility contract for external CLI dispatch. This file is the single source of truth for the Subagent concept; other documents (`/speckit.agents`, `/speckit.team`, `skills/create-team`) link here rather than re-defining it.

**Position in the Agent taxonomy**: a subagent is the **Agent Execution** layer of the three-layer model defined in [`agent-definitions.md`](agent-definitions.md) — *Agent Template → Agent Instance → Agent Execution* — viewed from the orchestrator that delegated it. This document governs only the Execution layer: how an Agent Instance's definition becomes a live run, and how that run stays observable.

## What a Subagent Is

A **Subagent** is a **task-scoped delegated worker**: an orchestrator (the main session or a team supervisor) hands it a bounded task brief plus an **independent prompt and configuration**, it executes autonomously within that scope, and it delivers a result through an agreed contract (returned message, result manifest, or declared output paths).

Three properties hold regardless of execution mode:

1. **Independent prompt & config** — the subagent runs under its own system prompt / tool list / model settings, derived from its **Agent Instance** definition (`.specify/agents/instances/<name>.agent.md`, or a Template under `.specify/agents/templates/`) plus its dispatch config (`.specify/agents/execution/configs/<name>.yaml`) or dispatch payload, not from the orchestrator's conversation.
2. **Bounded task scope** — it receives exactly one task brief (plus its territory manifest in team runs), never the orchestrator's full history.
3. **Result contract** — completion is signalled through a defined channel, so the orchestrator can tell "done" from "still running" from "failed".

A subagent is a running **Agent Execution**; the **Agent Instance** is the definition it is launched from (which in turn derives from an **Agent Template** — see [`agent-definitions.md`](agent-definitions.md)). The same Instance can be executed multiple times, sequentially or concurrently, without affecting the definition.

## Three Execution Modes

The word "subagent" covers three materially different execution mechanisms. Keep them distinct — they differ in isolation, parallelism, and how (or whether) their progress is observable.

| Mode | Mechanism | Isolation | Parallelism | Progress visibility |
|------|-----------|-----------|-------------|---------------------|
| **1. Native subagent** | The executing agent runtime dispatches subagents itself (e.g. Claude Code `Agent`/`Task` tool, Qoder CLI native subagents) | Runtime-managed context isolation | Runtime-dependent (Claude Code: parallel calls in one block) | Native — the host UI renders the subagent's activity |
| **2. Virtual subagent** | The executing tool has **no** subagent capability; the current session *simulates* one: it adopts the agent definition's independent prompt/config and executes the task itself, in-session | None — shares the session's context, budget, and tools | None — strictly sequential | Inline — work happens in the visible session, but consumes its context |
| **3. External subagent** | The orchestrator launches a **real, separate agent process** via shell (`qodercli -p …`, `claude -p …`) | Full process & context isolation | True OS-level parallelism | **Not automatic** — MUST follow the Visibility Contract below |

### Mode notes

- **Native** is the default whenever the executing runtime supports it: isolation and observability come for free, and lifecycle is managed by the harness.
- **Virtual** is a fallback for subagent-less tools. It preserves the *authoring* benefits of agent definitions (independent prompt/config, bounded brief) but none of the *runtime* benefits: no isolation, no parallelism, and the subagent's work consumes the session's own context window. Keep virtual subagent tasks small.
- **External** buys real isolation and parallelism and survives long-running work (optionally detached via `nohup`/`setsid` so the foreground session can exit). Its cost: the child process is a black box unless the dispatch is wired for visibility — which is exactly what the contract below fixes.

## Mode Selection

Choose per dispatch, per member, by scenario — not by habit:

| Scenario | Recommended mode |
|----------|------------------|
| Interactive single-task delegation; runtime supports subagents | Native |
| Executing tool lacks subagent support; lightweight sequential delegation | Virtual |
| Long-running task that must survive the foreground session | External (detached) |
| Parallel fan-out (team parallel dispatch, cross-repo analysts) | External (or native parallel calls when the runtime supports them and the task is short) |
| Team orchestration with stall detection / progress monitoring requirements | External with the Visibility Contract |
| Subagent must use a different model/config than the orchestrator and the runtime can't override per-dispatch | External (CLI flags: `--model`, `--reasoning-effort`, `--context-window`, …) |

When in doubt: **native first, virtual as fallback, external when isolation/parallelism/observability requirements exceed what the session can provide.**

## External Dispatch Visibility Contract

**The silent anti-pattern** (observed in real team runs):

```bash
qodercli -p "<prompt>" > agent.log 2>&1 &   # PROHIBITED
```

Print mode (`-p`) buffers **all** output until process exit. The log file stays at 0 bytes for the entire run — the orchestrator and the user see nothing: no progress, no stall signal, no debugging surface. A dispatch you cannot observe is a dispatch you cannot operate.

Every external subagent dispatch MUST therefore:

1. **Stream events** — run the CLI with `--output-format stream-json` (NDJSON, one event per line; supported by both `qodercli` and `claude`).
2. **Compact the stream** — pipe events through a filter that renders one short line per meaningful event (tool calls with key argument, assistant text excerpts, final `DONE` summary with turns/cost/duration).
3. **Emit the artifact triplet** per dispatched agent:
   - `<label>.live.log` — compact progress lines; tailable and monitorable in real time
   - `<label>.jsonl` — raw stream-json events, kept for forensics
   - `<label>.status` — `<label> exit=<code>` recorded at completion
4. **Monitor liveness** — watch `.live.log` growth (bytes/lines); stalled growth beyond the team's stall threshold means a stalled agent, triggering the team's recovery protocol (wait / nudge / terminate / reassign).
5. **Trace the session** — none of the supported agent CLIs exposes an official session-naming/rename mechanism (verified against each tool's official documentation surface; sessions carry auto-generated IDs only). Traceability therefore rides a convention, not a CLI flag:
   - give every dispatch a stable **label** (`<team-slug>--<run-stamp>--<member-role>`) that names the triplet files, and open the dispatched prompt with that label as a prefix line so the session's own transcript is self-identifying;
   - record the dispatch mapping (label → CLI → member → workspace) in the run report — the mapping table, not a renamed session, is the canonical cross-reference surface.

**Reference implementation**: `skills/create-team/scripts/dispatch.sh` (+ `stream-filter.py`) — a generic, CLI-agnostic wrapper implementing the four observability points above (works with `qodercli` and `claude`; override via `DISPATCH_CLI`; the label convention of point 5 is the caller's responsibility). Team runbooks and command workflows SHOULD reuse it instead of re-rolling per-run dispatch scripts.

## Terminology Boundaries

| Term | Meaning | Where defined |
|------|---------|---------------|
| **Agent Template / Instance / Execution** | The three-layer Agent taxonomy; a subagent is the Execution layer | `shared/definitions/agent-definitions.md` |
| **Agent Instance** (a.k.a. agent definition) | Responsibility-bound `.agent.md` (under `.specify/agents/instances/`) a subagent is launched from | `agent-definitions.md`; authored via `/speckit.agents`, `skills/create-agent` |
| **Subagent** (this document) | A running, task-scoped delegated Agent Execution | here |
| **Team** | Multi-agent structure orchestrating several subagents | `/speckit.team`, `skills/create-team` |
| **Tool** | Pre-verified reusable capability record (`.specify/memory/tools/`) | `shared/definitions/tool-definitions.md` |
| **AI agent CLI** | A supported coding agent binary (`qodercli`, `claude`, …) | `docs/reference/cli/` |
