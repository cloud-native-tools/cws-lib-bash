# Create Agent — Claude Code Guide

## Tool Mapping

| Operation | Claude Code Tool/Method |
|-----------|------------------------|
| Create new .agent.md file | `Write` tool to `.specify/agents/<name>.agent.md` |
| Update existing .agent.md | `Edit` tool with precise `old_string` matching |
| Validate YAML frontmatter | `Bash`: `python -c "import yaml; yaml.safe_load(open('<file>').read().split('---')[1])"` |
| Check for existing agents | `Bash`: `ls .specify/agents/*.agent.md 2>/dev/null` |
| Test agent invocation | `Agent` tool with the new agent name to test it responds correctly |
| Verify symlinks | `Bash`: `ls -la .github/agents/ .qoder/agents/ 2>/dev/null` |
| Update instructions registry | `Edit` tool on `.specify/instructions.md` with precise string matching |

## Best Practices

- Use `Write` for new agent files, `Edit` for modifications — `Write` on existing files overwrites the entire content without warning
- Always read the existing agent file before editing to avoid stale `old_string` matches
- After creating an agent, verify it's discoverable by checking symlink directories
- Use `Agent` tool to test the new agent in a sandboxed context before reporting success
- When updating the Resource Registry in `.specify/instructions.md`, match the exact existing table row to avoid clobbering

## Known Pitfalls

- **Write vs Edit confusion**: Using `Write` on an existing .agent.md replaces all content. Always check existence first with `Bash` tool, then use `Edit` for updates
- **Frontmatter parsing**: Claude Code's `Read` tool shows line numbers that must NOT be included in `old_string` for `Edit` operations
- **Agent tool subagent_type**: When testing with `Agent` tool, the `subagent_type` parameter cannot reference custom .agent.md files directly — it uses registered agent types
- **Symlink verification**: Directory-level symlinks (`.github/agents/ → .specify/agents/`) may not exist if `specify init` hasn't been run for all tools

## Capability Notes

- **Supported**: Full YAML frontmatter validation, file creation/editing, symlink verification, registry updates, agent testing via Agent tool
- **Limited**: Cannot test agent behavior in Copilot/Qoder context — only tests in Claude Code's own agent framework
- **Unsupported**: Creating agents for unsupported providers; interactive agent picker testing
