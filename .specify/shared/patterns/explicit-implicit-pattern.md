# Explicit–Implicit Rule Pattern (显隐规则模式) — A Design Pattern for Routing & Rule Systems

A reusable design pattern for any unit that must **resolve an ambiguous-at-authoring-time mapping at run time** — which project/target an instruction belongs to, which behavior a rule triggers, which handler an intent routes to — under one structural law: **explicit rules are primary and hard; implicit rules are auxiliary and soft; and every successful implicit resolution gets a chance to become explicit** (`shared/patterns/explicit-implicit-pattern.md`).

## When to Apply (适用判据)

Apply this pattern when **all** of these hold:

1. The unit **resolves input to a target or behavior** (routing, dispatch, rule selection) and the invocation repeats across sessions.
2. The full mapping **cannot be enumerated up front** — the long tail of user vocabulary, aliases, and context is open-ended.
3. Deterministic matching alone **cannot cover the space**: some inputs need semantic judgment (an LLM or heuristic) to resolve.
4. Wrong resolutions are **costly or silent-dangerous** — acting on the wrong target is worse than asking.

Do **not** apply to: a fully enumerable rule space (just write the explicit table, no pattern needed); one-shot resolution with no reuse (nothing to converge); pure defaults/config (no user input to resolve — defaults apply when there is *no* signal, this pattern applies when there *is* one).

## Core Model (核心模型)

- **Explicit rule (显式规则)** — a rule **recorded in a durable artifact** (a route table such as `ROUTE.md`, a config file, or program code) and applied **mechanically**. It is a **hard rule**: never overridden by inference at run time; changed only through an edit to the artifact, never silently.
- **Implicit rule (隐式规则)** — a rule **inferred at run time** (semantic judgment, association, heuristics), typically expressed as **text** the LLM consumes. It is a **soft rule**: may be wrong, exceptions are permitted, and it always yields to any matching explicit rule.
- **Route artifact (路由事实源)** — the single durable home of explicit rules (`ROUTE.md`, a code table, a registry). One owner, one format, machine-checkable.
- **Precedence stack (优先级栈)** — explicit beats implicit; implicit only fills gaps the explicit base leaves open. Resolution never consults inference while an explicit rule matches.
- **Explicitness ratio E (显式化率)** — the single variable characterizing a system's rule structure: **E = explicit rules ÷ (explicit + implicit rules), expressed as a percentage**. The higher E, the stricter and more deterministic the system; **E = 100% means the system contains no implicit rule at all** — every decision is recorded and mechanically applied — while a low E means most behavior is inferred at run time. E is a **structural** measure (what is recorded); it is distinct from, and leads, the runtime **explicit hit rate** (how often invocations actually resolve without inference). Choose E deliberately per surface — mission-critical routing aims high; open-ended creative assistance tolerates a lower E — and a system's target E is itself an explicit decision, not an accident of accumulation.

### Explicit signal classes (显式信号三态)

Explicitness is about **where the rule is recorded and how it applies**, not about string strictness. Three classes, in typical resolution order:

| Class | Signal | Example |
|-------|--------|---------|
| **Contextual (上下文显式)** | The environment itself identifies the target | The current workdir *is* a target's own directory — no words needed |
| **Declarative (声明显式)** | The user names the target in the prompt | The instruction contains a target's canonical name verbatim, with an action attached |
| **Associative (关联显式)** | The user's words do not strictly match a target name but associate strongly with exactly one target | A domain concept or nickname whose meaning belongs to exactly one target's scope (e.g. a practice term → the target owning that practice) — intent is explicit, resolution is semantic until the association is recorded |

Associative signals are the **boundary tier**: they resolve semantically today precisely so they can be promoted into recorded (contextual-grade) rules tomorrow.

## The Six Principles (六条原则)

1. **Implicit never replaces explicit (隐不替显)** — when an explicit rule matches, inference is not consulted; an implicit resolution must never "correct" or bypass a recorded rule. To change a recorded rule, edit the artifact — never deviate at run time.
2. **Explicit primary, implicit auxiliary (显式为主、隐式为辅)** — the explicit base is designed to carry the traffic; implicit inference is the fallback for the uncovered tail, not a parallel system.
3. **Convergence (隐式向显式收敛)** — every successful implicit resolution prompts a promotion into the route artifact. Over time the implicit share shrinks monotonically; a rule base that stops growing means the promotion loop is broken.
4. **Hard vs soft (显硬隐软)** — explicit rules are hard: violations are defects. Implicit rules are soft: exceptions are legitimate, and on any conflict the implicit side yields.
5. **Determinism ratio (确定性比例)** — the stricter and more deterministic a system must be, the larger the share of decisions its explicit base must carry — quantified by the **Explicitness ratio E** (显式化率): E = 100% is a fully hard-rule system with no implicit behavior. The runtime **explicit hit rate** (fraction of invocations resolved without inference) is the observable proxy, and both should trend upward toward the system's declared target E.
6. **Medium split (载体分工)** — explicit rules live in **program code** (deterministic matchers: exact match, registered alias, path/context checks) so they cost zero LLM judgment; implicit rules live in **text** (prompt descriptions, association hints) because only an LLM can apply them. This is the same split as the Program-First discipline in `.specify/shared/guidelines/token-efficiency.md`: fixed-rule judgments go to programs, the LLM receives only what programs cannot decide.

## The Resolution Loop (解析环 X0–X4)

```
- [ ] X0 Load the explicit rule base (route artifact + code matchers)
- [ ] X1 Explicit resolution: contextual → declarative → registered aliases
        └─ hit → apply; record the hit for the explicit-hit-rate metric; done
- [ ] X2 Implicit resolution: semantic inference ranks candidates
- [ ] X3 Gate: single high-confidence candidate → apply, annotate "resolved implicitly"
        └─ ambiguous / low confidence → ASK (minimum necessary question), never guess silently
- [ ] X4 Promotion: after an implicit success, offer to record the mapping
        └─ user confirms → write-back to the route artifact; next time X1 resolves it
```

- **X0 — load**: read the route artifact and compiled matchers before any judgment. A resolver that infers without first checking the explicit base violates Principle 1.
- **X1 — explicit first**: run the deterministic matchers in order (contextual, declarative, registered aliases). A hit ends resolution immediately — no second-guessing by inference, even if inference "would have chosen differently".
- **X2 — implicit fallback**: only reached on an explicit miss. Semantic inference produces ranked candidates with reasons — never a bare answer.
- **X3 — confidence gate**: one strong candidate → proceed but **annotate** that the resolution was implicit (the annotation is what makes the run auditable and promotable). Multiple plausible candidates → ask; silently picking is the pattern's cardinal sin.
- **X4 — promotion prompt**: ask the user whether to record the confirmed mapping (e.g. append a `ROUTE.md` row: signal → target → confirmed date). **Offer, never force** — and record a declined promotion so the same offer is not repeated every run (nagging is its own anti-pattern). On confirmation, the mapping moves from text-described inference to code-matchable rule.

## Boundary: What This Is Not (概念消歧)

- **vs defaults/config**: defaults decide when there is *no* user signal; this pattern decides when there *is* one. They compose — explicit rule > implicit inference > default.
- **vs vocabulary validation (词汇表校验, reconcile-pattern optional component)**: vocabulary validation corrects *words* (homophones, typos) before meaning is interpreted; this pattern routes *interpreted intent* to a target. They compose in that order: validate vocabulary, then resolve routing.
- **vs semantic routing (语义路由, reconcile-pattern optional component)**: semantic routing is a static intent→target table; this pattern generalizes it with precedence, a confidence gate, and the promotion loop. A reconcile skill's semantic-routing table is a natural *route artifact* for this pattern.
- **vs the glossary (`.specify/memory/glossary.md`)**: the glossary pins *term spellings/meanings*; a route artifact pins *signal → target mappings*. An association confirmed at X4 may also deserve a glossary entry if it names a concept, not just routes one.

**判定口诀 (rule of thumb)**: 输入要落到唯一目标、匹配表写不全、还得靠语义猜 → 显隐规则模式；猜完了要记得问一句"要不要写进路由表" → 收敛闭环成立。

**Nesting**: this pattern typically runs **inside** another engine's dispatch layer — a reconcile R2 (compute desired state), an interview I0 (resolve target), or a command's scope resolution. It decides *where*; the enclosing engine decides *what to do there*.

## Applying the Pattern (设计与改造清单)

Designing a new resolver, or retrofitting an existing ad-hoc dispatcher:

1. **Name the resolution space** (what resolves to what) and create the **route artifact** with a fixed row format (`signal → target → source → confirmed date`); give it exactly one owner.
2. **Enumerate explicit signal classes** (contextual / declarative / registered aliases) and write a **deterministic matcher per class in code** — Principle 6: what a program can match must not cost an LLM call.
3. **Write the implicit fallback as text** (association hints, domain descriptions), and define the **confidence gate**: what counts as a single strong candidate, and the exact question asked when ambiguous.
4. **Install the promotion loop**: after every implicit success, offer write-back; record declined offers; verify the route artifact is the *only* place a confirmed mapping may live.
5. **Add the health metrics**: the structural **Explicitness ratio E** (declared target per surface, recomputed when the rule base changes) and the runtime **explicit hit rate**. Expect both to rise; a flat line means the promotion loop is dead (offers skipped, nagging-suppressed, or write-backs not applied).
6. **Add conflict handling**: two explicit rules matching the same input is a defect — detect at write-back time (deterministic check), never resolve by inference at run time.

## Anti-patterns (反模式)

- **Implicit over explicit (隐式越权)**: inference "corrects" a recorded rule because the model thinks it knows better. Recorded rules change only by editing the artifact.
- **Silent implicit resolution (静默兜底)**: resolving by inference without annotating it and without the X4 promotion offer — the same guess is paid for on every run forever, and the rule base never converges.
- **Promoting a guess (把猜测固化为硬规则)**: recording a mapping at X4 *without* user confirmation — a soft inference becomes a hard rule nobody endorsed.
- **Promotion nagging (收敛骚扰)**: re-offering a mapping the user already declined; a declined offer is itself a recorded fact.
- **Implicit baked into code (隐式规则暗码化)**: hard-coding heuristic behavior instead of recording it as an inspectable rule — the rule becomes invisible, un-auditable, and un-editable.
- **Parallel rule bases (双轨制)**: maintaining an implicit system alongside the explicit one "for flexibility" — this violates Principles 1–2 directly; there is one stack, explicit on top.
- **Unbounded rule base (路由表失控)**: a route artifact with no conflict detection, no format check, or multiple writers — it decays into just another implicit system.
