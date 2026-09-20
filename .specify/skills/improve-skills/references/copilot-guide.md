# Improve Skills — GitHub Copilot Guide

## Tool Mapping

| Operation | Copilot Tool/Method |
|-----------|---------------------|
| Read SKILL.md | Open file in VS Code editor or use Copilot Chat file reference |
| Analyze execution history | Review recent conversation and terminal output; `@terminal` for `git log` |
| Apply targeted fixes | Workspace edit on SKILL.md |
| Validate frontmatter | `@terminal`: `python -c "import yaml; ..."` |
| Check line count | `@terminal`: `wc -l <skill-path>/SKILL.md` |
| Run skill_id refresh | `@terminal`: `scripts/bash/create-new-skill.sh --refresh-only --name <name> --json` |
| Verify discoverability | `@terminal`: `ls .specify/skills/<name>/SKILL.md` |
| Move content to references | Workspace edit to create new reference file and update SKILL.md pointer |

## Best Practices

- Use Copilot Chat to analyze SKILL.md content and identify improvement areas based on user feedback
- Make small, targeted workspace edits — large replacements may truncate content
- Use `@terminal` for all validation commands (line count, frontmatter, discoverability check)
- When moving content to references, create the reference file first, then update SKILL.md in a separate edit

## Known Pitfalls

- **Workspace edit truncation**: Large SKILL.md files (400+ lines) may cause workspace edit to lose content. Always verify file integrity after large edits
- **No background validation**: Copilot cannot run background tasks for validation. All checks must be sequential via `@terminal`
- **grep limitations in chat**: Copilot Chat's search may miss content in large files. Use `@terminal` with `grep` for reliable pattern matching
- **Rename leaves a stale directory**: discovery is by directory — after a rename, remove the old directory and verify no two `SKILL.md` files share the same frontmatter `name`
- **Path resolution**: `${SKILL_HOME}` must be resolved to the physical path manually. Use `@terminal` with `readlink -f` if needed

## Capability Notes

- **Supported**: SKILL.md reading/editing via workspace edit, terminal-based validation, Copilot Chat analysis, git log review
- **Limited**: No background tasks; workspace edit may truncate large files; single-file context per chat turn
- **Unsupported**: Agent-based parallel analysis; skill execution monitoring; cross-agent behavior testing; automated content migration
