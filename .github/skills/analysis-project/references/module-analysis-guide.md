# Module Analysis Guide

## Core Method

Divide modules by **business function and responsibility boundary**, not by folder names alone. A logical module may span multiple files, and a single file may contribute to more than one logical module.

Analysis depth standard: **another AI should be able to reconstruct the module's design from the report alone**. That means the report must explain not only what the module does, but why it exists, how it collaborates, and what trade-offs shaped it.

## Module Analysis Starts After Macro Framing

Module analysis is downstream of macro analysis, not a substitute for it.

Before going deep into a module, first establish:
- the overall business problem
- the project's macro architecture and major subsystems
- the relevant tech stack constraints

Use [architect-analysis-guide.md](architect-analysis-guide.md) for macro framing and [tech-stack-analysis-guide.md](tech-stack-analysis-guide.md) for implementation-context framing.

## Global Perspective Requirement

**Every module analysis must answer two global questions:**

1. **Role in the overall project**: why does this module exist, and what breaks or becomes awkward without it?
2. **Design collaboration with other modules**: what contract does it maintain with adjacent modules, and does that collaboration reinforce the project's broader design philosophy?

The most common mistake is isolated analysis. Module design is often a response to constraints created elsewhere in the system.

## Five Completeness Elements for Module Analysis

Every core module analysis must cover the following elements. Missing any one means the picture is incomplete.

1. **Business responsibility** — what sub-problem the module solves
2. **Core data structures or abstractions** — only the interfaces and types necessary to understand the design
3. **Execution flow** — call chain or data path, ideally with a Mermaid sequence or flow diagram and source file paths/line numbers
4. **Design decisions and trade-offs** — why this approach, what alternatives were not chosen, and what costs were accepted
5. **Inter-module collaboration** — who depends on it, what inputs/outputs or state cross the boundary, and whether the boundary is clean

Verification standard: if another AI reads only your analysis, can it draw the module's boundary, explain the main flow, and describe why the module was designed this way? If not, the analysis is still shallow.

Must include: business context, architecture patterns, core flow, collaboration relationships, design trade-offs.

Should NOT include: complete type dumps, every function signature, exhaustive parameter lists, or raw code unless the implementation itself is the design insight.

## Module Identification Methods

Use multiple perspectives together:

1. **Business capability perspective** — what end-user or platform capability does this code enable?
2. **Data flow perspective** — where does data enter, transform, branch, and leave?
3. **Change coupling perspective** — when a requirement changes, which files tend to change together?
4. **Boundary perspective** — where are the stable contracts and unstable implementation details?

## Depth Expectations

- **Core modules**: architecture-critical, innovative, or complexity-bearing components. These require explicit trade-off analysis, collaboration mapping, and diagrams.
- **Secondary modules**: utilities, wrappers, or straightforward adapters. One paragraph may be enough unless they hide an unusually important design choice.

## Good Module Narrative

Module chapters should form a logical chain, not a collection of isolated notes.

Recommended narrative threads:
- **Data flow driven**: follow a request, event, or document through the system
- **Layer driven**: from foundation to orchestration to interface
- **Problem decomposition driven**: start from the core problem and explain how each module removes one constraint

Avoid filesystem order and alphabetical order unless they coincide with the real architecture.

## Subagent Parallel Analysis

Phase 6 should launch subagents in parallel:
- each core module gets an independent subagent
- all secondary modules can be grouped into one batch subagent
- all subagents should be launched in the same message when possible

### Core Module Subagent Prompt Template

```
You are a senior architect conducting a deep analysis of the "{module name}" module in {project name}.

## Background
- Project positioning: {one-line description}
- Overall architecture: {brief architecture style and core design}
- Project design philosophy: {core design philosophy across the project}
- Relevant tech stack constraints: {language/framework/build/runtime constraints relevant to this module}
- This module's position in the system: {relationship with other modules}
- Narrative context: {what the previous section established, what question this module answers, what it should set up for the next section}

## Files to Analyze
{list of file paths}

## Analysis Structure
Describe design intent in natural language. Expose concrete symbols only when necessary to explain the design.

1. Role in the project
2. Business sub-problem this module solves
3. Design approach and rationale
4. Core abstractions and data structures
5. Core flow — Mermaid diagram + interpretation, with source file paths and line numbers
6. Collaboration with other modules — dependencies, shared state, contracts, and [pending main agent verification] for cross-module inferences
7. Key decisions and trade-offs
8. Industry comparison or redesign considerations
9. Extension points (if applicable)
10. Highlights and issues — involved file list

## Global Perspective Requirement
Show how this module's boundaries and trade-offs serve the overall architecture rather than treating it as an isolated island.

## Related Exploration Questions
{list of questions}
Integrate answers into the relevant sections.

## Write Strategy
For large modules (total file lines > 5000), write incrementally:
- after each subsystem analysis, write immediately
- use Write first, then Edit to append
- do not wait until all files are read before drafting
- append the coverage table at the end

## Output
Write to {work_dir}/drafts/06-module-{module name}.md, max 300 lines per write.

## Coverage Requirement
Current analysis mode: {mode}, core module minimum coverage: {min coverage}%.
The draft must end with a coverage details table (filename | total lines | lines read | coverage% | reason for unread), with a total line marked ✅ compliant / ❌ non-compliant.
"Lines read" means lines actually requested via the Read tool. Continue reading until the coverage target is met.
```

### Secondary Module Batch Prompt Template

```
You are a senior architect conducting batch analysis of secondary modules in {project name}.

## Background
- Project positioning: {one-line description}
- Overall architecture: {brief summary}
- Project design philosophy: {core design philosophy across the project}

## Secondary Modules to Analyze
{list: name, assumed responsibility, file scope}

## Output Per Module
1. Responsibility
2. Role in the overall project
3. Implementation approach
4. Anything special worth calling out
5. Involved file list

Write to {work_dir}/drafts/06-module-secondary.md

## Coverage Requirement
Current analysis mode: {mode}, secondary module minimum coverage: {min coverage}%.
The draft must end with a coverage details table (filename | total lines | lines read | coverage% | reason for unread), with a total line marked ✅ compliant / ❌ non-compliant.
"Lines read" means lines actually requested via the Read tool. Continue reading until the coverage target is met.
```

### Subagent Collaboration Norms

- **Only analyze assigned files**
- **Mark cross-module inferences with [pending main agent verification]**
- **Depth over breadth**: fully explain one real core flow rather than skimming five
- **Maintain global perspective**: always connect local design back to system goals
- **Maintain narrative continuity**: opening relates to the previous section, ending sets up the next one

## Quality Checklist

- [ ] Modules are divided by business function, not only by folder structure
- [ ] Each module explains role, business responsibility, and design rationale
- [ ] Core elements are complete: responsibility, abstractions, execution flow, decisions, inter-module collaboration
- [ ] Core flows include Mermaid diagrams and code-backed evidence
- [ ] Essential interfaces/types are included, but only those necessary for understanding
- [ ] Unnecessary symbol dumps are avoided
- [ ] Collaboration relationships and shared state are clear
- [ ] Each module connects back to the overall architecture
- [ ] Another AI could reconstruct the module design from the report alone
