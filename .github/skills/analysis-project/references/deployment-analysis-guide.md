# Deployment Analysis Guide

## Goal

Deployment analysis explains **how the project leaves the repository and becomes a runnable, operable system**.

This includes packaging, environment assumptions, runtime topology, delivery workflow, configuration handling, and operational safety. Many architecture reports are incomplete because they stop at code boundaries and ignore how the system actually runs.

## Questions Deployment Analysis Must Answer

1. **What gets deployed?** Binary, package, container, static assets, generated config, scripts, templates
2. **Where does it run?** Local developer machine, CI runner, server, container platform, edge environment, air-gapped system
3. **How is it configured?** Files, environment variables, flags, secrets, service discovery
4. **How is it upgraded or rolled back?** Release artifact, tag, migration step, compatibility strategy
5. **What operational dependencies exist?** Databases, caches, queues, cloud services, shells, runtimes, system packages

## What to Inspect

### 1. Packaging and Delivery Artifacts
Check for:
- Dockerfiles, compose files, Helm charts, systemd units, installers
- package manifests and publish configuration
- CI workflows producing build artifacts
- scripts that bootstrap or install the project

Explain the relationship between source layout and deployable artifact.

### 2. Runtime Topology
Describe the runtime architecture:
- single-process vs multi-service
- local-only vs distributed deployment
- control plane vs data plane roles
- synchronous vs asynchronous operational dependencies

Use diagrams where helpful. A simple CLI may have a lightweight deployment story; a platform product may have a full topology to analyze.

### 3. Environment and Configuration Model
Analyze:
- config files, templates, defaults, and overrides
- secrets handling
- environment-specific behavior
- startup validation and preflight checks

Good deployment analysis explains not only where config lives, but which assumptions the system makes about its environment.

### 4. CI/CD and Operational Workflow
Look at:
- build/test/release workflows
- publish or release automation
- migration or rollout scripts
- verification, smoke tests, or post-deploy checks

The goal is to understand whether the delivery process is manual, scripted, or fully automated.

### 5. Operability and Failure Handling
Evaluate:
- logging, metrics, traces, health checks
- retry and timeout strategy for external dependencies
- rollback or recovery path
- resilience under partial failure

If deployment is simple because the project is a local tool, say that clearly instead of inventing distributed-systems concerns.

## Interpretation Heuristics

### Deployment Simplicity Can Be a Product Decision
A deliberately lightweight deployment model can be a strategic advantage, especially for developer tools and local-first software.

### Hidden Operational Coupling Is a Risk
If the runtime looks simple but depends on undocumented shells, system packages, environment layout, or network assumptions, call that out as hidden deployment complexity.

### Packaging Choices Reflect Audience Assumptions
For example:
- Python package + `uvx` suggests developer-tool ergonomics
- container image + orchestrator manifests suggests service deployment as a product concern
- shell scripts plus templates may suggest bootstrap-heavy environments or portability trade-offs

## Suggested Output Structure

1. Deployment target and artifact summary
2. Runtime topology or execution model
3. Configuration and environment assumptions
4. Delivery pipeline and release process
5. Operability, resilience, and rollback analysis
6. Deployment strengths, risks, and evolution opportunities

## Connection With Other Guides

- Use [architect-analysis-guide.md](architect-analysis-guide.md) to connect runtime topology back to architectural intent.
- Use [tech-stack-analysis-guide.md](tech-stack-analysis-guide.md) to explain how the packaging and runtime stack shape deployment.
- Use [git-analysis-guide.md](git-analysis-guide.md) when release history or tag cadence reveals deployment maturity.