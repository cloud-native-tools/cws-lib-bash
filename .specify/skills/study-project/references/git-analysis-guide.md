# Git Analysis Guide

## Goal

Git analysis extracts **project evolution signals** that do not appear clearly in the current snapshot of the codebase.

Source code shows what exists now. Git history helps answer:
- how the current design emerged
- which areas change frequently
- how stable the release process is
- whether the project is converging, churning, or stagnating

## What to Inspect

### 1. Commit History
Look for:
- release bursts vs steady cadence
- concentration of work in specific subsystems
- refactor waves, migrations, or rewrites
- repeated fixes in the same area, which often reveal architectural pain points

Useful questions:
- What kinds of changes dominate: features, refactors, bug fixes, docs, tooling?
- Which modules attract the most change over time?
- Are there signs of architectural stabilization or repeated churn?

### 2. Tags and Releases
Analyze:
- release frequency and naming strategy
- semantic versioning discipline or lack of it
- whether release notes suggest architecture milestones
- how tags align with visible code or tooling changes

Tags often reveal the project's external promises better than internal docs.

### 3. Branches and Development Model
Check:
- whether long-lived branches exist
- how feature work appears to be organized
- whether the repository reflects trunk-based development, Git Flow, or a lightweight hybrid
- whether stale branches suggest abandoned directions

### 4. Author and Ownership Patterns
Inspect contribution distribution:
- is design concentrated in one or two maintainers?
- are some subsystems effectively single-owner?
- does contributor diversity match the project's maturity claims?

Ownership concentration is not automatically bad, but it affects bus factor and review quality.

### 5. Architectural Evolution Events
Search for commits that indicate:
- new layering or module boundaries
- dependency swaps
- packaging or build system migration
- deployment pipeline changes
- extraction of extension points or plugins

This is where Git becomes architectural evidence rather than project management metadata.

## How to Interpret Git Evidence

### Repeated Change Is a Signal
If the same area changes repeatedly, ask why:
- unstable requirements?
- poor abstraction boundary?
- scaling pain discovered late?
- external ecosystem churn?

### Silence Is Also a Signal
An untouched module might mean:
- mature stable foundation
- dead code
- code nobody wants to touch

Use code context and docs to distinguish these possibilities.

### Do Not Overfit
One large refactor commit does not automatically prove the old design was wrong. Treat history as supporting evidence, not standalone proof.

## Practical Caveats

- Shallow clones may hide tags, branches, or deeper evolution patterns.
- Mirrored repositories may not preserve the original branching strategy.
- Squash merges can conceal the real intermediate design process.
- Generated files can distort churn statistics if not filtered.

If history is incomplete, say so explicitly.

## Suggested Output Structure

1. Repository evolution summary
2. Commit cadence and dominant change themes
3. Release and tag analysis
4. Branching and collaboration model
5. Architectural evolution milestones
6. Risk and maturity signals inferred from history

## Connection With Other Guides

- Use [architect-analysis-guide.md](architect-analysis-guide.md) to compare current architecture with its historical evolution.
- Use [tech-stack-analysis-guide.md](tech-stack-analysis-guide.md) to explain toolchain or dependency migrations.
- Use [deployment-analysis-guide.md](deployment-analysis-guide.md) when release history reflects operational changes.