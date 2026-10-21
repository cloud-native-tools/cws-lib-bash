# Tech Stack Analysis Guide

## Goal

Tech stack analysis explains **why this project chose this combination of implementation technologies** and what those choices imply for architecture, team productivity, portability, and long-term evolution.

This is not a dependency inventory. It is an interpretation layer between architecture and implementation.

## What to Analyze

### 1. Programming Languages
For each important language in the repository, explain:
- what role it plays
- why it is a good fit for that role
- what trade-offs it introduces
- whether the language mix increases or reduces system complexity

Questions to ask:
- Is the language choice driven by runtime performance, developer efficiency, ecosystem, or distribution constraints?
- Does the project use one language consistently, or split responsibilities across languages?
- If multiple languages exist, is the boundary between them clean?

### 2. Build, Packaging, and Toolchain
Analyze the project's engineering backbone:
- package manager and dependency model
- build system and artifact generation
- task runner, code generation, linting, formatting, testing
- release packaging and installation experience

Explain whether the toolchain supports the project's claimed positioning. A CLI, framework, SDK, and server platform have very different toolchain expectations.

### 3. Frameworks and Runtime Libraries
Identify major frameworks or foundational libraries and explain:
- what capability they provide
- why the project builds on them instead of implementing from scratch
- whether the project stays idiomatic to the framework or fights it
- where framework constraints shape architecture

### 4. Design Patterns and Engineering Conventions
Look for repeated implementation patterns such as:
- plugin registration
- dependency injection or inversion
- adapter/facade layers
- pipeline or middleware chains
- template-driven generation
- explicit configuration vs convention

The goal is to expose the project's engineering style, not just list named patterns.

### 5. Ecosystem Fit
Judge whether the chosen stack fits the target audience and deployment model:
- Is installation friction appropriate?
- Is the stack common in the target ecosystem?
- Does the project benefit from the ecosystem's tooling and community norms?
- Are there ecosystem mismatches that create adoption costs?

## Evaluation Dimensions

For each important technology choice, discuss some of the following:
- **Capability fit**: does it solve the real technical need?
- **Complexity cost**: does it introduce accidental complexity?
- **Maintainability**: how hard is it to evolve or replace?
- **Learning curve**: does it fit the expected users and contributors?
- **Portability**: does it constrain environments, platforms, or workflows?
- **Maturity risk**: stable mainstream dependency or fast-moving bet?

## Good Analysis Pattern

> The project uses Typer and Rich for the CLI surface. Typer keeps command definitions close to Python type hints, which lowers maintenance cost for a command-heavy tool, while Rich provides opinionated terminal rendering that helps the product feel polished without building a custom presentation layer. The trade-off is stronger coupling to Python CLI idioms, but for a developer-tooling product this is aligned with the audience.

This is better than saying "the project uses Typer and Rich".

## Anti-Patterns

- Listing every dependency without interpretation
- Calling a stack "modern" or "clean" without a comparison baseline
- Ignoring toolchain friction, contributor ergonomics, or release complexity
- Discussing patterns detached from the actual business or architecture needs

## Suggested Output Structure

1. Stack overview table
2. Language analysis
3. Build/package/toolchain analysis
4. Framework and library analysis
5. Design pattern and convention analysis
6. Ecosystem fit and engineering maturity evaluation
7. Risks, constraints, and possible evolution directions

## Connection With Other Guides

- Use [architect-analysis-guide.md](architect-analysis-guide.md) first to establish the macro architectural problem.
- Use [module-analysis-guide.md](module-analysis-guide.md) after this guide to explain how stack choices materialize inside modules.
- Use [deployment-analysis-guide.md](deployment-analysis-guide.md) to connect stack choices to runtime and delivery constraints.