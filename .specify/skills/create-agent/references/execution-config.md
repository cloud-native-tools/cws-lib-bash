# Execution Config Schema (`configs/<slug>.yaml`)

Dispatch configuration for one agent. Path layout and the rules that govern it stay in
`SKILL.md` (`## Execution Config Capability`); this file holds the field-level schema.


```yaml
agent: <slug>              # the Instance/Template this config dispatches (templates/ or instances/)
mode: external             # native | virtual | external (subagent-definitions.md)
cli: qodercli              # external only: agent CLI binary
model: auto                # optional per-dispatch overrides
reasoning_effort: ""
context_window: ""
extra_flags: ""            # appended CLI flags
log_dir: .specify/agents/execution/logs
```

