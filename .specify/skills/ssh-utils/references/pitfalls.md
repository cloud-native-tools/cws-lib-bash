# Pitfalls — symptom-first troubleshooting

Run `--check` first; it resolves the effective `ssh_config` without connecting. `ssh -v` shows the auth/transport layers.

## 1. `Cannot execute command-line and remote command`

**Cause**: the matching `Host` block in ssh_config declares `RemoteCommand`. OpenSSH refuses to combine it with a command line. This is a configuration conflict, not an auth failure and not a security block.

**Fix**: carry `-o RemoteCommand=none` on the invocation. `${SKILL_HOME}/scripts/ssh-exec.py` does this on every call.

```bash
python3 ${SKILL_HOME}/scripts/ssh-exec.py --host <alias> --check
# remotecommand: echo preset   → preset detected; wrapper neutralizes it
```

Do not "fix" it by deleting the user's config entry, and do not disable strict host-key checking.

## 2. `Cannot execute command-line and remote command` from `scp` / `sftp`

The same preset applies because `scp` passes a command through ssh. Either use `--upload` / `--download` (this wrapper, which sets `RemoteCommand=none`), or add `-o RemoteCommand=none` to the `scp` call.

## 3. `Permission denied (publickey)` — authentication layer

`BatchMode=yes` is the default, so a missing key fails immediately instead of prompting.

```bash
ssh -v <alias> true 2>&1 | grep -Ei 'offering|accepted|denied|Authenticated'
ssh -G <alias> | grep -Ei '^(identityfile|identitiesonly) '
```

Check that the expected key is in the (possibly multi-line) `identityfile` list and loaded in the agent. `IdentitiesOnly yes` limits keys to those declared in config. Server-side access control (`AllowUsers`, `StrictModes`, authorized_keys permissions) is covered in `git-utils/references/server-troubleshooting.md`.

## 4. `su: Authentication failure` or the run hangs after connecting

`su - <user>` needs a password unless the connecting account is root or has a NOPASSWD rule. The wrapper cannot answer a prompt.

- Prefer `--host <user>@<host>` when the target user can log in directly.
- Otherwise ensure passwordless `su` for the connecting account.
- `--timeout` bounds the hang and returns `124`; the remote `su` may still be waiting.

## 5. Quoting is mangled or the remote shell eats arguments

Do not hand-build `ssh host "su - user -c '...'"` for anything beyond one short command. Use:

- `--script` for a script body — no remote quoting at all;
- `--script-arg=<value>` for arguments, with the `=` form;
- `--cmd` only when the caller controls the quoting of the whole string.

`--dry-run` prints the exact argv so quoting can be inspected before a connection.

## 6. `~` is not expanded

The wrapper expands a leading `~/` remotely (`"$HOME"/…`) for `--cwd`, `--remote` and `--download`. Other shell expansions are not performed: use `$HOME` explicitly if a path needs it, and prefer absolute paths in automation.

## 7. Script or stdin never arrives

Stdin is the script body for `--script` and the file body for `--upload`. Do not combine them with `--stdin-file`. For a command that reads stdin, pass `--stdin-file`; without it `--cmd` receives an empty stdin by design.

## 8. Exit code is `255`

SSH transport failure (DNS, TCP, auth, host key, protocol), not necessarily the remote command's code. The remote command's own `255` is indistinguishable — read stderr. Fix the transport before changing the command.

## 9. Exit code is `124`

The **local** timeout fired; the local SSH process was killed. The remote process may still be running. Do not retry blindly: detect remote completion (PID, sentinel file, log tail) before relaunching.

## 10. `Host key verification failed`

The host is unknown or its key changed. Verify the fingerprint out of band, then add it with `ssh-keyscan`/`known_hosts`. Do not globally disable `StrictHostKeyChecking`; at most scope an exception to one host and record why.

## 11. Connection drops during long output

Defaults set `ServerAliveInterval=15` and `ServerAliveCountMax=4`. For output-heavy runs, increase the local `--timeout` and prefer a sentinel/log-file protocol over a long-lived stream; detached execution (`nohup`) is the caller's pattern.

## 12. Locale or encoding differences

The remote login environment may not be UTF-8. Set it explicitly in the command when it matters (`LC_ALL=C.UTF-8 <command>`), and prefer `--json` for machine-readable output.
