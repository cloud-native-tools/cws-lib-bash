# Architecture Analysis Guide

## Mission

Architecture analysis answers one question: **why does this project need this overall structure to solve its target problem?**

The output is not a directory tour. It is a macro explanation of:
- what business problem the project exists to solve
- what system boundary it draws
- what major subsystems it introduces
- how those subsystems collaborate under real constraints
- what trade-offs define the architecture

If readers finish this section and still cannot explain the project's overall shape on a whiteboard, the analysis is not complete.

## Start From the Problem, Not the Folders

Before reading implementation details, answer four questions:
1. **Who has this problem?** Target users, operators, developers, or platform teams
2. **What situation creates the pain point?** Cost, latency, complexity, risk, team workflow, scale
3. **Why do existing solutions fall short?** Missing capability, bad trade-off, poor ergonomics, cost mismatch
4. **Why does this project need to exist independently?** Unique positioning, opinionated workflow, narrower focus, stronger extensibility

Architecture analysis is invalid if it can be copied to another project by changing a few names.

## Core Macro Questions

Every architecture section should answer these questions explicitly:

### 1. System Boundary
- What is inside the system and what is delegated outside?
- What assumptions does the project make about external systems?
- Which boundaries are hard, and which are intentionally extensible?

### 2. Architectural Style
- Layered, plugin-oriented, event-driven, pipeline-based, hexagonal, monolithic modularization, etc.
- Why does this style fit the problem better than common alternatives?
- Is the chosen style applied consistently across the project?

### 3. Core Runtime Path
- What is the hottest or most business-critical path?
- Which components participate in this path?
- Where are the key control points: validation, routing, orchestration, persistence, isolation, caching, retries?

### 4. Dependency Direction
- Which modules are allowed to depend on which others?
- Where does policy live, and where does mechanism live?
- Does the dependency graph reinforce or undermine the intended architecture?

### 5. Evolution Strategy
- Which parts are stable foundations, and which are meant to change frequently?
- Where has the project invested in extension points?
- Which boundaries will become bottlenecks as scale or scope grows?

## Recommended Analysis Structure

### Business Context and Positioning
Explain the problem scenario first. Use docs, website, README, and code evidence to validate the framing.

### System Context
Describe the project's place in a larger ecosystem:
- upstream and downstream systems
- users and operators
- external services, storage, networks, or developer tooling

### High-Level Component Map
Group the project into major subsystems by responsibility, not directory names. Examples:
- user-facing entry layer
- orchestration and policy layer
- domain engine or workflow core
- infrastructure adapters
- persistence and observability support

Use Mermaid diagrams heavily. Prefer one macro component diagram plus one critical-path diagram.

### Architecture Narrative
Walk through the primary path in business order, not in filesystem order. Good narrative patterns:
- request/data flow driven
- layered capability driven
- problem decomposition driven

### Trade-Off Analysis
For each major architectural choice, explain:
- why this design exists
- what common alternative was not chosen
- what the chosen design gains
- what it costs in complexity, performance, coupling, or learning curve

### Strengths and Risks
Only call out architecture-level highlights and issues:
- modular boundaries
- extension model
- dependency direction
- scalability constraints
- operational failure handling

Avoid code-style or naming-level commentary.

## How to Find Architecture Highlights

### Compare Against the Obvious Alternative
Ask: if you designed this quickly, what would you have done first? If the project chose a different path, the reason is often the architectural insight.

### Look for Tension Points
Good architecture is a response to tension:
- flexibility vs simplicity
- runtime safety vs developer speed
- consistency vs autonomy
- portability vs deep platform integration

The most valuable analysis often lives at these tension points.

### Focus on Boundaries
Module internals can be rewritten. Boundaries are expensive to change. Boundary design reveals architecture maturity better than any internal helper function.

## Writing Standard

### Good
> The project keeps policy decisions in the orchestration layer and pushes protocol-specific details to adapters. This keeps the domain workflow stable even as integrations evolve, but it also means adapter capabilities can leak upward when an external system exposes features the core model does not represent cleanly.

### Bad
> The project has a clear layered architecture and good modular design.

The good version includes mechanism, reason, benefit, and cost. The bad version is generic praise.

## Minimum Deliverables

An architecture analysis should usually contain:
- business framing
- one macro architecture diagram
- one critical-path diagram
- major subsystems and responsibilities
- 3-5 key architectural decisions with trade-offs
- architecture-level strengths and risks

## Connection With Other Guides

- Use [tech-stack-analysis-guide.md](tech-stack-analysis-guide.md) to explain why the chosen languages, frameworks, and build stack support the architecture.
- Use [module-analysis-guide.md](module-analysis-guide.md) when drilling from subsystem view into module-level design.
- Use [git-analysis-guide.md](git-analysis-guide.md) to validate how the architecture evolved over time.
- Use [deployment-analysis-guide.md](deployment-analysis-guide.md) to explain how runtime topology reflects architectural choices.