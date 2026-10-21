# Usage Examples

Worked invocation examples for `cli-setup`. The contract layer in `SKILL.md` defines
the workflow and constraints; this file holds the concrete command sequences.


```bash
# Full workflow: install codex, configure with glm-5.2 via bailian, start in yolo mode
config_agent_install codex
config_agent_configure codex glm-5.2 bailian
config_agent_start codex yolo

# Switch claude from idealab to bailian (mutual exclusion — old config replaced)
config_agent_configure claude claude-opus-4-8 bailian

# List all supported tuples
config_agent_list

# Show what's currently configured
config_agent_show
```

