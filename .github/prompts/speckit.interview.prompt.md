<!-- AUTO-GENERATED from templates/commands/interview.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions.

## Positioning

`/speckit.interview` is the standalone, general-purpose entry for **interview mode**. The mode itself — design tree, frontier, rounds, question format, fact-vs-decision split, write-through, ledger, exit gate, anti-patterns — is defined once in `.specify/shared/patterns/interview-pattern.md`. **Read that document and follow it; never restate or re-derive its rules here.** This command owns only the *invocation*: resolving the run mode, the target artifact, and the ledger, then running the loop to the exit gate.

Use it when the information needed lives in the user's head and the decisions branch. It is **not** a clarification pass with a question cap (`/speckit.clarify`), not a design generator (`/speckit.plan`), and not an artifact-space converger (`/speckit.docs`, `/speckit.feature`).

**Against `/speckit.clarify` specifically** — both ask the user questions, and the difference is the answer space. Clarify *澄清*: the space is already bounded by the artifact and its taxonomy, so it asks **closed** questions (options table + a **Recommended** pick) and the user ratifies. This command *采访*: the space is unknown and discovering it is the point, so it asks **open** questions and the user originates. Presenting options here would presuppose the very thing being elicited.

## Glossary

Consult `.specify/memory/glossary.md` and apply `.specify/shared/workflow/glossary.md`: map recorded homophone/confusable variants to canonical terms before acting, surfacing each correction. Vocabulary discipline matters more here than in most commands, and it runs **both ways**:

- **Inbound** — an interview records the user's own words into a durable artifact, so a misheard proper noun propagates into every downstream decision.
- **Outbound** — questions must use the glossary's **canonical** term for a concept. Which terms may stand unexplained, how each is glossed at first use, and what context a question must carry for a reader who opens it alone days later are defined once in `.specify/shared/guidelines/user-facing-comprehension.md`; its condition sets MUST NOT be restated here.

At wrap-up propose new project-specific terms (`origin=auto`, `status=proposed`) with user confirmation.

## Run Modes

Standalone invocation has **two run modes**. They differ in **what is being converged** — one named target versus an unmapped space — and therefore in what each round's write-through does. Both obey the pattern; neither may drop write-through, the fact-vs-decision split, or the user-confirmation exit gate.

Both modes run the pattern's round **unmodified**: compute the frontier, ask **the whole frontier at once** as **open questions** — no option menus, no recommended answers — wait, then write through and recompute. The question unit is *not* what separates them; never drip-feed one question at a time in either mode.

| | **Special Interview (专题访谈)** | **Informal Interview (漫谈访谈)** |
|---|---|---|
| **Purpose** | Pin down **one** thing: complete and sharpen the description/definition of a named file, directory, or concept | **Map a space** whose shape is not yet known: survey broadly, then organize what came back |
| **Target** | **Required and single.** Do not start without one | May start from a bare topic; the artifact set may grow as the space is mapped |
| **Tree scope** | Bounded by that one target — every branch must be a decision *about it*; anything else is recorded as out-of-scope | Spans the whole space; branches may belong to different artifacts, and new areas legitimately appear mid-interview |
| **On write (每轮落盘)** | 边改边反馈: **edit the target in place**, then **echo the change back** — the user sees their decision as recorded text and corrects a misread on the spot | 整理落盘: **consolidate** the round into the record — reconcile answers against each other, group by area, and split or add artifacts as the shape emerges |
| **Converged when** | The target's definition is complete and internally consistent, **and** the user confirms | The frontier is empty, every area has a home, **and** the user confirms |
| **Choose when** | The target exists (or must exist) and its definition *is* the deliverable | You are still exploring and do not yet know which artifacts the answers belong to |

### Mode resolution

Resolve **before the first question**, in this precedence:

1. Named explicitly in `$ARGUMENTS` (`special` / `informal`, or 专题 / 漫谈).
2. **Resuming** — the ledger header's recorded mode wins and is never re-inferred.
3. A concrete existing file, directory, or named concept given as the target → **Special**.
4. Only a broad topic, or several unrelated areas at once → **Informal**.
5. Still ambiguous → ask exactly one question offering both, with a recommendation; then proceed.

State the resolved mode **and why** back to the user, and record it in the ledger header. Switching mid-interview is allowed **only on the user's explicit request**: record it as a header amendment naming the round where it changed. Never switch silently — in particular, never widen Special into Informal to escape a target whose definition is proving hard to pin down.

## Interview Mode

The pattern's four required declarations, as this command sets them (plus the per-mode write behaviour):

| Declaration | This command's value |
|-------------|----------------------|
| **Target artifact** | Resolved in step 3 — required and single in Special; may be a topic-seeded record in Informal |
| **Write behaviour** | Every round writes through before the next is asked. Special edits the one target in place and **echoes the change back**; Informal **consolidates and organizes** the round into records, splitting or adding artifacts as the space takes shape |
| **Ledger** | In a feature context `<REQUIREMENTS_DIR>/interview-log.md`; otherwise `.specify/memory/session/interview-<topic-slug>.md`. Holds the **decision records** (ID, `dependsOn`, artifact span) that retraction propagation runs on, plus the run mode in its header |
| **Exit gate** | Per-mode convergence criterion above → present the consolidated understanding → **explicit user confirmation**; never act before it |
| **Round budget** | **Unbounded** in both modes. This is the escalation target for capped flows; it stops when the criterion is met or the user stops it |

## Outline

1. **Resolve context**: run `.specify/scripts/bash/check-prerequisites.sh --json --paths-only` from repo root once; parse JSON for `REPO_ROOT`, `BRANCH`, `REQUIREMENT_ID`, `REQUIREMENTS_DIR`, `FEATURE_SPEC`, `IMPL_PLAN`, `TASKS`. A non-feature branch is not an error — it selects the non-feature ledger location.

2. **Resolve the run mode** per Mode resolution above, and state it back with its reason.

3. **Resolve the target artifact** (what converges), in this precedence:
   - a path or artifact named in `$ARGUMENTS` → that file (a directory or concept resolves to the document that defines it; if none exists, name the file that will);
   - otherwise, in a feature context, the current phase's primary artifact (`tasks.md` → `plan.md` → `requirements.md`, first that exists);
   - otherwise a new interview record beside the ledger.

   State the resolved target back to the user before asking anything. **In Special mode a single concrete target is mandatory** — if it cannot be resolved, stop and ask for it rather than interviewing against a vague subject.

4. **Writability probe (fail fast)**: verify the target artifact and its directory are writable before generating any questions. If unwritable, STOP with the owning path and a fix command (e.g. `sudo chown -R $USER <dir>`) — never run the loop first and lose the answers at the final write.

5. **Resolve the ledger and resume**: per the table above. If a ledger exists, read its header conventions — **never renegotiate them**, mode included — and resume from the first unsettled branch. Report what is already settled, so it is not re-asked.

6. **Load context summary-first** (see `.specify/shared/guidelines/token-efficiency.md`): read the target artifact (it is the edit target, so read it fully); pull `.specify/memory/features.md` as index rows only; take `.specify/memory/constitution.md`, `research.md`, and `docs/` as **targeted excerpts only when a candidate question actually needs them**. Never bulk-load context "to be safe" — an interview's context grows every round.

7. **Run the loop I0–I6** per `.specify/shared/patterns/interview-pattern.md`. The round shape is the same in both modes — compute the frontier, ask **the whole frontier in one message**, wait, write through, recompute. Every question follows the pattern's question format in full: its decision ID, a plain-language title, a **Context block rendered as a markdown blockquote (`> `)** (why it arises now, which earlier decisions it builds on — **named**, not merely cited as `D3` — and what the answer will change in the target), then **an open question**.

   **No option menus, no recommended answers** — this is an interview, not a clarification. The answer space is what the interview is *for*; presenting choices makes the user pick the closest one instead of saying what was actually on their mind, and a recommendation turns elicitation into review, so what lands in the artifact is the agent's opinion under the user's name. Ask "what should happen when…", never "should we do X?". If the user is stuck and asks for help, offer examples **as explicitly non-exhaustive illustrations**, never renumbered into a menu and never with one marked as recommended.

   **Present each prompt on whatever surface shows it best.** If the host CLI offers a tool that presents a given prompt more clearly than plain text, use it; if no available tool fits, use **markdown or plain text** — a tool is adopted for what it does for the reader, never because it exists. Match the tool to the **prompt's shape**: a choice widget (this CLI's `AskUserQuestion` is one) fits the loop's genuinely closed prompts — run-mode selection at `I0`, conflict resolution at `I5`, retraction triage at `I6`, deferral, the exit-gate confirmation — while **frontier questions stay markdown**, because their space is unknown and no widget fits. Never bend a prompt to fit a tool by inventing options, never mark an option as recommended, and when nothing suitable exists just ask in plain text: the loop's semantics do not depend on any widget. See the pattern's Host Interactive Tools section for the full judgment.

   **Drive the graph through the engine, never by reasoning about it in prose** — `.specify/scripts/python/interview-utils.py` owns frontier computation, ordering, cycle rejection, descendant walks, and retraction propagation (see the pattern's Engine section for the full contract and the strict division of labour):

   ```bash
   E=.specify/scripts/python/interview-utils.py; L=<resolved ledger>
   python3 $E init  --ledger $L --target <target> --mode special|informal --branch <name> ...
   python3 $E add   --ledger $L --id D4 --question "…" --depends-on D3    # I1: declare edges
   python3 $E frontier --ledger $L --json                                 # I2: this round's questions
   python3 $E conflicts --ledger $L --with "<candidate answer>"           # I5: before overwriting
   python3 $E answer --ledger $L D4 --decision "…" --span "## Section"    # I5: settle + record span
   python3 $E retract --ledger $L D3                                      # I6: dry-run blast radius
   python3 $E retract --ledger $L D3 --decision "…" --apply               # I6: re-open descendants
   python3 $E status --ledger $L --json                                   # exit gate readiness
   ```

   A non-zero exit is a **verdict** (`4` = cycle, or answering a decision whose premise is unsettled): report it, never work around it. Three pattern obligations are easy to skip:
   - **I1** — declare every decision's `--depends-on` as you add it, and ask in the engine's `order` (deep premises first); a widely-depended-on premise settled late turns one retraction into a session of rework.
   - **I3** — dispatch a subagent for any environment fact a question needs, do not block the round on it, and never ask the user for it.
   - **I5** — every settled answer records its `--span` before the round closes, and an answer that contradicts a settled decision is **surfaced, not overwritten**.

   The modes differ only in what `I5`'s write-through does, and in what `I6` has to repair:

   **Special Interview — edit in place, then feed back:**
   - Apply the round's answers to the **one** target, overwrite-style, only as far as the answers license.
   - **Echo the change back** — the edited sections or their diff — so the user sees their decisions as recorded text and can correct a misread before the next round.
   - Keep the tree bounded to that target: answers implying changes elsewhere are recorded as out-of-scope items, not acted on.
   - On retraction, roll back the invalidated spans **within that target** and re-echo, so the file never carries text derived from a retracted premise.

   **Informal Interview — consolidate and organize:**
   - **Reconcile the round against itself first** (a later answer may qualify an earlier one), then write the reconciled result.
   - **Organize as you write**: group answers by area, and split or add artifacts as the space's shape emerges — this is expected here, not scope creep.
   - Report which areas grew, so the user can see the map forming rather than only the answers.
   - On retraction, spans may sit in **several** artifacts and an invalidated grouping may have to be re-organized — report which areas the retraction touched, not only which decisions it reopened.

8. **Exit gate**: when the mode's convergence criterion is met, present the consolidated understanding (decisions, what each changed, what was deferred) and ask for confirmation. On confirmation, hand off to the next command per the handoff guidance at the end of this document. If the user reopens a branch, it re-enters the tree and the loop continues — an interview is done when the *user* says the result is stable, not when the agent runs out of questions.

## Report

- Run mode, and the target artifact and ledger paths
- Rounds run; questions asked / answered / deferred
- Branches settled vs. deferred (⏭ with reasons)
- Retractions (↩︎): what changed, which descendants were invalidated and re-asked, which were kept and why
- Conflicts surfaced and how the user resolved each
- Sections of the target artifact touched
- Facts resolved by probe rather than by asking (evidence that the fact/decision split held)
- Any mode switch, with the round it happened and the user request that authorized it
- Suggested next command

## Behavior Rules

- **Never fabricate an answer.** An unasked branch stays open in the ledger. This is the one unrecoverable failure of the mode.
- **Never ask for a discoverable fact.** Look it up or probe for it.
- **Never proceed on silence** and never self-certify completion — the exit gate is the user's confirmation.
- **Retraction is always available — say so.** Tell the user up front that any earlier answer can be revised by its ID, and that whatever depended on it will be re-asked. Never treat a change of mind as an interruption.
- **A retraction propagates; it is never a local edit.** Walk the recorded `dependsOn` edges, classify every descendant (still valid / needs confirmation / invalidated), roll back the invalidated spans, and re-open those decisions. Leaving a descendant derived from a retracted premise is the failure this machinery exists to prevent.
- **Surface conflicts; never resolve them silently.** When an answer contradicts a settled decision, name both and let the user choose which gives way.
- **Every question carries its own context, in a blockquote.** What that context must contain is owned by the comprehension discipline pointed to in the Glossary section above; this command adds only the rendering requirement — a markdown quote block.
- **No jargon, no unexplained abbreviations.** Governed by the comprehension discipline pointed to in the Glossary section above, which owns the permitted-jargon whitelist, the forbidden-jargon blacklist, and the in-place annotation rule; the conditions are not restated here.
- **One decision per question.** A question containing "and" usually holds two; split them and let the dependency edges order them.
- **No option menus, no recommended answers.** The answer space belongs to the user — that is the difference between this and `/speckit.clarify`. Offering choices anchors them to the closest one; recommending an answer records the agent's opinion under their name. Examples are allowed only when the user asks, as explicitly non-exhaustive illustrations.
- **Use a host tool only where it presents the prompt better; otherwise use markdown.** A choice widget (e.g. `AskUserQuestion`) fits closed prompts — run-mode selection, conflict resolution, retraction triage, deferral, the exit gate — where the option set is the true, complete space. Frontier questions stay markdown: no widget fits an unknown space, and inventing options to use one is the anchoring failure with extra steps. Fall back to plain text whenever nothing suitable exists; never skip a question over it.
- **Ask "what", not "whether".** "What should happen when a message fails?" opens the space; "Should we retry three times?" collapses it into ratifying a proposal.
- **Ask the whole frontier, in both modes.** Compute the frontier and put all of it in one message. Drip-feeding one question at a time wastes the user's rounds; asking a question whose prerequisite is still open forces a guess.
- **Write through every round, before the next one opens.** Special edits the target and echoes the change; Informal consolidates and organizes. Deferring a write to "later" in either mode breaks resumability and lets the artifact drift from the conversation.
- **Special stays on its one target.** If answers imply changes elsewhere, record the implication as out-of-scope and surface it at the exit gate; do not silently edit other artifacts.
- **Informal must not silently deep-dive.** When a round exposes a concrete target worth pinning down properly, say so and offer a Special interview on it (now or as a follow-up) instead of quietly turning the survey into a definition pass.
- **Stop only at round boundaries** — after the round's write-through is complete. Leave the ledger complete and report where to resume.
- **No live user** (fire-and-forget subagent invocation): process only the batch already answered in the ledger and return. Never advance the frontier without answers.
- **Respect termination signals** ("stop", "done", "enough"): close the current round, write through, record the remaining frontier as deferred, and report — a stopped interview must still leave a usable artifact.

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.interview" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Handoffs

**Before**: none — an interview may run at any time, on any artifact. In a feature context it is most useful when `/speckit.clarify` hits its question cap with the decision space still branching.

**After**: determined by what converged — a converged `requirements.md` → `/speckit.plan`; a converged `plan.md` → `/speckit.tasks`; a converged `tasks.md` → `/speckit.implement`; a converged goal → `/speckit.goal` or `/speckit.team`; anything else → the command that owns the target artifact. An Informal interview that surfaced a target worth pinning down hands off to a **Special** interview on it.