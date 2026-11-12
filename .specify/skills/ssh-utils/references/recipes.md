# Recipes — intent to command

All commands use `${SKILL_HOME}/scripts/ssh-exec.py`. Replace `<alias>`, `<run-user>`, `<project-dir>` and paths with caller-supplied values.

## Inspect the effective configuration

```bash
python3 ${SKILL_HOME}/scripts/ssh-exec.py --host <alias> --check
```

Reports `hostname`, `user`, `port`, `identityfile`, `proxyjump` and `remotecommand` from `ssh -G`. When `remotecommand` is not `none`, the config presets a command — the exact case that makes a plain `ssh <alias> "cmd"` fail.

## Run one command

```bash
python3 ${SKILL_HOME}/scripts/ssh-exec.py --host <alias> --cmd 'uname -a'
```

`--cmd` is a shell command string executed on the remote login shell. Keep it short; when the command contains nested quotes, use `--script` instead of escaping by hand.

## Run as another user inside a directory

```bash
python3 ${SKILL_HOME}/scripts/ssh-exec.py --host <alias> \
  --user <run-user> --cwd <project-dir> --cmd 'specify check'
```

The wrapper composes `su - <run-user> -c '<cd ... && command>'` with POSIX quoting. `su` must be passwordless for the connecting account (root or a NOPASSWD rule); otherwise the run hangs until `--timeout` fires. Prefer `--host <user>@<host>` when the target user can log in directly.

## Stream a local script over stdin

This is the SDD inventory pattern: the script never lands on the remote disk.

```bash
python3 ${SKILL_HOME}/scripts/ssh-exec.py --host <alias> \
  --user <run-user> --cwd <project-dir> \
  --script ${SKILL_HOME}/path/to/inventory.py \
  --script-arg=--project --script-arg=<project-dir> --json
```

- Interpreter defaults from the suffix: `.py` → `python3`, `.sh`/`.bash` → `bash`, otherwise `sh`; override with `--script-interpreter`.
- Use `--script-arg=<value>` (with `=`) so an argument beginning with `--` is not parsed as a wrapper option.
- Script arguments are sent verbatim — no remote tilde or glob expansion. Pass absolute paths.
- Stdin is the script body. Do not also pass `--stdin-file`.

## Upload and download

```bash
# upload; a trailing / on --remote appends the local basename
python3 ${SKILL_HOME}/scripts/ssh-exec.py --host <alias> \
  --upload ./runner.sh --remote /home/<run-user>/ --mode 0755

# download
python3 ${SKILL_HOME}/scripts/ssh-exec.py --host <alias> \
  --download /home/<run-user>/run.log --local ./run.log
```

Both stream bytes through the SSH channel, so `RemoteCommand=none` and the same auth path apply. Parent directories are not created.

## Feed stdin to a command

```bash
python3 ${SKILL_HOME}/scripts/ssh-exec.py --host <alias> \
  --cmd 'wc -l' --stdin-file ./input.txt
```

Without `--script`, `--upload` or `--stdin-file`, `--cmd` receives an empty stdin so a caller without a pipe cannot hang the run.

## Extra SSH options

```bash
python3 ${SKILL_HOME}/scripts/ssh-exec.py --host <alias> --cmd true \
  --port 2222 --identity ~/.ssh/id_work --config ./ssh_config \
  --ssh-option ProxyJump=bastion
```

`--ssh-option RemoteCommand=<anything but none>` is refused: it would reintroduce the conflict this skill exists to remove.

## Long-running work

`--timeout` is a local bound only — on timeout the remote process may keep running. For a run that must outlive the SSH connection, launch it detached on the remote side (`nohup … &` with all three redirections) and poll with a status file; the orchestration of detached runs belongs to the caller (for SDD stage loops, `sdd-loop-driver`).

## JSON consumption

```json
{
  "host": "devbox",
  "action": "script",
  "remoteCommand": "su - deploy -c 'cd /srv/app && python3 - --project /srv/app'",
  "exitCode": 0,
  "durationMs": 412,
  "stdout": "...",
  "stderr": "",
  "bytesSent": 2048
}
```

For downloads, `stdout` is empty and `bytesWritten` carries the size. `--dry-run --json` returns the exact `argv` without connecting.
