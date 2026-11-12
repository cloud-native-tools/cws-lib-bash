---
name: ssh-utils
description: |
  Run commands on remote hosts over SSH with deterministic quoting and safe
  non-interactive defaults. Every invocation neutralizes a preset
  `RemoteCommand` with `-o RemoteCommand=none`, streams local scripts over
  stdin, wraps execution with `su - <user>`, and propagates remote exit codes.
  Use when: running remote commands, pushing a local script to a remote host,
  executing as another user in a project directory, transferring files, or
  diagnosing SSH configuration conflicts.
  Triggers: "ssh", "ssh-utils", "remote command", "RemoteCommand", "scp",
  "remote host", "run on server", "su - user", "远程执行", "远程命令",
  "ssh 远程", "登录服务器执行", "推脚本到远端", "RemoteCommand 冲突"
skill_id: "<SKILL:.specify/skills/ssh-utils/SKILL.md>"
classification: external
---

# SSH Utilities

Own the **transport mechanics** of remote execution: connection options, quoting, stdin script push, user switching and exit-code propagation. Host aliases, users and paths are runtime policy supplied by the caller — this skill embeds none.

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.

## Overview

| Concern | Owner |
|---------|-------|
| SSH options, quoting, stdin, exit codes | this skill (`.specify/scripts/ssh-exec.py`) |
| Topology (orchestration side vs execution side) | `.specify/shared/workflow/execution-topology.md` |
| Whether to dispatch remotely | the calling skill's carrier rule |
| Remote user / path / alias values | the caller |

## Quick Reference

```bash
# Inspect effective config (detects a preset RemoteCommand)
python3 ${SKILL_HOME}/scripts/ssh-exec.py --host <alias> --check

# Run a command
python3 ${SKILL_HOME}/scripts/ssh-exec.py --host <alias> --cmd '<command>'

# Run as another user in a directory
python3 ${SKILL_HOME}/scripts/ssh-exec.py --host <alias> --user <run-user> \
  --cwd <project-dir> --cmd '<command>'

# Stream a local script over stdin (no remote temp file)
python3 ${SKILL_HOME}/scripts/ssh-exec.py --host <alias> --user <run-user> \
  --cwd <project-dir> --script <local.py> --script-arg=--project \
  --script-arg=<project-dir> --json

# Transfer
python3 ${SKILL_HOME}/scripts/ssh-exec.py --host <alias> --upload <local> --remote <remote-path>
python3 ${SKILL_HOME}/scripts/ssh-exec.py --host <alias> --download <remote-path> --local <local-path>
```

## Hard Requirements

1. **RemoteCommand is always neutralized.** Every non-interactive invocation MUST carry `-o RemoteCommand=none`. A host whose ssh_config presets `RemoteCommand` rejects a command line with `Cannot execute command-line and remote command`; this is configuration, not a security control. The wrapper enforces the option and refuses `--ssh-option RemoteCommand=<other>`.
2. **No hand-built nested quoting.** For `su -` or multi-step commands, use this wrapper instead of composing `ssh host "su - user -c '...'"` by hand. Use `--script` for script bodies; use `--cmd` only for short commands whose quoting the caller controls.
3. **Non-interactive by default.** `BatchMode=yes` fails fast instead of hanging on a password prompt; `RequestTTY=no`. Use `--allow-password` / `--tty` only for an announced human-interactive step.
4. **Exit codes are preserved.** The wrapper returns the remote exit code, `124` on local timeout (remote may still run), and `255` on SSH transport failure. Never treat a non-zero code as success.
5. **Values are policy, never embedded.** Host alias, user, project path, port, identity and config path are arguments. This skill MUST NOT contain host inventories, IP addresses, user homes or credentials.
6. **Credentials stay outside argv.** Authentication comes from ssh-agent, keys and ssh_config. Never pass passwords, tokens or private-key paths in a command string.
7. **Diagnose before improvising.** On a transport failure, run `--check` first; match the symptom in `${SKILL_HOME}/references/pitfalls.md` before changing options.

## Why `RemoteCommand=none`

OpenSSH rejects a remote command when the matching `Host` block already declares `RemoteCommand`:

```text
Cannot execute command-line and remote command.
```

`-o RemoteCommand=none` clears the inherited option for this invocation. `--check` reports `remotecommand` from `ssh -G` and warns when it is preset. Do not "fix" this by removing the user's config entry or by disabling host-key checks.

## Usage Notes

- **Scripts**: `--script` reads the file locally and sends it to `<interpreter> -`; the interpreter defaults from the suffix (`.py` → `python3`, `.sh`/`.bash` → `bash`, otherwise `sh`). Arguments use the `=` form so a leading `--` is not parsed as an option: `--script-arg=--project`.
- **Working directory**: `--cwd` accepts absolute paths and `~/...`; a leading `~` is expanded remotely, not locally.
- **Files**: upload/download stream through `cat` over the same SSH channel, so `RemoteCommand=none` applies there too. Upload requires `--remote`; download requires `--local`; the destination parent directory must already exist.
- **Timeouts**: `--connect-timeout` bounds dialing (default 10s); `--timeout` bounds the whole local run (default 0 = no limit). A timeout kills the local SSH process only.
- **Machine output**: `--json` returns host, action, remote command, exit code, duration, stdout/stderr, and transfer byte counts.
- **Dry run**: `--dry-run` prints the exact `ssh` argv, including `-o RemoteCommand=none`, without connecting.

## Workflow

1. Resolve the host alias, run user and project directory from the caller; if any is missing, ask — do not guess.
2. Run `--check` when the host is new or a transport error occurred.
3. Choose the narrowest action: `--cmd` for one command, `--script` for a local script, `--upload`/`--download` for bytes.
4. Add `--user` and `--cwd` when the command must run as the project user inside the project directory.
5. Consume the exit code; on failure read `${SKILL_HOME}/references/pitfalls.md` before retrying.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Remote command succeeded |
| 1–254 | Remote command's own exit code |
| 2 | Usage or validation error (local) |
| 124 | Local timeout; the remote process may still be running |
| 127 | `ssh` client not found on PATH |
| 255 | SSH transport failure (auth, network, host key) |

## Path Conventions

- `${SKILL_HOME}` — this skill's root directory (where this `SKILL.md` lives).
- `${SKILL_WORKDIR}` — the caller's working directory at invocation time.

## Resources

- `.specify/scripts/ssh-exec.py` — the only execution entry point; `--help` for the full option surface.
- `references/recipes.md` — intent → command recipes, including the SDD stdin-script pattern.
- `references/pitfalls.md` — symptom-first troubleshooting, starting with the RemoteCommand conflict.

## Boundary

- This skill is **transport only**: it does not decide topology, choose a remote host, provision users, edit ssh_config, or manage keys.
- Server provisioning (git user, bare repos, authorized keys, ssh_config Host entries) belongs to `git-utils` scope D.
- Interactive shells, port forwarding and tunnels are out of scope; use `ssh` directly for those.
- The wrapper executes the command it is given. Destructive remote actions keep the caller's confirmation discipline.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:ssh-utils" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:ssh-utils" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:ssh-utils" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
