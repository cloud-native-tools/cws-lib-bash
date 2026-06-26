# Improve Agent — Claude Code Guide

## Tool Mapping

| Operation | Claude Code Tool/Method |
|-----------|------------------------|
| Read agent template | `Read` tool on `templates/agent-role-<slug>-template.md` |
| Analyze template issues | `Bash`: `grep -n '<pattern>' templates/agent-role-*.md` for evidence gathering |
| Apply targeted fixes | `Edit` tool with precise `old_string` matching on template files |
| Validate template structure | `Bash`: `grep -c '## Identity' templates/agent-role-<slug>-template.md` |
| Check placeholder usage | `Bash`: `grep -oE '\{\{[A-Z_]+\}\}' templates/agent-role-<slug>-template.md` |
| Compare with other roles | `Read` tool on related role templates for consistency checks |

## Best Practices

- Always `Read` the full template before editing — templates can be long and context matters
- Use `Bash` with `grep` for evidence gathering before making changes — avoid inference-only improvements
- Make minimal, targeted edits via `Edit` tool — avoid rewriting entire sections
- After edits, re-read the template to verify the change integrated correctly
- Check handoff chain consistency by reading upstream/downstream role templates

## Known Pitfalls

- **Context window limits**: Large templates (100+ lines) may cause context issues. Focus `Read` on specific line ranges when needed
- **Placeholder drift**: Verify that `{{PLACEHOLDER}}` variables used in the template match the approved list from `/speckit.agents` command
- **Edit precision**: `old_string` must match exactly including whitespace. Read the file first to get exact content
- **Template vs generated agent**: This skill modifies `templates/` files, NOT `.specify/agents/` files. Confusing the two leads to lost changes

## Capability Notes

- **Supported**: Full template reading, precise editing, grep-based evidence gathering, cross-template comparison, YAML frontmatter validation
- **Limited**: Cannot test the improved template's effect on agent behavior without running `/speckit.agents` to regenerate
- **Unsupported**: Interactive testing of generated agents in non-Claude Code contexts
