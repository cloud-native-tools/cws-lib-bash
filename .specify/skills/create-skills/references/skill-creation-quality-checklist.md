# Skill Creation Quality Checklist

Use this checklist to validate a newly created Skill before reporting completion.

## Metadata & Frontmatter

- [ ] `name` matches the Skill directory name
- [ ] `description` includes trigger keywords and scenarios (not vague)
- [ ] `skill_id` is present and uses the `<SKILL:.specify/skills/<name>/SKILL.md>` format
- [ ] Optional frontmatter fields (`argument-hint`, `user-invocable`, `disable-model-invocation`) are only present when needed

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

## Registry & Discoverability

- [ ] `.specify/instructions.md` Skills table has one deduplicated row
- [ ] `Skill Name`, `Skill ID`, `Description`, and `Canonical Path` columns are populated
- [ ] `None yet.` placeholder is removed if this is the first entry

## Anti-Pattern Prevention

- [ ] Description is not vague (includes trigger keywords)
- [ ] Skill name matches the project validator (`[A-Za-z0-9_-]+`); newly invented names prefer lowercase kebab-case (`[a-z0-9]+(-[a-z0-9]+)*`)
- [ ] `SKILL.md` is not oversized (under 500 lines)
- [ ] Steps are executable (not just context/background)
- [ ] Resource paths are consistent and point to existing files

## Validation

- [ ] Frontmatter is valid YAML
- [ ] All referenced resource paths resolve correctly
- [ ] The Skill can be discovered via its trigger description in a fresh context