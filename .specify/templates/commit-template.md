
# Git Commit Message Template

> Goal: Generate a **single-line**, concise, readable, traceable commit message for use with:
>
> `git commit -m "{msg}"`

## Output (single line)

The rendered `{msg}` **MUST** be exactly one line:

```text
[TYPE]([SCOPE]): [SUBJECT]
```

## Placeholders

- `[TYPE]`: Commit type (see Allowed types below)
- `[SCOPE]`: Scope of impact (prefer feature/spec key, e.g., `NNN-short-name`)
- `[SUBJECT]`: One-line summary (imperative/verb-first, ≤72 chars preferred)

Optional context fields (for generating `[SCOPE]` / `[SUBJECT]`):

- `[BRANCH]`: Current branch name (e.g., `feat/123-login-reset`)
- `[REQUIREMENTS_KEY]`: spec directory key (e.g., `123-login-reset`)
- `[FEATURE_TITLE]`: Feature title (prefer from requirements.md title)
- `[DATE]`: ISO date (YYYY-MM-DD)

## Allowed types

Choose one from the following set as priority:

- `feat`: New/implemented user-visible capability (typically includes `src/` or runtime logic changes)
- `fix`: Bug fix
- `docs`: Documentation/spec/instructions only (does not change runtime behavior)
- `test`: Test-only changes
- `chore`: Build/tooling/dependency/misc (CI, scripts, formatting, etc.)

## Scope rules

1. **Prefer** using `[REQUIREMENTS_KEY]` as `[SCOPE]`:
	- Derive from the directory name under `.specify/specs/[REQUIREMENTS_KEY]/` (e.g., `123-login-reset`)
2. If `[REQUIREMENTS_KEY]` is unavailable:
	- Derive a short scope from `[BRANCH]` (strip prefixes like `feat/`, `fix/`, `chore/`; truncate if necessary)
3. `[SCOPE]` should be short, stable, and traceable (mappable to a spec directory or feature registry)

## Subject rules

- Use imperative / verb-first: Implement/Add/Fix/Update/Refactor… (be concise and consistent)
- Avoid trailing period
- Avoid vague expressions: e.g., "update stuff / misc changes"
- Prefer aligning subject with `[FEATURE_TITLE]` or spec document semantics

## Recommended patterns

- `feat([SCOPE]): implement [FEATURE_TITLE]`
- `fix([SCOPE]): resolve <short-problem>`
- `docs([SCOPE]): update specs and plans`

## Examples

```text
feat(123-login-reset): implement password reset flow
fix(123-login-reset): prevent token reuse after reset
docs(123-login-reset): align requirements and plan
chore(tooling): refresh prereq scripts
```

