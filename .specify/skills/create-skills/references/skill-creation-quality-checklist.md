# Skill Creation Quality Checklist

Use this checklist to validate a newly created Skill before reporting completion.

## Metadata & Frontmatter

- [ ] `name` matches the Skill directory name
- [ ] `description` includes trigger keywords and scenarios (not vague)
- [ ] `description` does NOT summarize the workflow body — capability + triggers only (a workflow summary invites agents to skip loading the body)
- [ ] `skill_id` is present and uses the `<SKILL:.specify/skills/<name>/SKILL.md>` format
- [ ] Optional frontmatter fields (`argument-hint`, `user-invocable`, `disable-model-invocation`) are only present when needed

## Self-Improvement

- [ ] The generated Skill contains `## Self-Improvement Contract` exactly once, immediately before `## Feedback`.
- [ ] The contract identifies canonical owner, own-run evidence, `improve-skills`, validation, later comparison, and escalation by referencing `.specify/shared/workflow/self-improvement-workflow.md` rather than copying it.
- [ ] It does not authorize same-run self-editing, permission expansion, or an outcome claim before comparison.

## Structure & Sizing

- [ ] `SKILL.md` is under 500 lines
- [ ] Body starts with a clear Goal section
- [ ] Workflow steps are executable and checkable (not just background prose)
- [ ] Large details are moved to `./references/` with clear links from `SKILL.md`
- [ ] Reference chain is at most one level deep

## Resource Organization

- [ ] Resource paths use relative form (e.g., `./scripts/x.py`, `./references/details.md`)
- [ ] `scripts/`, `references/`, `assets/` contents are relevant when checked in; empty standard directories are acceptable
- [ ] No unrelated documents (README.md, CHANGELOG.md, INSTALLATION_GUIDE.md)

## Discoverability (no registry)

- [ ] `.specify/skills/<name>/SKILL.md` exists and is discoverable by directory scan (the discovery mechanism — see `.specify/skills.md`)
- [ ] Frontmatter `name` matches the directory name; no other directory under `.specify/skills/` carries the same `name` value
- [ ] No registration table is written — skills are found via their directories, not registered

## Anti-Pattern Prevention

- [ ] Description is not vague (includes trigger keywords)
- [ ] Skill name matches the project validator (`[A-Za-z0-9_-]+`); newly invented names prefer lowercase kebab-case (`[a-z0-9]+(-[a-z0-9]+)*`)
- [ ] `SKILL.md` is not oversized (under 500 lines)
- [ ] Steps are executable (not just context/background)
- [ ] Resource paths are consistent and point to existing files

## Token Efficiency (纪律引用: `.specify/shared/guidelines/token-efficiency.md`)

- [ ] Deterministic steps go to programs (token-efficiency program-first): every fixed-rule text/data judgment in the workflow (pattern match, structural validation, counting, dedup, diff) is delegated to a script/engine step, not the LLM
- [ ] Data access is summary-level (token-efficiency summary-first): no step instructs injecting a machine-managed data file whole into LLM context; digests/projections/excerpts are used, with escalation per the discipline doc

## Validation

- [ ] Frontmatter is valid YAML
- [ ] All referenced resource paths resolve correctly
- [ ] The Skill can be discovered via its trigger description in a fresh context