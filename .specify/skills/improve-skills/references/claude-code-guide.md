# Improve Skills — Claude Code Guide

## Tool Mapping

| Operation | Claude Code Tool/Method |
|-----------|------------------------|
| Read SKILL.md | `Read` tool on `${SKILL_HOME}/SKILL.md` (canonical path) |
| Analyze execution history | `Read` conversation context; `Bash` for `git log` on skill files |
| Apply targeted fixes | `Edit` tool with precise `old_string` matching |
| Validate frontmatter | `Bash`: `python -c "import yaml; yaml.safe_load(open('SKILL.md').read().split('---')[1])"` |
| Check line count | `Bash`: `wc -l ${SKILL_HOME}/SKILL.md` (must stay under 500) |
| Run skill_id refresh | `Bash`: `scripts/bash/create-new-skill.sh --refresh-only --name <name> --json` |
| Verify registry | `Bash`: `grep '<skill_id>' .specify/instructions.md` |
| Move content to references | `Write` to create `${SKILL_HOME}/references/<topic>.md`, then `Edit` to replace inline content with pointer |

## Best Practices

- Always re-read SKILL.md before editing, especially after recent changes or formatter runs
- Use `Bash` with `grep` to gather concrete evidence before making changes — evidence-based improvements only
- Use `Edit` for targeted fixes; reserve `Write` for new reference files only
- After edits, verify line count stays under 500; move overflow to `${SKILL_HOME}/references/`
- Use `Agent` tool with `subagent_type="Explore"` for broad codebase analysis when gathering improvement evidence
- Check skill_id consistency by grepping `.specify/instructions.md` after any metadata changes

## Known Pitfalls

- **Symlink resolution**: `${SKILL_HOME}` resolves through symlinks. When checking file existence, use `Bash` with `readlink -f` or `ls -la` to verify the physical path
- **skill_id refresh exit code**: `create-new-skill.sh --refresh-only` may exit 0 with warnings. Always check stderr output for "not found" or "warning" messages
- **Edit after Read**: The `Read` tool shows line numbers that must NOT be included in `old_string` for `Edit` operations — match only the content after the tab
- **Registry deduplication**: When updating the Skills registry row, verify no duplicate entries exist first with `grep -c`
- **Reference chain depth**: SKILL.md → reference is max one level. Do not create references that point to other references

## Capability Notes

- **Supported**: Full SKILL.md reading/editing, evidence-based analysis, script execution, registry management, content migration to references, background validation via Agent tool
- **Limited**: Cannot test skill behavior on non-Claude Code agents; long SKILL.md files may require chunked reading
- **Unsupported**: Real-time skill execution monitoring; interactive skill testing across multiple agent runtimes
