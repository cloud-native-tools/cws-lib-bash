# Unattended Loop Pattern (无人值守循环模式) — A Design Pattern for Multi-Stage Progressions

A reusable design pattern for any unit whose job is to drive a **bounded sequence of stages to completion with zero mid-run user reminders**: the orchestrator advances from stage to stage automatically — probing where the work currently stands, dispatching each stage, watching for its completion sentinel, independently verifying the claimed completion, and continuing — until every stage is done and the work is closed out.

The pattern's promise is captured by its motivating ruling: *"需要使用一个循环来完成这项工作，而不是每次由我提醒你『重试』或者『继续』"* — one entry prompt declares **goal and starting point**; the mechanism carries every execution detail.

Where [`interview-pattern.md`](interview-pattern.md) converges shared understanding *with* the user (human-in-the-loop), this pattern removes the human from the loop: interview-style questions that arise mid-run are decided by the executor **with the assumption recorded**, never bounced back to the user.

## When to Apply (适用判据)

Apply this pattern when **all** of these hold:

1. The work decomposes into a **bounded, ordered stage sequence** (e.g. an SDD lifecycle: requirements → clarify → plan → tasks → implement → review → merge), each stage producing checkable artifacts.
2. Each stage's completion is **machine-checkable** — a declared sentinel plus independently verifiable artifacts — so "done" never rests on the executor's self-report alone.
3. **Unattended operation is the requirement**: no user is available to say "continue", "retry", or "the answer is X" between stages.
4. Interruptions are expected and must be **resumable**: the entry may fire at any stage, so the current stage is detectable from durable state, not from the (long gone) session context.

Do **not** apply when any stage needs a user decision that cannot be resolved by recorded rules — that need converts the run back to human-in-the-loop (use [`interview-pattern.md`](interview-pattern.md) for the decision point, then resume).

## Boundary: What This Is Not (概念消歧)

| Mode | Information source | Terminates when | Human position |
|------|--------------------|-----------------|----------------|
| **Unattended loop** (this pattern) | Durable project state + the stage set | All stages verified done, or stall/budget exhausted (then reports and stops) | Absent mid-run; entry declares goal + breakpoint; receives the final report |
| **Iteration loop** ([`operating-loops.md`](../../skills/internal/create-team/references/operating-loops.md)) | Agents' own output scored against quality dimensions | Quality threshold or `max_iterations` | Sets the threshold, then observes |
| **Continuous loop** (same reference) | An unbounded stream of incoming work | Never — operates on a cadence | May be absent; kill-switch/budget instead |
| **Long-run mode** (implement 长跑, in-process) | A single command's internal state file | The command finishes or stagnates | Absent, but scope is one command, not cross-stage orchestration |
| **Interview** ([`interview-pattern.md`](interview-pattern.md)) | The user's tacit knowledge | The user confirms stability | Answers every round |

**判定口诀 (rule of thumb)**: 有界阶段集、完成可机检、中途无人 → unattended loop；靠打分逼近阈值 → iteration；源源不断的工作流 → continuous；单命令进程内长跑 → long-run；需要用户逐轮拍板 → interview。

**Carrier, not competitor (承载与模式)**: this pattern is knowledge — the *shape* of the loop. Its hard requirements (self-iteration, independent stage verification, stall handling) are carried by whatever executes the loop: in the SDD instantiation they are solidified into a **self-contained, portable skill** that any host agent loads **without** the spec-kit framework on the executor side (only the target projects that the driven subagents work in need `.specify/`); where the framework *is* present, a Team (iteration pattern, verifier seat, budget/cadence) is an optional richer carrier, never a requirement. The per-unit loop discipline cards inside skill/team templates (WHEN→SEE→DO→CHECK→STOP→LEAVE) are this pattern's single-unit cousins; cross-stage orchestration is what this pattern adds.

## Core Model (核心模型)

- **Stage set (阶段集)** — the ordered stages the loop drives, fixed by the mechanism (for SDD: the six `/speckit.*` stages plus merge). Each stage has a name used in sentinels and state.
- **Stage sentinel (阶段尾标)** — the executor's declared completion marker: the last output line is `<STAGE>-DONE`. It is a **necessary** condition only.
- **Independent verification (独立校验)** — the **sufficient** condition: a verifier that is not the executor checks the stage's artifacts (git log for the expected commit, spec file existence, discipline compliance). Sentinel without verified artifacts is a **fake-done and counts as not-done** — never advance on self-report.
- **Breakpoint probe (断点探测)** — on entry, detect the current stage from durable state (branch name, recent commits, spec directory, terminal-state document) and resume from there. Resume is the **default**, including the terminal case where review is done and only the merge remains.
- **State spine (状态脊)** — each line's stage/retry/status lands in a durable, per-line state record the moment it changes; a fresh context can take over the line from the spine alone. Cross-cycle memory lives in the spine, not in any session.
- **Budget & cadence (预算与节奏)** — per-stage timeout, retry cap, and resource budget are entry-overridable parameters with defaults; they bound how long the loop may keep itself alive.

## The Loop (循环 U0–U6)

```text
U0 ENTRY     one-shot prompt: goals, lines, breakpoints (or "probe"), terminal-state authority
U1 PROBE     per line: detect current stage from durable state (breakpoint probe)
U2 DISPATCH  write stage prompt file + runner, launch in background (recipes: external-dispatch-recipes.md)
U3 WATCH     poll the line's log for the sentinel OR the stage timeout
U4 VERIFY    sentinel present AND independent artifact check passes → advance; else → U5
U5 STALL     timeout / retry cap / budget exhausted → stop the line, land state spine,
             report upward (fast-fail: an anomaly halts, never waits silently)
U6 LEAVE     all lines done → close out: merge each line's work per the merge discipline,
             summarize per-line terminal state back to the user in one report
```

The **U3→U4→U2** cycle is the loop's engine: sentinel seen, verification passed, next stage's runner derived from the previous one and relaunched — no user turn in between. Parallel lines are independent loop instances sharing the orchestrator, one connection and one state spine per line.

## Discipline Defaults (纪律缺省)

The stage prompt skeleton carries the unattended-safe defaults, each owned by an existing discipline (referenced, not restated): execute directly and record assumptions instead of asking; commit only this feature's artifacts; pre-existing dirty files are left untouched; remote push stays behind its destructive-class confirmation gate; anomalies halt and report instead of being patched over silently. The skeleton lives with the dispatch recipes — [`external-dispatch-recipes.md`](../workflow/external-dispatch-recipes.md) — and both documents treat it as the single home of the prompt-shape knowledge.

## Boundary

- **Merge closure is a gated action**: closing a line may require pushing the feature branch or merging to the trunk; those remain destructive-class actions — the loop stops at the gate and surfaces it, unless the entry explicitly authorized the merge/push up front.
- **No stage-internal redesign**: the pattern drives stages as opaque units; it does not reach into how a stage's command works internally.
- **Failure is a state, not a silent wait**: every stall path terminates in a written state spine plus a report — an unattended run that goes quiet is the one unacceptable outcome.
