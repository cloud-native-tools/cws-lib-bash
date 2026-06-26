# Improve Agent — GitHub Copilot Guide

## Tool Mapping

| Operation | Copilot Tool/Method |
|-----------|---------------------|
| Read agent template | Open file in editor or use search to find content |
| Analyze template issues | Search across `templates/agent-role-*.md` files for patterns |
| Apply targeted fixes | Workspace edit on the target template file |
| Validate template structure | `@terminal`: `grep -c '## Identity' templates/agent-role-<slug>-template.md` |
| Check placeholder usage | `@terminal`: `grep -oE '\{\{[A-Z_]+\}\}' <file>` |
| Compare with other roles | Open multiple template files side-by-side in VS Code |

## Best Practices

- Use VS Code's side-by-side editor to compare the target template with related role templates
- Use Copilot Chat to analyze the template content and suggest improvements based on user feedback
- Make targeted workspace edits — avoid replacing large sections that may cause content loss
- Use `@terminal` for grep-based evidence when Copilot's search is insufficient

## Known Pitfalls

- **Search limitations**: Copilot's built-in search may not support complex regex. Use `@terminal` with `grep` for advanced pattern matching
- **Multi-file context**: Copilot has limited ability to hold multiple files in context simultaneously. Process one template at a time
- **Workspace edit precision**: Large file edits via workspace edit may truncate content. Prefer small, targeted changes
- **Frontmatter editing**: YAML frontmatter must remain valid after edits — verify with `@terminal` if unsure

## Capability Notes

- **Supported**: Template reading via editor, workspace edit for targeted fixes, search for evidence, terminal for validation
- **Limited**: Multi-file comparison in single chat turn; complex regex search; large-section replacement
- **Unsupported**: Automated template regeneration; agent behavior testing; cross-template consistency validation in one pass
