---
name: analysis-project
description: Deep analysis of current project with professional architecture reports. Use when the user mentions "分析项目", "分析仓库", "源码分析", "架构分析", "代码分析", "学习这个项目", "研究这个框架"
---

# Project Deep Analysis Skill

Deep analysis of current project to produce professional architecture reports. Reports are technical research with deep insights — after reading, the audience understands business problems, masters architecture design, and forms their own thinking.

## Core Principles

### First Principle: Business Problem Before Code

**Every analysis must start from the business problem the project solves, never from what functions or classes exist in the codebase.** This is the single most important rule that separates an architecture analysis from a code walkthrough.

**The mindset shift**: Before reading any line of code, you must be able to answer:
- Who has this problem? (the target audience, their role, context)
- What situation creates this pain point? (workflow breakdown, bottleneck, cost)
- Why do existing solutions fail? (gap analysis, trade-offs that don't fit)
- Why does this project need to exist as a standalone solution? (unique positioning)

Only after these questions are answered should you look at the code — and even then, read code to understand *how* the business problem is solved, not *what* the code does.

**Concrete comparison**:

| Code Walkthrough (DON'T) | Business-Driven Analysis (DO) |
|------|-----|
| `handleRequest(ctx)` receives a Context parameter and calls `authMiddleware.Check()` before routing | The system treats every incoming request as untrusted by default, enforcing a "deny unless explicitly allowed" policy. Authentication is the first gate in a three-layer defense (auth, rate-limit, routing) — this ordering prevents wasted compute on unauthorized requests |
| `interface MessageQueue { push(); pop() }` defines Producer/Consumer pattern | Modules communicate through an asynchronous message bus. Producers don't know who consumes their messages, and consumers don't know who produced them. This decoupling allows independent scaling and failure isolation — if the consumer is down, messages queue up rather than errors propagating back to the producer |
| The `Router` class has a `RadixTree` field | The routing layer chose a radix tree over a hash table because parameter routes (`/users/:id`) and wildcard matching (`/static/*`) require prefix-based lookups, which hash tables cannot support natively. This is a deliberate performance investment for an API gateway's hottest path |

**Red flag during analysis**: If any section of your report reads like it could apply to a different project by simply changing names and function references, it lacks business grounding. Every module's description should be unmistakably about *this* project solving *this* problem — no other project has the same combination of problem, constraints, and design choices.

### Abstraction Level: Explain Design, Not Code

Describe at the design pattern and architecture level by default. **Do not paste raw code unless necessary**. Only show code when the design is particularly elegant, the project introduces unique concepts, or implementation is its core selling point — and always explain in natural language first.

### Deep Insight: Why > What (Mandatory)

Every design decision must explain motivation, trade-offs, and alternative costs:
- **Why this design?** Not just "what pattern was used", but "why it fits this scenario"
- **What if not?** The cost of alternatives
- **How does it compare to industry best practices?** Where it leads and where it lags
- **If you were to redesign it?** Demonstrates deeper understanding

See [architect-analysis-guide.md](references/architect-analysis-guide.md), [tech-stack-analysis-guide.md](references/tech-stack-analysis-guide.md), and [git-analysis-guide.md](references/git-analysis-guide.md) for depth standards, technical interpretation, and evolution-based validation.

### Inspiring Writing

The goal is to help readers **learn something and think**, not to produce a code manual. Like a senior engineer explaining at a whiteboard — with opinions, reasoning, and comparisons. See [architect-analysis-guide.md](references/architect-analysis-guide.md).

### Global Connection

Every local analysis must connect to the project's overall design philosophy — this is what distinguishes a "code manual" from an "architecture analysis". Use [architect-analysis-guide.md](references/architect-analysis-guide.md) for macro narrative and [module-analysis-guide.md](references/module-analysis-guide.md) for module-level connection rules.

## Recommended Analysis Order

Use the following order unless the project characteristics strongly suggest otherwise:

1. **Architecture first** — establish business framing, system boundary, and subsystem map with [architect-analysis-guide.md](references/architect-analysis-guide.md)
2. **Tech stack second** — explain why the implementation stack fits the architecture with [tech-stack-analysis-guide.md](references/tech-stack-analysis-guide.md)
3. **Module deep dive third** — analyze core and secondary modules with [module-analysis-guide.md](references/module-analysis-guide.md)
4. **Git history fourth** — validate evolution, release rhythm, and architectural change signals with [git-analysis-guide.md](references/git-analysis-guide.md)
5. **Deployment last** — explain runtime topology and delivery model with [deployment-analysis-guide.md](references/deployment-analysis-guide.md)

This order keeps the report moving from macro intent, to implementation means, to internal structure, to historical evolution, and finally to operational reality.

## Analysis Workflow

> **Flexibility principle**: The phases below are advisory guidelines. The agent should dynamically decide based on project characteristics — skip or simplify any phase that has no meaning for the current project. Final report quality is the standard.

### Phase 1: Project Acquisition & Initialization

1. Parse user input (supports `owner/repo`, GitHub/GitLab/Gitee URL, local path)
2. Create workspace: `~/repo-analyses/${REPO_NAME}-{YYYYMMDD}` as `$WORK_DIR`
3. Clone with `git clone --depth=1` if remote; skip if local path provided
4. Gather basic metadata (Stars, Forks, contributors, code statistics)
5. **Business context discovery**: before diving into code, answer the four business questions from the First Principle (Who? What situation? Why existing solutions fail? Why standalone?). Write initial hypotheses to `drafts/01-business-context.md` — these will be validated and refined through subsequent phases.

1. **Count effective code lines** (exclude tests, build configs, auto-generated code, examples/docs)
2. **Validate business hypotheses from Phase 1**: does the code scale and organization match your initial business understanding? A project solving a complex distributed systems problem should have substantial architectural code, not just utility functions. If the ratio doesn't match expectations, investigate — either your business hypothesis was wrong, or the project's architecture is misaligned with its stated goals.
3. **Let user choose analysis mode** (via AskUserQuestion):

| Mode | Core Modules≥ | Secondary Modules≥ | Use Case |
|------|--------------|--------------------|----------|
| Quick | 30% | 10% | Quick overview |
| Standard (recommended) | 60% | 30% | Regular architecture analysis |
| Deep | 90% | 60% | Deep dive into every design decision |

3. Write stats and chosen mode to `drafts/03-plan.md`; subsequent phases follow this for depth control

### Phase 3: External Research + Project Documentation (Search First, Read Later)

1. WebSearch for project reviews, comparisons, architecture discussions (3-5 searches)
2. Crawl project website (homepage, Features, Use Cases, Comparison, etc.)
3. Read project documentation (architecture/, docs/, CONTRIBUTING.md, RFC/ADR, etc.)
4. Write research findings to `drafts/03-research.md`. **This is the most critical phase for answering "what problem does this project solve"** — external sources often state the problem more clearly than code does. Must include:
   - **Core problem** (who, what scenario, what pain point, why existing solutions fall short)
   - **Competitor comparison** (3-5 similar projects with positioning differences)
   - **Unique value proposition** (why this project needs to exist separately)
   - **Business validation**: cross-reference Phase 1 business hypotheses against external research — what was confirmed, what was wrong, what new dimension was discovered?
   - **Initial architecture and deployment clues**: use docs, repo structure, and packaging files to prepare for [architect-analysis-guide.md](references/architect-analysis-guide.md) and [deployment-analysis-guide.md](references/deployment-analysis-guide.md)
5. Write analysis plan to `drafts/03-plan.md`

### Phase 4: Project Feature Identification + Adaptive Questioning

From project features (entry files, directory structure, dependencies, docs), identify:
- Project type and positioning (library/framework/application/tool)
- Scale, maturity, design style signals, tech stack characteristics
- Delivery and runtime signals (CLI-only, package distribution, service deployment, containerization, CI/CD automation)
- **Extract questions from features**: each observation may suggest a question worth asking the user
  - Unusual tech stack combination → ask about motivation
  - Complex plugin system → ask about priorities
  - Simplicity vs flexibility → ask about trade-offs

Ask user questions (≤3 per round), one of which should confirm the **level of detail for the report introduction** (well-known projects may not need lengthy introductions). See questioning strategy in [module-analysis-guide.md](references/module-analysis-guide.md).

**Business-problem-driven questions**: at least one question should validate your evolving understanding of the problem. Examples: "This project seems to solve [X problem] for [Y audience] — is that the right framing?", "I noticed [design choice Z] — does this suggest the primary use case is [A] or [B]?", "The README mentions [claim], but the code seems optimized for [different concern] — which direction should I prioritize in the analysis?"

### Phase 5: Dynamic Report Structure Design

1. Synthesize Phase 3 research, Phase 4 features, and user responses
2. **Design chapter structure** (no fixed template), must satisfy:
   - Scenario-based problem introduction (material from Phase 3)
   - Competitive positioning (differences in design philosophy and tech approach)
   - Project overview, architecture chapter, tech stack chapter, module deep analysis, git evolution chapter, deployment chapter, evaluation & insights
   - Architecture visualization (Mermaid diagrams), code evidence
3. **Identify modules**: categorize core vs secondary by business function
4. **Design narrative line**: determine module presentation order and transition logic (data flow / layered / problem-driven)
5. Output report outline for user confirmation, then write to `drafts/05-modules-plan.md`

### Phase 6: Parallel Deep Analysis (Subagent Team)

Must use Agent tools to launch subagents in parallel:
- Each core module → one independent subagent
- All secondary modules → one combined subagent for batch processing
- All subagents launched in the same message

Each subagent prompt must include:
- Overall project design philosophy and global perspective
- Narrative context (previous module conclusion → this module's questions → next module setup)
- Coverage requirements and write strategy

Detailed prompt templates at [module-analysis-guide.md](references/module-analysis-guide.md).

**Main agent discipline**:
- After subagent launch, main agent must NOT read source files assigned to subagents
- **No early merging**: must wait for ALL subagents to complete before starting Phases 7-8
- While waiting, focus on: reading project docs, external research, designing report skeleton

### Phase 7: Cross-Validation + Quality Control (Main Agent)

1. **Coverage gating**: read coverage tables from draft tails; auto-supplement or report reasons for non-compliant modules
2. **Spot-check validation**: pick 2-3 key conclusions per core module, verify against source code
3. **Cross-validation**: verify cross-module conclusions and global connection
4. Write to `drafts/07-cross-validation.md`

### Phase 8: Multi-Source Fusion & Final Report (Main Agent)

1. Distill architecture insights and systematic design philosophy
2. Deepen competitor comparison (supplement search if Phase 3 was insufficient)
3. **Multi-source fusion**: use Phase 5 structure as skeleton, extract content from drafts
   - Take the most detailed version when a concept appears in multiple drafts
   - Eliminate "see draft X" navigation references
   - Narrative coherence: organize by narrative line, use natural transitions
   - Preserve the recommended chapter order: architecture → tech stack → modules → git evolution → deployment, unless the project clearly demands a different narrative
4. **Segmented writing**: final report typically exceeds 500 lines; Write first 2-3 chapters (200-300 lines), then Edit to append
5. Coverage summary to `drafts/08-coverage.md` (not included in final report)
6. Output single markdown file: `$WORK_DIR/ANALYSIS_REPORT.md`

### Intermediate File Manifest

| Phase | Files |
|-------|-------|
| 3 | `03-research.md`, `03-plan.md` |
| 5 | `05-modules-plan.md` |
| 6 | `06-module-{name}.md` (generated by subagent) |
| 7 | `07-cross-validation.md` |
| 8 | `08-insights.md`, `08-coverage.md` |

## Output Requirements

- Heavy use of **Mermaid diagrams** for architecture, flows, data flows
- Default output in **Chinese** (follow user's language if different)
- Critical thinking: compare with industry practice, point out real issues, don't dodge defects
- Code as evidence: all conclusions backed by code, cite `file path` or `file path:line range`

## Special Scenarios

- **Extra-large projects (>50k lines)**: prioritize core modules, use Agent parallelism
- **Comparison mode**: complete Phases 1-4 for both projects, design comparison-style report structure in Phase 5

## Reference Documents

| Document | Content |
|----------|---------|
| [architect-analysis-guide.md](references/architect-analysis-guide.md) | Macro architecture framing, business-first analysis, narrative standards |
| [tech-stack-analysis-guide.md](references/tech-stack-analysis-guide.md) | Language, framework, build, pattern, and ecosystem-fit analysis |
| [module-analysis-guide.md](references/module-analysis-guide.md) | Module analysis methods, completeness standard, subagent prompt templates |
| [git-analysis-guide.md](references/git-analysis-guide.md) | Commit/tag/branch history analysis and architectural evolution signals |
| [deployment-analysis-guide.md](references/deployment-analysis-guide.md) | Runtime topology, packaging, delivery pipeline, and operability analysis |

## Report Output Location

After completing all analysis phases, the final analysis report must be written to `analysis-project.md` in the workspace root. This is the deliverable file that users will consume.

```
$WORK_DIR/analysis-project.md
```
