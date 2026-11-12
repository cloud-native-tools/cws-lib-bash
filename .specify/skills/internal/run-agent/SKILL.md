---
name: run-agent
description: Dispatch an existing Agent Instance or Template as a live subagent execution — resolve the definition across the layers, present then dispatch, inject the fast-fail clause, and relay the result. Also owns the no-argument listing/suggestion behaviour for `/speckit.agents`, and the authoring baseline vocabulary (frontmatter fields, valid file locations, validation rules) that agent authoring references. Use this when the user mentions ["run agent", "dispatch agent", "运行代理", "执行代理", "列出代理", "list agents", "agent not found", "subagent dispatch", "调用 agent"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/run-agent/SKILL.md>"
---

# run-agent

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.


## Goal

Turn a defined agent into a **live execution** and keep the agent store's operational
surface honest: one `/speckit.agents` invocation either runs an agent, or — with no
arguments — tells the user what exists and what would be worth doing next. This skill also
owns the **authoring baseline** (the frontmatter vocabulary and validation rules) that the
`create-agent` / `improve-agent` authoring skills enforce.

Canonical extraction source: `.specify/templates/commands/agents.md` § Run Mode, § Default Behavior
(No Arguments), and the authoring-baseline block (Authoring Rules / Frontmatter Baseline /
Valid File Locations / Validation). Content moved here verbatim in substance; the command
template keeps entry + delegation only.

## Input Contract

- **Intent**: `run <agent-name> [task]`, or empty (no-argument listing behaviour).
- **Agent resolution**: by `name` from the request or conversation context. Load
  `.specify/agents/instances/<name>.agent.md`, falling back to
  `.specify/agents/templates/<name>.agent.md` (**instance wins on collision**); apply
  `.specify/agents/execution/configs/<name>.yaml` when present.
- **Layer explicitness**: every operation targets exactly one layer —
  `template` / `instance` / `execution` (taxonomy:
  `.specify/shared/definitions/agent-definitions.md`). If the layer is ambiguous, ask; never
  guess silently.

Agent not found → report **"agent not found"** and offer to `create` it. Do not improvise a
one-off prompt in its place.

## Workflow

### Run Mode (subagent dispatch)

Running turns a definition into a **new, independent Agent Execution**. Each invocation
spawns a fresh Execution — the same Instance can be run multiple times (sequentially or
concurrently), and each Execution is isolated from the definition and from every other
Execution.

**Execution Topology (拓扑声明输入)** — the dispatch is parameterized by an Execution
topology declaration per `.specify/shared/definitions/subagent-definitions.md` § Execution
Topology Declaration:

- **本地拓扑（local）**: `<project-dir>` + `<cli>` — the orchestrator drives the CLI directly
  with the local project as working directory.
- **远端拓扑（remote）**: `<alias>`（or host IP）+ `<run-user>`（uid≠0）+ `<project-dir>` + `<cli>`
  via `ssh` → `su` — long-running/parallel work that must outlive the session.
- **双形态等价（dual input forms）**: the declaration arrives as **内联参数（inline）** or an
  **执行配置文件（execution config）**; when BOTH are given and any element disagrees, the
  dispatch is **rejected at parse time with the conflicting fields listed**（拒收报错并列冲突字段）
  — never a silent pick. A missing/invalid referenced template is a **快速失败**（模板缺失即停）—
  no silent degradation to an inline substitute.
- **前置检查先于派发**: run the five-family preflight with its failure-handling chain from
  `references/dispatch-preflight.md` — this SKILL.md references that table and MUST NOT copy it.
- **拓扑配方引用**: concrete command shapes (breakpoint probe, stage prompt files, runner
  derivation, detached dispatch + polling, local variant) come from
  `.specify/shared/workflow/external-dispatch-recipes.md` — referenced, never copied here; a
  shape the recipes do not cover fails fast instead of being improvised.

**Configuration resolution (mandatory before dispatch)** — the deterministic engine
`.specify/scripts/python/execution-config.py` is the ONLY configuration resolver; this skill
MUST NOT merge or normalize configuration itself:

- **Resolve**: `python3 .specify/scripts/python/execution-config.py --action resolve --agent
  <slug> [inline overrides] --workspace-root <project-dir> --format json`. The inline
  argument names are exactly `--mode`, `--cli`, `--model`, `--reasoning-effort`,
  `--context-window`, `--extra-flags`, `--log-dir`, `--quantification-method`; pass the same
  values the dispatch will use, including the topology declaration inputs.
- **Disclose** (disclosure, not a blocking gate): `config_id`, `mode`, `cli`, the effective
  `model / reasoning_effort / context_window`, `source_chain`, `skipped_layers`,
  `quantification.{requested,resolved}`, and `requires_external`.
- **Stop on resolve failure**: a non-zero `resolve` exit stops the dispatch — report the
  engine's field/support-set message. A missing defaults layer points at `specify init`.
- Keep the returned `snapshot` path and `config_id` for the post-dispatch record.

1. **Resolve the target agent** — per the Input Contract above.
2. **Present & dispatch** — present the agent's `name`, `description`, and the task, then
   dispatch directly. The presentation is **disclosure, not a blocking gate**（用户可随时叫停）.
3. **Dispatch** — launch as a subagent with its configured `capability-tools`, `model-tier`,
   `run-turn-budget`, and system prompt. Choose the execution mode per
   `.specify/shared/definitions/subagent-definitions.md`: **native** when the runtime supports
   subagents, **virtual** in-session when it does not, **external** CLI process for
   long-running/parallel work or per-dispatch model overrides.
   ⚠️ External CLI dispatch MUST follow that document's **Visibility Contract** (stream-json +
   compact filter + `.live.log` / `.jsonl` / `.status` triplet) — never redirect print-mode
   output into a silent log. The Execution works autonomously within its defined scope.
   For an **external** dispatch, reuse `.specify/skills/internal/create-team/scripts/dispatch.sh`:
   `DISPATCH_CLI=<cli> DISPATCH_LOG_DIR=<absolute-log-dir> bash <dispatch.sh> <label>
   <workdir> <prompt-file> -- <cli_args...>`. Pass the engine's `cli_args` array verbatim
   after `--` — never reorder, re-quote, or filter them. `DISPATCH_LOG_DIR` MUST be absolute
   (resolve the snapshot's workspace-relative `log_dir` against the target project directory,
   or use `.specify/agents/execution/logs`); the dispatch label is used verbatim as `run_id`.
   For **remote** topology, run `resolve` (before) and `collect-dispatch` (after) on the
   **target project side** through the same `ssh` family, so the snapshot, logs, and store
   belong to the target project.
4. **Collect (external only)** — after `dispatch.sh` returns, invoke
   `python3 .specify/scripts/python/exec-quant.py --action collect-dispatch --unit-id
   agent:<slug> --run-id <label> --snapshot <snapshot> --config-id <config_id>
   --workspace-root <project-dir>`. A non-zero exit is reported with its reason and MUST NOT
   change the dispatch result, re-run the dispatch, or delete any artifact.
5. **Report** — relay the result back to the user. If the subagent fails or hits its turn
   limit, report the **partial result and the failure reason** — not a summary that hides it.

**Dispatch-time injection (mandatory)**: before dispatching, verify the outgoing prompt
carries the fast-fail injection clause — its owner literal lives in
`.specify/shared/guidelines/fast-fail.md` § 子代理派发注入 — and require an explicit anomaly
line in the returned message. A return without that line is **incomplete**, and its
conclusions MUST NOT be consumed. Found missing **before** dispatch → repair in passing and
disclose at wrap-up; found **after** dispatch → fast fail, because the agent already ran
ungoverned and editing the prompt cannot undo that.

- **`role-transition` pointer item（授职派发）**: when this dispatch grants dispatch duty
  (`dispatch_duty: granted`), the payload MUST carry the `role-transition` injection — the
  stable identifier plus the closed nine-item pointer list owned by
  `.specify/shared/definitions/superagent-definitions.md` § Role-Transition Injection. The
  items travel as pointers; no rule text is copied into the payload.
- **Self-check extension（逐项判定）**: the existing pre-dispatch self-check above is extended
  to require the `role-transition` identifier **and each of its nine item-id slugs** — the
  identifier alone is insufficient. A missing identifier or slug is a payload-construction
  defect and blocks the dispatch before it starts.

**Anti-nesting obligation (反嵌套，派发前拦截)**: the outgoing prompt MUST NOT reference any
driver/loop skill (e.g. `sdd-loop-driver`), MUST NOT instruct the subagent to load any skill,
and MUST NOT contain loop logic — the loader of a driver manual is the driver itself, and a
subagent that receives the manual becomes a second driver, so the hierarchy escapes.

**The narrowed hierarchy is depth 2, not an exemption**: 循环层级深度 2，其三个条件的完整谓词、
链上三个禁令、virtual 模态排除与「每成员一运行」的硬上限的唯一声明位点是
`.specify/shared/definitions/subagent-definitions.md` § Dispatch-Time Governance Obligation —
referenced here, never restated. A stage executor stays a leaf: a dispatch prompt handed to it
MUST NOT name a driver.

**Pre-dispatch probe (fail-closed)**: the probe resolves the two declared halves by calling the
engine, never by re-reading the definitions in prose:

```console
$ python3 .specify/scripts/python/sdd-route.py --action authorize \
    --agent <agent-definition> --team <team-slug> --seat <seat-slug> --format json
```

Run it from the target project root, so the roster resolves. Dispatch only when the record's
`effective` value is `allowed` **and** the duty's recorded routing decision is `sdd`; any other
value, an unreadable input (exit `2`), or a missing decision record blocks the dispatch. The
probe fails closed and a refusal is never dispatched: it MUST name the failed condition — the
failing half (`agent` / `seat` / `both`), the recipient's resolved values, the two source paths
and the seat slug — because a record saying only "not authorized" tells the reader nothing about
which declaration to fix. Rewording the prompt cannot repair a refusal: the verdict is resolved
from the declarations, not from the prompt's wording. Provenance: the sdd-loop-driver Driver
Topology defect fix (2026-10-16); obligation declared in
`.specify/shared/definitions/subagent-definitions.md` § Dispatch-Time Governance Obligation.

**Multi-unit duties route to a capable body (FR-024)**: a duty whose honest partition is `N >= 2` concurrent units MUST NOT be handed to a body that cannot dispatch. Before dispatch, judge the recipient's dispatch capability from its **existing** `capability-tools` frontmatter key (the `capability` action of `.specify/scripts/python/concurrency-check.py` reads the same list; no frontmatter key is introduced here). When the recipient is incapable, the framework MUST route the duty to a capable executor — the orchestrator/main agent itself, a capable sibling, or the driver — and **record the routing decision** (recipient, capability reading, routed-to, reason) in the run record. A coordinator whose own toolset lacks dispatch still emits its partition (each package naming its scope, inputs and output path) so the capable executor can run the packages without re-deriving them; a duty silently serialised inside an incapable body is a defect, not a degradation. The candidate carrier for any dispatched execution is one of the two legal process carriers named by `.specify/shared/definitions/subagent-definitions.md` § Three Execution Modes (fork for same-family agents, subprocess for heterogeneous agents); the host-internal in-process subagent path is not a concurrency carrier.

**Scope boundary**: Run mode executes a **single** agent on a **single** task. For
multi-agent orchestration (parallel dispatch, serial chains, iteration loops, long-running
loops), use `/speckit.team` — not this skill.

### Default Behavior (No Arguments)

When `/speckit.agents` receives empty arguments it MUST execute this sequence instead of
routing to a mode:

1. **List all existing agents** — scan `.specify/agents/{templates,instances}/*.agent.md` and
   present a summary table with each agent's **layer**, `name`, `description`, `tools`, and
   `model`. If no agents exist, state **"No agents found"** explicitly.
2. **Give contextual suggestions** — grounded in observable context (conversation history,
   repo state, agent definitions), **never fabricated**:
   - description matches the current task → suggest `run <name>`;
   - definition looks outdated or underperforming → suggest `refine <name>`;
   - none fit → suggest `create`, with a proposed role derived from context.
3. **Show capability summary** — briefly list the three modes (create / refine / run).

Informational and non-destructive: it MUST NOT create, refine, or run any agent without
explicit user instruction.

## Authoring Baseline

The vocabulary the authoring skills (`create-agent`, `improve-agent`) enforce. Field
semantics are owned by `.specify/shared/definitions/agent-definitions.md`; the reference
implementation is the shipped role set.

```yaml
---
name: "<required: unique identifier>"
description: "<required: trigger words + when to use>"
capability-tools: [Read, Grep, Glob]
model-tier: auto
run-turn-budget: 500
display-color: purple
---
```

Supported fields (neutral vocabulary — host renderers map them onto each tool's native keys
at init time): `name` (required), `description` (required), `capability-tools`,
`disallowed-tools`, `model-tier` (`auto` / `lite` / `efficient` / `performance` /
`ultimate`), `run-turn-budget`, `timeout-mins`, `skills`, `mcp-servers`, `permission-mode`,
`background`, `isolation`, `display-color`, plus the framework fields `user-invocable`,
`disable-model-invocation`, `supervisor`, `role-scope`, `project`, `sdd-invocation`.

**`sdd-invocation`** is the SDD invocation capability key: an authored instance declares it
to state whether its seat may start a nested SDD run, and its seat-side counterpart is the
`seats:` entry in `team.md`.
Three facts about it are **owned elsewhere and cited here, never restated**: the closed
value set, the absent-key default, and the framework-only (never rendered to a host tool)
status all live in the neutral key set `NEUTRAL_AGENT_METADATA_KEYS` /
`NEUTRAL_AGENT_FRAMEWORK_KEYS` in `src/specify_cli/__init__.py` — read that owner for the
values. `validate_agent_metadata` rejects a declaration whose value falls outside the
owner's closed set, and `parse_agent_frontmatter` accepts it only as a flat scalar (no list
or mapping form).

**承载责任（hosting responsibility）**：声明 `sdd-invocation: allowed` 的定义 MUST 在正文里同时写明
三件事 —— ① 承载驱动（`sdd-loop-driver`）本身；② 自身不执行任何阶段命令；③ 止于 review，并把
handoff 交回外层。声明与正文 MUST 一起被读取：只有声明而缺这三条陈述判不合规，只有这三条陈述而
没有声明同样判不合规 —— 承载能力不是一件可以默认成立的事。阶段执行者能力仍是叶子，MUST NOT 声明
`allowed`，该禁令对本仓出厂预置的阶段执行角色族（如 `agents/sdd-requirement-analyzer.agent.md`）直接断言，而不是对一条约定断言。
取值域、缺省与「不渲染到宿主工具」三项一律按路径读中立键集所有者
`src/specify_cli/__init__.py`（`NEUTRAL_AGENT_METADATA_KEYS` / `NEUTRAL_AGENT_FRAMEWORK_KEYS`），
本节不复述取值。

**Authoring rules**: focus on **what** the agent does and **when to call** it; concise,
explicit instructions over narrative; a single responsibility per agent; least-privilege
tool set; approved providers only — Claude Code, opencode, Qoder, Codex CLI, Hermes Agent,
GitHub Copilot — reject anything else.

**Valid file locations**:
- Canonical: `.specify/agents/templates/*.agent.md` + `.specify/agents/instances/*.agent.md`
  (single source of truth per layer; discovered by globbing these patterns and reading each
  file's frontmatter `name` / `description`).
- Execution artifacts: `.specify/agents/execution/{configs,scripts}/` tracked;
  `execution/logs/` gitignored, never committed.
- Rendered outputs (read-only, rebuilt from the neutral source): `.qoder/agents/`,
  `.claude/agents/`, `.github/agents/`, `.opencode/agents/`.

Agent definitions are **self-contained**: everything an agent needs lives in its own
`.agent.md` (no shared-assets directory under the agent stores).

**Validation**: YAML frontmatter must be valid; unsupported provider references are
rejected (provider whitelist); the tool list must match workflow needs; unresolved
contradictions block save.

## Boundaries

- **Authoring** (create / refine an agent definition) is not this skill — that is
  `create-agent` / `improve-agent`, reached through the command's intent routing.
- **Team operations** (organize or run several agents together) are not this skill and not
  this command — route to `/speckit.team`.
- **Lifecycle distinction**: *temporary* agents live only in conversation context and are
  never written to the agent directory; *persistent* agents are written under
  `.specify/agents/{templates,instances}/` and made available to all officially supported
  tools on initialization via per-tool rendering into real files (e.g.
  `.qoder/agents/<slug>.agent.md` in Qoder format; instance wins on filename collision).

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:run-agent" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:run-agent" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:run-agent" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
