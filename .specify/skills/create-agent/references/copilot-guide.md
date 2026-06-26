# Create Agent — GitHub Copilot Guide

## Tool Mapping

| Operation | Copilot Tool/Method |
|-----------|---------------------|
| Create new .agent.md file | Workspace edit to `.specify/agents/<name>.agent.md` |
| Update existing .agent.md | Workspace edit with targeted replacement |
| Validate YAML frontmatter | `@terminal`: `python -c "import yaml; ..."` |
| Check for existing agents | `@terminal`: `ls .specify/agents/*.agent.md` |
| Test agent invocation | Use VS Code agent picker to find and invoke the new agent |
| Verify symlinks | `@terminal`: `ls -la .github/agents/` |
| Update instructions registry | Workspace edit on `.specify/instructions.md` |

## Best Practices

- Test agent discoverability via the VS Code agent picker immediately after creation
- Use Copilot-native frontmatter: `model: "GPT-5 (copilot)"` for the model field
- When creating agents meant for Copilot, include `@agent` mention examples in the description
- Verify `.github/agents/` symlink exists — this is how Copilot discovers custom agents

## Known Pitfalls

- **Workspace edit scope**: Large `.specify/instructions.md` files may cause workspace edit to truncate content. Make small, targeted edits
- **Agent picker delay**: Newly created agents may not appear in the VS Code agent picker until the window is reloaded
- **Frontmatter format**: Copilot is stricter about YAML formatting — ensure no trailing whitespace in frontmatter fields
- **Symlink creation**: Copilot cannot create symlinks. If `.github/agents/` doesn't exist, advise the user to run `specify init`

## Capability Notes

- **Supported**: Agent file creation via workspace edit, frontmatter editing, agent picker testing, terminal-based validation
- **Limited**: Cannot create symlinks; workspace edit may truncate large files; no sandboxed agent testing
- **Unsupported**: Agent tool delegation; background agent testing; programmatic agent invocation
