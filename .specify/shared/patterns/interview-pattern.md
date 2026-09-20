# Interview Pattern (访谈模式) — A Design Pattern for Commands, Skills & Agents

A reusable design pattern for any unit whose job is to extract information that **only the user has**, through many rounds of live interaction, while **continuously writing every answer through to a target artifact**, until the user confirms a stable shared understanding.

Where [`reconcile-pattern.md`](reconcile-pattern.md) converges a *durable artifact space* toward a describable ideal form, this pattern converges a *shared understanding* between the agent and the user. The information source is the user's head; the terminator is the user's confirmation.

## When to Apply (适用判据)

Apply this pattern when **all** of these hold:

1. The needed information is **tacit** — it lives in the user's head (intent, preference, priority, trade-off acceptance) and is **not derivable** from the repo, the filesystem, the tools, or the web.
2. The decisions **branch**: an answer changes which questions are even askable next, so a fixed questionnaire cannot cover the space.
3. There is a **target artifact** that must absorb every answer and stay current — the session produces a converged document, not a chat transcript.
4. A **live user** is answering. The mode is human-in-the-loop by construction.

Do **not** apply to: facts the agent can look up itself (that is the agent's job — see [Fact vs Decision Split](#fact-vs-decision-split-事实归我决策归你)); a single preview→confirm gate; read-only analysis or reporting; unattended / fire-and-forget runs.

## Boundary: What This Is Not (概念消歧)

This pattern is easily confused with four neighbours that also involve "repeated rounds + LLM judgment + a converging artifact". The root differences are **where the information comes from** and **what ends the loop (信息来源 + 终止语义)**:

| Mode | Information source | Terminates when | Human position |
|------|--------------------|-----------------|----------------|
| **Interview** (this pattern) | The **user's tacit knowledge** | The frontier is empty **and** the user confirms the understanding is stable | Answers every round; the loop cannot advance without them |
| **Reconcile** ([`reconcile-pattern.md`](reconcile-pattern.md)) | A durable **artifact space** with a describable ideal form | Current state matches desired state within the tolerance band | Present per invocation, gating destructive actions |
| **Iteration loop** ([`operating-loops.md`](../../skills/create-team/references/operating-loops.md)) | The **agents' own output** scored against quality dimensions | A quality threshold is reached, or `max_iterations` is hit | Sets the threshold, then largely observes |
| **Continuous loop** (same reference) | An unbounded **stream of incoming work** | Never — it operates on a cadence | May be absent at L3 (kill-switch/budget instead) |
| **Confirmation gate** | Already-computed agent output | One preview→confirm exchange | Approves or rejects once |

**判定口诀 (rule of thumb)**: 信息只在用户脑子里、且答案会长出新问题 → interview；有可描述的制品理想形态要反复收敛 → reconcile；靠打分逼近阈值 → iteration；源源不断的工作流 → continuous；只需一次点头 → confirmation gate。

**Nesting, not competitors (嵌套关系，不是竞品)**: an interview **feeds** downstream work — its converged artifact becomes the input to a reconcile run, a plan, or a team's execution. It never replaces them, and they never replace it: no amount of reconciling or scoring can recover a decision the user was never asked about.

**Near-synonyms not to conflate (容易张冠李戴的近义概念)**:
- 前沿 frontier (interview: which questions are askable *now*) ≠ 容忍带 tolerance band (reconcile: which diffs are worth converging)
- 用户确认稳定 (interview: the exit gate) ≠ 质量阈值 (iteration: a score) ≠ 一次性预览确认 (confirmation gate)
- 访谈台账 interview ledger (which branches were decided, by whom, when) ≠ audit log (reconcile: what was written) ≠ STATE.md (continuous: cross-run memory)

## Core Model (核心模型)

- **Design tree (决策树) / dependency DAG** — the decision space as a graph: every decision branches into the decisions that hang off it. Answering "use a queue" creates "which queue", "what retry policy", "what dead-letter behavior"; those questions did not exist before the answer. It is a **DAG, not strictly a tree** — one decision may rest on several premises — and it is **persisted, not remembered** (see [Decision Records](#decision-records-决策记录)). An unpersisted tree cannot propagate a retraction.
- **Decision record (决策记录)** — each decision is a row carrying a **stable ID**, its **`dependsOn` premises**, the answer, and the **artifact span** it wrote. These three fields are what make the rest mechanical: dependencies drive re-asking, the span drives precise rollback, and the ID keeps both stable across sessions.
- **Isolation planning (隔离规划)** — at `I1`, group the tree into branches that are as **independent** as possible and record which decisions are known to interact. Cheap up front, and it is what limits rework: a retraction inside a well-isolated branch invalidates that branch only, while a hidden cross-branch coupling invalidates work the user already paid for.
- **Frontier (前沿)** — every decision whose prerequisites are **already settled**: the questions that can be asked *now* without guessing at answers not yet heard. A question that depends on another question still open belongs to a **later round**, not this one.
- **Round (轮次)** — ask the **whole frontier at once**, each an **open question** (no option menu, no recommended answer — see the question format); then **wait**. One question per round when the frontier is wide wastes the user's time; asking a blocked question forces the agent to guess.
- **Write-through (即答即落)** — every round's answers land in the target artifact before the next round is asked. The artifact, not the conversation, is the deliverable.

## The Interview Loop (访谈环 I0–I6)

```
- [ ] I0 Resolve target + ledger; declare conventions once; resume if a ledger exists
- [ ] I1 Seed / refresh the design tree + plan branch isolation  → artifact: decision records
- [ ] I2 Compute the frontier
- [ ] I3 Dispatch fact-finding probes (non-blocking)
- [ ] I4 Ask the whole frontier in one round, then WAIT
- [ ] I5 Write through to the artifact + records (ID, dependsOn, span)
        └─ frontier non-empty → back to I2
- [ ] I6 Retraction (any round, on user request): invalidate descendants →
        roll back their spans → re-open them → back to I2
- [ ] Exit gate: present the consolidated understanding → explicit user confirmation
```

- **I0 — resolve & resume**: identify the **target artifact** (what converges) and the **ledger location** (see [State & Resumability](#state--resumability-状态与续跑)). Declare the session's conventions **once** — granularity, how decisions are recorded, the done-criterion for a branch — so they are not renegotiated every round. If a ledger already exists, read its header conventions (**never renegotiate them**) and resume from the first unsettled branch.
- **I1 — seed the tree & plan isolation**: build the initial decision graph from the target artifact's current content, a scan of the surrounding repo/context, and this run's user input. Mark what is already settled — never re-ask a decision the artifact already records. Then **plan the isolation**: group decisions into branches that can be settled independently, record the known couplings between them, and order the branches so that the decisions with the **most descendants are asked first**. Asking a widely-depended-on premise late is what turns one retraction into a session's worth of rework.
- **I2 — compute the frontier**: select every decision whose prerequisites are settled. Defer the rest explicitly; a deferred question is *scheduled*, not dropped.
- **I3 — dispatch probes (non-blocking)**: when a frontier question needs an **environment fact**, dispatch a subagent to find it instead of asking the user. Do **not** block the round: a running probe is an unsettled prerequisite, so only the questions downstream of it wait — ask the rest of the frontier now.
- **I4 — ask one round, then wait**: present the whole frontier in the [question format](#question-format-提问格式契约) below — each question **self-contained** (why it arises now, which earlier decisions it builds on, named rather than cited by ID, and what the answer will change) and **open-ended**, with no option menu and no recommended answer. Then **stop and wait**. Do not answer on the user's behalf; do not proceed on silence.
- **I5 — write through & record**: record each decision into the target artifact **overwrite-style — the latest round wins**, so the artifact never accumulates contradictory rounds. For every decision, persist its **ID**, its **`dependsOn`** premises, and the **artifact span** it wrote (section / anchor / line range — whatever the artifact supports). **Check each answer against the already-settled decisions**: if it contradicts one, do not silently overwrite — surface the conflict, name both decisions, and let the user pick which one gives way (picking the older one is a retraction, so it goes to `I6`). Then recompute the frontier (`I2`): each answer reshapes the graph, pushing the frontier outward and unblocking what depended on it.
- **I6 — retraction (翻供传播)**: the user may change any earlier answer at any time; this is expected, not an exception. On a retraction of decision `D`:
  1. **Collect the transitive descendants** of `D` from the persisted `dependsOn` edges — everything reachable, not just the immediate children.
  2. **Classify each** against the new answer: **still valid** (the answer does not actually rest on what changed — say why), **needs confirmation** (plausibly still right; re-ask it openly, showing the prior answer as context so the user can see what they said before — not as a recommendation to accept), or **invalidated** (its premise is gone).
  3. **Roll back the invalidated spans** in the target artifact using each record's span, so no text derived from a retracted premise survives. This is why the span is persisted.
  4. **Re-open** the invalidated decisions (status back to open) and let `I2` bring them back into the frontier — re-asked in dependency order, not all at once.
  5. **Record the retraction** in the ledger: what changed, which descendants were invalidated, which were kept and why. A retraction that leaves no trace is indistinguishable from an inconsistency.

  Never silently keep a descendant whose premise changed, and never quietly re-derive it without asking — the first corrupts the artifact, the second fabricates a decision.
- **Exit gate**: the session is done when the frontier is empty — every branch visited, nothing silently assumed, **no unresolved conflicts, and no descendant left stale by a retraction**. Present the consolidated understanding and obtain **explicit user confirmation**. **Never act on the design before that confirmation**; an empty frontier is the agent's opinion, the confirmation is the user's. A retraction raised *at* the gate sends the run back to `I6` — the gate is not a point of no return.

### Question Format (提问格式契约)

A question the user has to decode is a question they answer badly. Every question therefore ships with **its own context** — the user must be able to answer it without scrolling back, reconstructing what was decided earlier, or asking what a word means.

Each question carries four parts:

1. **Identity** — its decision ID, so the user has a handle to retract by later.
2. **A plain-language title** — what is being decided, in the user's vocabulary.
3. **Context (为什么现在问这个)** — why this question arises now, **what earlier decisions it builds on (spelled out, not as bare IDs)**, and what the answer will change in the target artifact. Render it as a **markdown blockquote (`> `)** so it is visually separable from the question being asked: the user's eye should find the background and the question as distinct blocks. This is the part most often skipped and most often the reason an answer is wrong.
4. **An open question** — asked so that the answer space stays the user's to define. **No option menu, no recommended answer.**

```
❓ **D4** — **Retry behaviour for failed messages**

> **Context**: You chose a message queue for storage (D1) and Redis as the queue (D3).
> Redis Streams has no built-in retry limit, so whatever we do here we have to build.
> Your answer will be written into `## Storage > Retry policy` of `plan.md`, and it
> shapes what happens to a message that keeps failing — including whether we need a
> holding area for messages that exhausted their retries.

What should happen when processing a message fails?
```

### No Options, No Recommendation (访谈 ≠ 澄清)

This is the load-bearing difference from a clarification pass, and it is easy to get wrong because both flows "ask the user questions":

| | **Clarify (澄清)** | **Interview (访谈)** |
|---|---|---|
| The answer space | **Already known** — bounded by the artifact, the taxonomy, the code | **Unknown** — it is what the interview is for |
| Question shape | Closed: options table + a **Recommended** pick | **Open**: the user defines the space |
| Agent's stance | Proposes; the user ratifies or corrects | Elicits; the user originates |
| Failure it avoids | Ambiguity in something already decided | Presupposing an answer nobody gave |

**Why no options**: an option menu is an assertion that the agent already knows the possibilities. In an interview it usually does not, and presenting three choices makes the user pick the closest one instead of saying the thing that was actually on their mind. The good answer is frequently the fourth option the agent never imagined — anchoring is the exact failure this mode exists to prevent.

**Why no recommendation**: a recommendation converts elicitation into review. That is a *feature* of clarify (faster, and the space is known) and a *defect* here — the user reads the recommendation, finds it plausible, and agrees. What lands in the artifact is then the agent's opinion wearing the user's name, which is the fabrication rule violated by a subtler route.

**When the user is stuck**: after the open question and only if they ask, offer examples **as illustrations, explicitly non-exhaustive** ("some projects do X, others do Y — but tell me what fits yours"). Never renumber them into a menu, and never mark one as recommended. If a question genuinely has a small closed answer space (a yes/no, a choice between two existing files), say so plainly and ask directly — do not manufacture a taxonomy around it.

**Comprehension rules (可理解性规则)** — these are not stylistic preferences; violating them corrupts the answer:

User-facing wording and context rules are defined once in `.specify/shared/guidelines/user-facing-comprehension.md` (this file covers surface class ④); its condition sets MUST NOT be restated here. The four rules that used to be listed here are that document's whitelist, blacklist, and context floor.
- **One decision per question.** A question containing "and" usually holds two decisions — split them, and let the dependency edges order them.
- **Ask what, not whether.** "What should happen when X?" invites the user's actual model; "Should we do X?" narrows it to yes/no and smuggles in a proposal.

### Host Interactive Tools (宿主交互工具)

The governing principle is **capability fit, not tool preference**:

> If the host agent CLI offers a tool that presents a given prompt **more clearly than plain text**, use it. If no available tool fits that prompt, **do not use one** — present the prompt as markdown or plain text. A tool is adopted for what it does for the reader, never because it exists.

Judge fit by the **prompt's shape**, matched against what the tool actually offers:

- **Choice widgets** (this CLI's `AskUserQuestion` is one: 2–4 preset options plus an "Other" escape) fit prompts whose answer space is **genuinely closed and fully enumerable**. They render better than prose, make the prompt unmissable, and record the answer as a real selection.
- The same widget is **wrong for a frontier question**, because that space is unknown — see [No Options, No Recommendation](#no-options-no-recommendation-访谈--澄清). Showing three choices anchors the user to the closest one even with an escape available, since the escape reads as the awkward path. Here plain text *is* the better surface, so the principle says skip the tool.
- Nothing in this section is specific to `AskUserQuestion`. A host offering a **free-text prompt** tool, a form with open fields, or a diff/preview surface should have it used wherever that presents the prompt better than markdown would. Re-judge per host and per prompt; do not hard-code a tool name into the workflow.

Applying that to this loop's prompts:

| Prompt | Surface | Why |
|--------|---------|-----|
| **Frontier questions** (the elicitation itself) | **Markdown / plain text**, open format | The answer space is unknown — no choice widget fits, so none is used |
| Mode / convention choices at `I0` (e.g. which run mode) | Choice widget, if the host has one | A closed, enumerable set the agent legitimately knows |
| Conflict resolution at `I5` (which of two settled decisions gives way) | Choice widget, if available | Exactly two named candidates, both already on record |
| Retraction triage at `I6` (keep this descendant as-is, or re-answer it) | Choice widget, if available | A bounded per-descendant question; the prior answer is shown as context, never as a recommendation |
| Exit-gate confirmation (understanding stable, or reopen a branch) | Choice widget, if available | A yes/reopen decision, enumerable by construction |
| Deferral (park this branch out of scope) | Choice widget, if available | Bounded |

Rules whenever a host tool is used:

- **Options must be the true, complete space** — never a sample of it. If they are not, the prompt belongs in plain text.
- **Never mark an option as recommended** inside an interview prompt, even where the tool supports it.
- **Never bend a prompt to fit a tool.** Inventing options so a frontier question can go through a widget is the anchoring failure with extra steps. The prompt's shape decides the surface, not the reverse.
- **Degrade cleanly and silently.** No suitable tool — or none at all — means markdown or plain text, and the loop's semantics are unchanged. Never let a tool's absence become a reason to skip a question, batch it away, or answer it yourself.
- **The host tool is a presentation layer, not an authority.** It never changes what is asked, only how it is shown.

### Fact vs Decision Split (事实归我，决策归你)

The load-bearing rule of the pattern:

- **Facts are the agent's job.** Anything discoverable — file contents, existing conventions, dependency versions, whether an endpoint exists, what the docs say — is looked up, never asked. Asking the user to be a lookup service is the fastest way to lose their attention.
- **Decisions are the user's.** Intent, priority, trade-off acceptance, naming preference, scope boundaries. Put each one to them and wait. Inferring a decision because it "seems obvious" is fabrication with extra steps.

When a question mixes both, split it: look the fact up, then ask only the decision that remains.

## State & Resumability (状态与续跑)

The **ledger** is the durable state that lets one interview span sessions, days, or agents. Place it nearest to the artifact it serves:

| Context | Ledger location |
|---------|-----------------|
| Inside a feature / spec workflow | `.specify/specs/<feature>/interview-log.md` |
| No feature context | `.specify/memory/session/` (per the memory-as-files layer) |
| The host defines its own ledger | Use it — never open a second parallel ledger |

Rows are **structured columns**, not free text — and they are what makes conflict handling and retraction mechanical rather than a guess:

### Decision Records (决策记录)

```markdown
# Interview Ledger: <topic>

- **Started**: <date>
- **Target artifact**: <path>
- **Branches**: <branch-a (isolated) | branch-b ↔ branch-c (coupled: <what couples them>)>
- **Granularity**: <one branch per round | …>
- **Recording**: overwrite-style; latest round wins
- **Done criteria**: <what makes a branch settled>
- **Status legend**: ⬜ open / 🔄 asked, awaiting answer / ✅ settled / ⏭ deferred-out-of-scope / ↩︎ retracted (superseded)

| ID | Round | Branch | Question | dependsOn | Status | Decision | Artifact span | Superseded by |
|----|-------|--------|----------|-----------|--------|----------|---------------|---------------|
| D1 | 1 | <branch> | <Q title> | — | ✅ | <answer> | <section / anchor / lines> | |
| D4 | 2 | <branch> | <Q title> | D1, D3 | ⬜ | | | |
```

- **`dependsOn`** is the edge set the retraction walk (`I6`) traverses. An unrecorded dependency is an invisible one: its descendant will silently survive a premise change.
- **Artifact span** is what makes rollback precise. Without it, undoing a retracted decision means re-deriving the whole artifact by hand.
- **Superseded by** links a retracted decision (↩︎) to the record that replaced it, so the history reads as a chain rather than a contradiction.

#### Engine (程序优先)

Graph reachability, ordering, and cycle detection are **fixed-rule computations**, so they belong to a program — never re-derived in prose by the model (Principle XII / token-efficiency Program-First). The engine is `scripts/python/interview-utils.py` (`<TOOL:.specify/memory/tools/interview-utils.py.md>`), backed by a JSON sidecar beside the markdown ledger (`interview-log.md` → `interview-log.dag.json`):

```bash
E=.specify/scripts/python/interview-utils.py; L=<ledger>.md
python3 $E init   --ledger $L --target <path> [--mode special|informal] [--branch NAME ...]
python3 $E add    --ledger $L --id D4 --question "…" [--depends-on D1 ...] [--branch NAME]
python3 $E answer --ledger $L D4 --decision "…" --span "## Section" [--round N]
python3 $E frontier    --ledger $L --json   # askable now, deep premises first
python3 $E order       --ledger $L --json   # full topological order (I1 ordering rule)
python3 $E descendants --ledger $L D3 [--direct]
python3 $E retract     --ledger $L D3 [--decision "…"] [--apply]   # dry-run by default
python3 $E conflicts   --ledger $L --with "<candidate answer>"
python3 $E status      --ledger $L --json   # counts, stale rows, exit-gate readiness
python3 $E render      --ledger $L          # regenerate the markdown table
```

Exit codes: `0` ok · `2` input error · `3` not found · `4` validation failed (cycle / blocked answer). A non-zero exit is a **verdict** — report it, never argue around it.

The division of labour is strict:

| Engine owns (deterministic) | The model owns (judgement) |
|-----------------------------|----------------------------|
| Frontier computation, topological order, descendant-count ordering | Which decisions exist, and how the space decomposes into branches |
| Cycle rejection at insertion; refusing to answer a blocked decision | Wording the open questions and their context |
| Transitive descendant walk; which spans need rollback; re-opening them | Classifying each descendant as still-valid / needs-confirmation / invalidated |
| Narrowing conflict **candidates** by shared terms | Deciding whether two decisions truly conflict |
| Exit-gate readiness (nothing open, nothing stale) | Presenting the consolidated understanding and asking for confirmation |

`retract` is **dry-run by default** so the blast radius is shown before anything is touched, and it never edits the target artifact — rolling back the reported spans stays the caller's job, since only the caller knows how to edit that artifact.

Operating rules:

- **Checkpoint at round boundaries only.** When turns or time run out, stop after a completed round — never mid-round with answers unrecorded. End every session with the ledger fully written; start every session by re-reading it.
- **IDs are stable and never reused.** A retracted `D3` stays `D3` (↩︎, superseded); the replacement gets a new ID. Reusing an ID silently rewrites history and breaks every `dependsOn` pointing at it.
- **No settled decision without its edges and span.** A round does not close until every answer it settled has recorded `dependsOn` and its artifact span. Backfilling these later is guesswork, and it is exactly what a retraction cannot survive.
- **Retract, never delete.** A superseded decision keeps its row (↩︎ + `Superseded by`), so the artifact's current state stays explainable by its history.
- **Tell the user retraction is available.** Say up front that any earlier answer can be revisited and that the mechanism will re-ask what depended on it. Users who believe an answer is final either over-deliberate or quietly live with a wrong one.
- **Unseen branches stay ⬜.** Skipping ahead and inventing the user's answer is the one unrecoverable failure mode of this pattern: the artifact then looks converged while encoding decisions nobody made.
- **Deferred is explicit.** A branch ruled out of scope is ⏭ with the reason, not silently dropped.

## Embedding Contract (宿主接入契约)

A unit claiming this mode must declare four things: the **target artifact**, the **ledger location**, the **exit gate**, and its **round budget** (unbounded, or a cap with an escalation path). Per host type:

| Host | Declares | Additional obligation |
|------|----------|-----------------------|
| **Command** | An `## Interview Mode` section naming the pattern, the target artifact, the ledger, and the exit gate | If it caps rounds/questions (like a bounded clarification pass), name the escalation path to an unbounded interview |
| **Skill** | The same four items in its `SKILL.md` | A **non-interactive escape hatch**: when no live user is available, degrade to a declared default and say so — never fabricate answers |
| **Agent / team member** | The mode in its workflow section, plus the human-in-the-loop constraint | Which team pattern it runs under, and what a fire-and-forget subagent invocation is allowed to do (process the requested batch against the durable ledger, then return) |

A host may **narrow** the pattern (fewer rounds, a fixed taxonomy of questions) but may not drop the write-through rule, the persisted decision records (ID + `dependsOn` + span), retraction propagation, the self-contained **open**-question format (mandatory context, no preset options, no recommended answer), the fact/decision split, or the user-confirmation exit gate, or the pointer to the comprehension discipline (which a host narrowing this pattern MUST NOT drop).

## Adoption Map (接入图谱)

Where the pattern already lives in this project, and where it fits:

| Unit | Relationship |
|------|--------------|
| [`interview-walkthrough.md`](../workflow/interview-walkthrough.md) | **Instance** — the requirements domain: interview units, decision cards, verification levels, delivery-loop coupling. Its "open main question first, never preset the answer space" rule is this pattern's rule, field-proven |
| `/speckit.interview` | **Instance** — the standalone, general-purpose entry for running the pattern on any target artifact |
| `/speckit.clarify` | **Sibling flow, not an instance.** It asks *closed* questions (options table + a **Recommended** pick) because its answer space is already bounded by the artifact and its taxonomy — the opposite stance to this pattern. It borrows only the context discipline and the fact/decision split, and **escalates here** when the space turns out to be unknown rather than merely ambiguous |
| `/speckit.goal` (`create`) | **Partial instance** — the objective and criteria are elicited **openly** per this pattern (the user's outcome, not a menu); the identity slug is a mechanical field, not an interview question |
| `/speckit.plan` | **Opt-in escalation** — when design decisions are underdetermined, interview instead of fabricating a design |
| `create-team` | **Opt-in escalation** — eliciting a missing goal, and deriving roster/pattern when the goal underdetermines them |
| `summarize-project`, `create-skills`, `study-project` | **Pre-existing narrower loops** — gate-by-gate confirmation, one-question-per-round authoring, ≤3-per-round scoping. Conformant as-is; when next revised, check each question against the open-question rule before citing this pattern |
| `/speckit.analyze`, `/speckit.review`, `/speckit.implement`, `/speckit.history`, `/speckit.feature` | **Bad fit — do not adopt.** Read-only diagnosis, mechanical execution, or automated distillation: there is no tacit information to elicit |

## Anti-patterns (反模式)

- **Interrogating for discoverable facts**: asking the user what the code, config, or docs already say.
- **Tree in the agent's head**: keeping the design tree unpersisted. It works until the first retraction, then there is no way to know what depended on what — so the artifact silently keeps decisions whose premise is gone.
- **Settling without edges**: recording an answer with no `dependsOn` and no artifact span. Both are unrecoverable after the fact, and both are what retraction runs on.
- **Retraction as a local edit**: changing one answer and moving on, leaving descendants that were derived from the old one. The artifact then reads as consistent while encoding two incompatible premises.
- **Silent conflict resolution**: quietly overwriting an earlier settled decision because a later answer contradicts it. Name both and let the user choose which gives way.
- **Deep premises asked late**: settling a widely-depended-on decision after the branches that rest on it, so one retraction invalidates a whole session's work. Order by descendant count at `I1`.
- **Context-free questions** and **jargon / bare abbreviations**: both are governed by the comprehension discipline named in the header pointer, which owns the conditions and the context floor; the labels stay here so the anti-pattern list remains navigable.
- **Presetting the answer space**: offering an option menu in an interview. Three choices make the user pick the closest one instead of saying what was actually on their mind — and the good answer is usually the option the agent never imagined. That is clarify's shape, not this one.
- **Recommending an answer**: it turns elicitation into review. The user finds the recommendation plausible, agrees, and the artifact records the agent's opinion under the user's name — fabrication by a subtler route.
- **Widget-driven questioning**: inventing 2–4 options for a frontier question so it can be asked through a choice widget. The tool's schema is not a reason to preset an answer space — the prompt belongs in plain text.
- **Asking "whether" instead of "what"**: a yes/no question smuggles in a proposal and collapses the space the interview was meant to open.
- **Compound questions**: one question holding two decisions ("should we retry, and how many times?"). Split them so each can be answered, recorded, and retracted independently.
- **Drip-feeding**: one question per round while the frontier holds five askable questions.
- **Asking blocked questions**: putting a question whose prerequisite is still open, then guessing the prerequisite to interpret the answer.
- **Accumulating without writing through**: banking several rounds of answers "to integrate later" — the artifact drifts from the conversation and the session becomes unresumable.
- **Append-only recording**: stacking every round into the artifact so it holds mutually contradictory decisions. Overwrite; latest round wins.
- **Self-certified completion**: declaring shared understanding and acting on it without the user's explicit confirmation.
- **Fabricated answers**: filling in unseen branches to make the artifact look finished.
- **Unattended interviewing**: running the mode with no live user instead of degrading to the declared non-interactive default.
