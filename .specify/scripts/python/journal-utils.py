#!/usr/bin/env python3
"""journal-utils.py — the one deterministic journal engine (Feature 096).

Contracts: `contracts/journal-engine.contract.md` C-01…C-13 and
`contracts/journal-format.contract.md` C-01…C-12. The spelling face (journal filename, header
keys, entry columns, the closed event classes with their minimum persistent evidence, retention
classes, pointer kinds, the missing placeholder and the escape rule) is read from
`.specify/shared/declarations/facts/journal-format.yaml` through `.specify/scripts/python/declaration_reader.py`;
valid stage names come from `.specify/shared/declarations/facts/driver-stage-sequence.yaml` and the
completion-sentinel template from `.specify/shared/declarations/facts/driver-completion-sentinels.yaml`.
This module holds no second copy of any of them.

Two actions, a closed exit-code set: `append` projects carrier facts into `<spec-dir>/journal.md`
under a non-blocking exclusive flock on the journal itself; `check` validates an existing journal
and is strictly read-only. Stdlib only; CPython >=3.8.
"""
from __future__ import annotations

import argparse
import calendar
import fcntl
import json
import re
import subprocess
import sys
import time
from pathlib import Path

# --------------------------------------------------------------------------- #
# wiring: the one declaration reader and the script-interface helper
# --------------------------------------------------------------------------- #
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

try:  # the layer's one read entry (C-11); a copy without it degrades to owner-unavailable
    import declaration_reader
except ImportError:  # pragma: no cover - the framework tree always carries the reader
    declaration_reader = None

try:  # the helper owns the rule; an engine copied WITHOUT it still runs its actions
    from script_interface_cli import configure_parser as _sig_configure
    from script_interface_cli import guard_argv as _sig_guard
except ImportError:  # pragma: no cover - a sandbox/handler copy carries the engine only
    def _sig_configure(parser, **_kwargs):
        return parser

    def _sig_guard(_argv=None, declared=None, **_kwargs):
        return None

FACT_SLUG = "journal-format"
STAGE_FACT_SLUG = "driver-stage-sequence"
SENTINEL_FACT_SLUG = "driver-completion-sentinels"

ISO_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
ISO_RE = re.compile(ISO_PATTERN)
ISO_WRITE = "%Y-%m-%dT%H:%M:%SZ"

#: The header keys and entry columns the engine knows how to fill. The owner declares the text and
#: the order; this set only names the semantics the engine can supply (C-11 keeps the domains).
HEADER_SEMANTICS = ("line_id", "run_id", "spec", "observer_instance", "created_at")
ROW_SEMANTICS = ("seq", "observed_at", "event_at", "stage", "event", "command", "artifact", "exit",
                 "evidence")

OBSERVER_HEADING_RE = re.compile(r"^##\s+Observer Record\s+—\s+(.+?)\s*$")
ISO_FIELD_RE = re.compile(ISO_PATTERN)
EVIDENCE_SPLIT = "; "


class EngineError(Exception):
    """One typed error: ``label`` prints verbatim and ``code`` is the closed exit code."""

    def __init__(self, label, code=2):
        super().__init__(label)
        self.label = label
        self.code = code


# --------------------------------------------------------------------------- #
# the declaration layer
# --------------------------------------------------------------------------- #
def _load_statement(repo, slug):
    if declaration_reader is None:
        raise EngineError("owner-unavailable: %s" % slug)
    try:
        fact = declaration_reader.load_fact(str(repo), slug)
    except declaration_reader.DeclarationError as error:
        raise EngineError("owner-unavailable: %s" % (getattr(error, "slug", None) or slug))
    return fact["body"].get("statement")


def load_format(repo):
    """The format owner's statement, validated and normalized (no default is invented here)."""
    statement = _load_statement(repo, FACT_SLUG)
    if not isinstance(statement, dict):
        raise EngineError("owner-unavailable: %s" % FACT_SLUG)
    required = ("journal_filename", "title_template", "header_keys", "entry_columns",
                "event_classes", "retention_classes", "pointer_kinds", "missing_placeholder",
                "escaping")
    if any(key not in statement for key in required):
        raise EngineError("owner-unavailable: %s" % FACT_SLUG)
    header_keys = [str(key) for key in statement["header_keys"]]
    if len(header_keys) != len(set(header_keys)) or set(header_keys) != set(HEADER_SEMANTICS):
        raise EngineError("owner-unavailable: %s" % FACT_SLUG)
    columns = [str(key) for key in statement["entry_columns"]]
    if len(columns) != len(set(columns)) or set(columns) != set(ROW_SEMANTICS):
        raise EngineError("owner-unavailable: %s" % FACT_SLUG)
    events = {}
    for item in statement["event_classes"]:
        if not isinstance(item, dict) or "name" not in item or "min_persistent" not in item:
            raise EngineError("owner-unavailable: %s" % FACT_SLUG)
        try:
            events[str(item["name"])] = int(item["min_persistent"])
        except (TypeError, ValueError):
            raise EngineError("owner-unavailable: %s" % FACT_SLUG)
    escaping = statement["escaping"]
    if not isinstance(escaping, dict) or "pipe_escape" not in escaping \
            or "newline_replacement" not in escaping:
        raise EngineError("owner-unavailable: %s" % FACT_SLUG)
    return {
        "filename": str(statement["journal_filename"]),
        "title_template": str(statement["title_template"]),
        "header_keys": header_keys,
        "columns": columns,
        "events": events,
        "retentions": {str(value) for value in statement["retention_classes"]},
        "kinds": {str(value) for value in statement["pointer_kinds"]},
        "placeholder": str(statement["missing_placeholder"]),
        "pipe_escape": str(escaping["pipe_escape"]),
        "newline": str(escaping["newline_replacement"]),
        "stages": [],
    }


def load_stages(repo):
    statement = _load_statement(repo, STAGE_FACT_SLUG)
    if not isinstance(statement, list) or not statement:
        raise EngineError("owner-unavailable: %s" % STAGE_FACT_SLUG)
    return [str(stage) for stage in statement]


def load_sentinel_template(repo):
    statement = _load_statement(repo, SENTINEL_FACT_SLUG)
    if not isinstance(statement, dict) or "pattern" not in statement:
        raise EngineError("owner-unavailable: %s" % SENTINEL_FACT_SLUG)
    return str(statement["pattern"]), str(statement.get("transform") or "")


def sentinel_for(stage, template):
    pattern, transform = template
    value = stage.upper() if transform == "uppercase" else stage
    return pattern.replace("{stage}", value)


# --------------------------------------------------------------------------- #
# time and paths
# --------------------------------------------------------------------------- #
def utc_now():
    return time.strftime(ISO_WRITE, time.gmtime())


def epoch_to_iso(value):
    try:
        return time.strftime(ISO_WRITE, time.gmtime(int(float(value))))
    except (TypeError, ValueError, OverflowError):
        return None


def iso_to_epoch(value):
    try:
        return calendar.timegm(time.strptime(value, ISO_WRITE))
    except (TypeError, ValueError):
        return None


def rel(path, repo):
    try:
        return Path(path).resolve().relative_to(Path(repo).resolve()).as_posix()
    except ValueError:
        return Path(path).resolve().as_posix()


def pointer(retention, kind, target, anchor=None):
    text = "%s:%s:%s" % (retention, kind, target)
    if anchor:
        text += "#" + anchor
    return text


def _read_text(path):
    return Path(path).read_text(encoding="utf-8")


def _last_nonempty(text):
    last = ""
    for line in text.splitlines():
        if line.strip():
            last = line.strip()
    return last


def _last_anomaly(text):
    """The log's last `ANOMALY:` line — it survives a later completion sentinel."""
    last = None
    for line in text.splitlines():
        if line.strip().startswith("ANOMALY:"):
            last = line.strip()
    return last


def _field(line, name):
    match = re.search(r"(?:^|\s)%s=(\S+)" % re.escape(name), line or "")
    return match.group(1) if match else None


# --------------------------------------------------------------------------- #
# the state spine
# --------------------------------------------------------------------------- #
def read_spine(path):
    try:
        text = _read_text(path)
    except OSError as error:
        raise EngineError("input-error: spine unreadable: %s" % (error.strerror or error))
    lines = text.splitlines()
    sections, current = [], None
    for line in lines:
        stripped = line.strip()
        # The shape owner (SKILL.md § SDD Observer) prints the section inside an indented
        # fenced block; a verbatim copy is legal, so leading whitespace never decides a heading.
        heading = OBSERVER_HEADING_RE.match(stripped)
        if heading:
            current = {"anchor": stripped[3:].strip(),
                       "timestamp": heading.group(1).strip(), "fields": {}}
            sections.append(current)
            continue
        if stripped.startswith("## "):
            current = None
            continue
        if current is not None:
            item = re.match(r"^-\s+([A-Za-z_]+):\s*(.*)$", stripped)
            if item:
                current["fields"][item.group(1)] = item.group(2).strip()
    attempts = re.findall(r"attempts[:：]\s*(\d+)", text)
    stages = re.findall(r"^stage[:：]\s*(\S+)\s*$", text, re.M)
    return {
        "record": sections[-1] if sections else None,
        "has_u0": any(re.match(r"^##\s+U0\b", line) for line in lines),
        "stalled": bool(re.search(r"卡死状态[:：]\s*stalled", text)),
        "attempts": int(attempts[-1]) if attempts else 0,
        "stage": stages[-1] if stages else None,
    }


def check_identity(spine_state, line_id, run_id, execution_label):
    """C-07 / V-16: the latest record must describe this execution, and must be `started`."""
    record = spine_state["record"]
    if record is None:
        raise EngineError("identity-mismatch: no observer record section")
    fields = record["fields"]
    if fields.get("state") != "started":
        raise EngineError("identity-mismatch: state=%s" % fields.get("state"))
    if fields.get("line_id") != line_id:
        raise EngineError("identity-mismatch: line_id")
    if fields.get("run_id") != run_id:
        raise EngineError("identity-mismatch: run_id")
    if fields.get("execution_label") != execution_label:
        raise EngineError("identity-mismatch: execution_label")
    return record


# --------------------------------------------------------------------------- #
# the journal: parse, render, findings (V-1…V-13, V-17)
# --------------------------------------------------------------------------- #
def split_cells(line):
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells, current, index = [], [], 0
    while index < len(body):
        char = body[index]
        if char == "\\" and index + 1 < len(body) and body[index + 1] == "|":
            current.append("|")
            index += 2
            continue
        if char == "|":
            cells.append("".join(current).strip())
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    cells.append("".join(current).strip())
    return cells


def escape_value(value, fmt):
    text = str(value)
    text = text.replace("|", fmt["pipe_escape"])
    return text.replace("\r", fmt["newline"]).replace("\n", fmt["newline"])


def render_cells(values, fmt):
    return "| " + " | ".join(escape_value(value, fmt) for value in values) + " |"


def parse_pointers(text, fmt):
    """E-7 grammar; returns ``(pointers, invalid)`` where pointers are 4-tuples."""
    if not text or text == fmt["placeholder"]:
        return [], 0
    pointers, invalid = [], 0
    for chunk in text.split(EVIDENCE_SPLIT):
        chunk = chunk.strip()
        if not chunk:
            invalid += 1
            continue
        retention, sep1, rest = chunk.partition(":")
        kind, sep2, target = rest.partition(":")
        if not sep1 or not sep2 or not target:
            invalid += 1
            continue
        anchor = None
        if "#" in target:
            target, _, anchor = target.partition("#")
        if retention not in fmt["retentions"] or kind not in fmt["kinds"] or not target:
            invalid += 1
            continue
        pointers.append((retention, kind, target, anchor))
    return pointers, invalid


class Journal:
    """One journal file read into rows plus the validation findings that read produced."""

    def __init__(self, path, repo, fmt):
        self.path = Path(path)
        self.repo = Path(repo)
        self.fmt = fmt
        self.text = ""
        self.header = {}
        self.rows = []
        self.findings = []
        self.table_found = False
        self._resolved = {}
        if self.path.is_file():
            self.text = _read_text(self.path)
            self._parse()

    # -- parsing ----------------------------------------------------------- #
    def _parse(self):
        lines = self.text.splitlines()
        if not lines:
            self.findings.append(("V-1", 1))
            self.findings.append(("V-2", 1))
            return
        index = 1
        while index < len(lines):
            stripped = lines[index].strip()
            if not stripped:
                index += 1
                continue
            if stripped.startswith("|"):
                break
            item = re.match(r"^-\s+([A-Za-z_]+):\s*(.*)$", stripped)
            if item:
                self.header[item.group(1)] = item.group(2).strip()
            else:
                self.findings.append(("V-12", index + 1))
            index += 1
        if set(self.header) != set(self.fmt["header_keys"]) \
                or len(self.header) != len(self.fmt["header_keys"]):
            self.findings.append(("V-1", min(2, len(lines))))
        if "created_at" in self.header and not ISO_FIELD_RE.match(self.header["created_at"]):
            self.findings.append(("V-1", min(2, len(lines))))
        if index >= len(lines):
            self.findings.append(("V-2", max(len(lines), 1)))
            return
        header_line = index + 1
        if split_cells(lines[index]) != self.fmt["columns"]:
            self.findings.append(("V-2", header_line))
        self.table_found = True
        index += 1
        if index < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[index].strip()):
            index += 1
        else:
            self.findings.append(("V-2", header_line))
        expected_seq = 1
        while index < len(lines):
            stripped = lines[index].strip()
            if not stripped:
                index += 1
                continue
            if not stripped.startswith("|"):
                break
            cells = split_cells(lines[index])
            line_no = index + 1
            if len(cells) != len(self.fmt["columns"]):
                self.findings.append(("V-11", line_no))
                index += 1
                continue
            values = dict(zip(self.fmt["columns"], cells))
            self.rows.append({"line_no": line_no, "values": values})
            self._validate_row(values, line_no, expected_seq)
            expected_seq += 1
            index += 1
        while index < len(lines):
            stripped = lines[index].strip()
            if not stripped:
                index += 1
                continue
            if stripped.startswith("|"):
                self.findings.append(("V-2", index + 1))
            else:
                self.findings.append(("V-12", index + 1))
            index += 1
        self._validate_gaps()

    def _validate_row(self, values, line_no, expected_seq):
        placeholder = self.fmt["placeholder"]
        try:
            if int(values["seq"]) != expected_seq:
                self.findings.append(("V-3", line_no))
        except ValueError:
            self.findings.append(("V-3", line_no))
        if not ISO_FIELD_RE.match(values["observed_at"]):
            self.findings.append(("V-4", line_no))
        if values["event_at"] != placeholder and not ISO_FIELD_RE.match(values["event_at"]):
            self.findings.append(("V-4", line_no))
        if values["event"] not in self.fmt["events"]:
            self.findings.append(("V-5", line_no))
        if values["stage"] != placeholder and values["stage"] not in self.fmt["stages"]:
            self.findings.append(("V-6", line_no))
        if values["exit"] != placeholder:
            try:
                int(values["exit"])
            except ValueError:
                self.findings.append(("V-7", line_no))
        pointers, invalid = parse_pointers(values["evidence"], self.fmt)
        if invalid:
            self.findings.append(("V-8", line_no))
        if not pointers:
            self.findings.append(("V-9", line_no))
        else:
            minimum = self.fmt["events"].get(values["event"], 0)
            if minimum == 1 and not any(item[0] == "persistent" for item in pointers):
                self.findings.append(("V-9", line_no))
            for retention, kind, target, _anchor in pointers:
                if retention == "persistent" and not self._resolves(kind, target):
                    self.findings.append(("V-10", line_no))

    def _validate_gaps(self):
        for index, row in enumerate(self.rows):
            values = row["values"]
            if values["event"] != "observer-start" or index == 0:
                continue
            previous = self.rows[index - 1]["values"]
            if previous["event"] == "observer-gap":
                continue
            start = values["event_at"]
            if start != self.fmt["placeholder"] and ISO_FIELD_RE.match(start) \
                    and ISO_FIELD_RE.match(previous["observed_at"]) \
                    and previous["observed_at"] < start:
                self.findings.append(("V-17", row["line_no"]))

    def _resolves(self, kind, target):
        key = (kind, target)
        if key in self._resolved:
            return self._resolved[key]
        if kind == "commit":
            result = subprocess.run(
                ["git", "-C", str(self.repo), "cat-file", "-e", target + "^{commit}"],
                capture_output=True, text=True, timeout=60,
            )
            ok = result.returncode == 0
        else:
            ok = (self.repo / target).exists()
        self._resolved[key] = ok
        return ok


# --------------------------------------------------------------------------- #
# append projections — every row is a deterministic projection of a carrier fact
# --------------------------------------------------------------------------- #
def _row(event, evidence, event_at="-", stage="-", command="-", artifact="-", exit_code="-"):
    return {"event": event, "event_at": event_at, "stage": stage, "command": command,
            "artifact": artifact, "exit": exit_code, "evidence": evidence}


def _identity(values):
    return (values["event"], values["stage"], values["artifact"], values["evidence"],
            values["event_at"])


def _read_carrier(path):
    """``(text, error)`` — an unreadable existing carrier is reported, never silently skipped."""
    path = Path(path)
    if not path.exists():
        return None, None
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as error:
        return None, str(error.strerror or error)


def _error_row(path, repo):
    target = rel(path, repo)
    return _row("observer-error", pointer("runtime", "artifact", target), artifact=target)


def _find_triplet(repo, label):
    root = Path(repo) / ".specify" / "agents" / "execution" / "logs"
    if not root.is_dir():
        return None
    matches = sorted(root.rglob(label + ".status"))
    return rel(matches[0], repo) if matches else None


def _git_history(repo, since_iso):
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "--reverse", "--since=" + since_iso,
         "--format=__JOURNAL_COMMIT__%H%x1f%ct", "--name-only"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        return None
    commits, current = [], None
    for line in result.stdout.splitlines():
        if line.startswith("__JOURNAL_COMMIT__"):
            payload = line[len("__JOURNAL_COMMIT__"):]
            commit_hash, _, epoch = payload.partition("\x1f")
            current = {"hash": commit_hash, "epoch": int(epoch) if epoch.isdigit() else None,
                       "paths": []}
            commits.append(current)
            continue
        if current is not None and line.strip():
            current["paths"].append(line.strip())
    return commits


def _gap_candidates(journal, record, args, repo, fmt):
    """C-08 / journal-format C-10: name an uncovered window instead of inferring events."""
    started_at = record["fields"].get("started_at") or ""
    if not journal.rows or not ISO_FIELD_RE.match(started_at):
        return []
    last_observed = journal.rows[-1]["values"]["observed_at"]
    if last_observed >= started_at:
        return []
    evidence = pointer("persistent", "spine", rel(args.spine, repo), record["anchor"])
    previous_evidence = journal.rows[-1]["values"]["evidence"]
    if previous_evidence and previous_evidence != fmt["placeholder"]:
        evidence += "; " + previous_evidence
    return [_row("observer-gap", evidence, event_at=last_observed)]


def _project_candidates(spine_state, record, args, repo, spec_dir, state_dir, fmt, sentinel_template):
    candidates = []
    placeholder = fmt["placeholder"]
    started_at = record["fields"].get("started_at") or ""

    # line-start: first append only, from the spine U0 block.
    if spine_state["has_u0"]:
        candidates.append(_row("line-start", pointer("persistent", "spine", rel(args.spine, repo))))

    # observer-start: one per execution, keyed by the record section and the triplet path.
    evidence = pointer("persistent", "spine", rel(args.spine, repo), record["anchor"])
    triplet = _find_triplet(repo, args.execution_label)
    if triplet:
        evidence += "; " + pointer("runtime", "triplet", triplet)
    candidates.append(_row("observer-start", evidence,
                           event_at=started_at if ISO_FIELD_RE.match(started_at) else placeholder))

    # Stall (state spine 卡死状态 grammar).
    if spine_state["stalled"]:
        candidates.append(_row("stall", pointer("persistent", "spine", rel(args.spine, repo))))

    # Retry (the pid envelope keeps one line per attempt; the extra lines are the events).
    retries = []
    for stage in fmt["stages"]:
        pid_text, pid_error = _read_carrier(state_dir / ("pid-%s-%s" % (args.line_id, stage)))
        if pid_error:
            candidates.append(_error_row(state_dir / ("pid-%s-%s" % (args.line_id, stage)), repo))
            continue
        if not pid_text:
            continue
        pid_lines = [line for line in pid_text.splitlines() if "event=pid" in line]
        for extra in pid_lines[1:]:
            at = epoch_to_iso(_field(extra, "at")) or placeholder
            retries.append(_row("retry", pointer("runtime", "pid",
                                                 rel(state_dir / ("pid-%s-%s" % (args.line_id, stage)), repo)),
                                event_at=at, stage=stage))

    # Stage rows, in declared order: start, end, verdict, anomaly, dispatch, retry.
    for stage in fmt["stages"]:
        pid_path = state_dir / ("pid-%s-%s" % (args.line_id, stage))
        status_path = state_dir / ("status-%s-%s" % (args.line_id, stage))
        log_path = state_dir / ("log-%s-%s.log" % (args.line_id, stage))
        meta_path = state_dir / ("prompt-%s-%s.md.meta.json" % (args.line_id, stage))

        pid_text, pid_error = _read_carrier(pid_path)
        if pid_error:
            candidates.append(_error_row(pid_path, repo))
        elif pid_text:
            first = next((line for line in pid_text.splitlines() if "event=pid" in line), "")
            candidates.append(_row("stage-start", pointer("runtime", "pid", rel(pid_path, repo)),
                                   event_at=epoch_to_iso(_field(first, "at")) or placeholder, stage=stage))

        status_text, status_error = _read_carrier(status_path)
        if status_error:
            candidates.append(_error_row(status_path, repo))
        status = {}
        if status_text:
            status = {"exit": _field(status_text, "exit"), "at": _field(status_text, "at"),
                      "sentinel": _field(status_text, "sentinel")}
            candidates.append(_row("stage-end", pointer("runtime", "status", rel(status_path, repo)),
                                   event_at=epoch_to_iso(status["at"]) or placeholder, stage=stage,
                                   exit_code=status["exit"] or placeholder))

        log_text, log_error = _read_carrier(log_path)
        if log_error:
            candidates.append(_error_row(log_path, repo))
        last_line = _last_nonempty(log_text or "")
        if status and status.get("sentinel") == "1" and status.get("exit") == "0" \
                and last_line == sentinel_for(stage, sentinel_template):
            evidence = pointer("runtime", "status", rel(status_path, repo))
            if log_text is not None:
                evidence += "; " + pointer("runtime", "log", rel(log_path, repo))
            candidates.append(_row("stage-verdict", evidence,
                                   event_at=epoch_to_iso(status.get("at")) or placeholder,
                                   stage=stage, exit_code=status.get("exit") or placeholder))

        if _last_anomaly(log_text or "") is not None:
            evidence = pointer("runtime", "log", rel(log_path, repo))
            if status_text:
                evidence += "; " + pointer("runtime", "status", rel(status_path, repo))
            candidates.append(_row("anomaly", evidence,
                                   event_at=epoch_to_iso(status.get("at")) or placeholder,
                                   stage=stage, exit_code=status.get("exit") or placeholder))

        meta_text, meta_error = _read_carrier(meta_path)
        if meta_error:
            candidates.append(_error_row(meta_path, repo))
        elif meta_text is not None:
            meta_at = placeholder
            try:
                payload = json.loads(meta_text)
                for key in ("at", "created_at", "timestamp"):
                    if isinstance(payload.get(key), (int, float)):
                        meta_at = epoch_to_iso(payload[key]) or placeholder
                        break
                    if isinstance(payload.get(key), str) and ISO_FIELD_RE.match(payload[key]):
                        meta_at = payload[key]
                        break
            except (ValueError, AttributeError):
                candidates.append(_error_row(meta_path, repo))
                continue
            candidates.append(_row("dispatch", pointer("runtime", "meta", rel(meta_path, repo)),
                                   event_at=meta_at, stage=stage))

    candidates.extend(retries)

    # Checkpoints (persistent).
    checkpoint_dir = spec_dir / "checkpoints"
    if checkpoint_dir.is_dir():
        for path in sorted(checkpoint_dir.glob("*.md")):
            stem = path.stem
            stage = stem.split("-", 1)[1] if "-" in stem else ""
            candidates.append(_row("checkpoint", pointer("persistent", "checkpoint", rel(path, repo)),
                                   stage=stage if stage in fmt["stages"] else placeholder,
                                   artifact=rel(path, repo)))

    # Git history over the observation window (commit + artifact-write).
    window_start = record["fields"].get("started_at") or ""
    window_epoch = iso_to_epoch(window_start) if ISO_FIELD_RE.match(window_start) else 0
    since_iso = window_start if ISO_FIELD_RE.match(window_start) else "1970-01-01T00:00:00Z"
    spec_rel = rel(spec_dir, repo) + "/"
    history = _git_history(repo, since_iso)
    if history is None:
        candidates.append(_error_row(Path(repo) / ".git", repo))
        history = []
    for commit in history:
        if commit["epoch"] is not None and commit["epoch"] < window_epoch:
            continue
        commit_iso = epoch_to_iso(commit["epoch"]) or placeholder
        candidates.append(_row("commit", pointer("persistent", "commit", commit["hash"]),
                               event_at=commit_iso))
        for path in commit["paths"]:
            if not path.startswith(spec_rel):
                continue
            tail = path[len(spec_rel):]
            if tail == fmt["filename"] or tail.startswith("checkpoints/"):
                continue
            candidates.append(_row("artifact-write",
                                   pointer("persistent", "commit", commit["hash"]),
                                   event_at=commit_iso, artifact=path))

    return candidates


def _terminal_rows(args, record, repo):
    if not (args.settle or args.final):
        return []
    evidence = pointer("persistent", "spine", rel(args.spine, repo), record["anchor"])
    triplet = _find_triplet(repo, args.execution_label)
    if triplet:
        evidence += "; " + pointer("runtime", "triplet", triplet)
    rows = []
    if args.final:
        rows.append(_row("line-terminal", evidence))
    rows.append(_row("observer-settle", evidence))
    return rows


# --------------------------------------------------------------------------- #
# actions
# --------------------------------------------------------------------------- #
def action_append(args, repo):
    fmt = load_format(repo)
    fmt["stages"] = load_stages(repo)
    sentinel_template = load_sentinel_template(repo)
    spine_state = read_spine(args.spine)
    record = check_identity(spine_state, args.line_id, args.run_id, args.execution_label)

    spec_dir = Path(args.spec_dir).resolve()
    if not spec_dir.is_dir():
        raise EngineError("input-error: spec-dir absent: %s" % spec_dir)
    journal_path = spec_dir / fmt["filename"]

    try:
        handle = open(journal_path, "a+", encoding="utf-8")
    except OSError as error:
        raise EngineError("input-error: journal unreadable: %s" % (error.strerror or error))
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print("concurrent-writer-refused")
            return 3
        handle.seek(0)
        existing = handle.read()
        journal = Journal(journal_path, repo, fmt)
        if existing.strip() and not journal.table_found:
            raise EngineError("input-error: journal is not a readable journal: %s"
                              % rel(journal_path, repo))

        candidates = []
        candidates.extend(_gap_candidates(journal, record, args, repo, fmt))
        candidates.extend(_project_candidates(spine_state, record, args, repo, spec_dir,
                                             Path(args.state_dir).resolve(), fmt, sentinel_template))
        candidates.extend(_terminal_rows(args, record, repo))

        existing_identities = {_identity(row["values"]) for row in journal.rows}
        new_rows = [row for row in candidates if _identity(row) not in existing_identities]

        now = utc_now()
        lines = []
        if not existing.strip():
            header_values = {
                "line_id": args.line_id,
                "run_id": args.run_id,
                "spec": record["fields"].get("spec") or spec_dir.name,
                "observer_instance": record["fields"].get("instance")
                or ("sdd-observer-" + args.line_id),
                "created_at": now,
            }
            lines.append(fmt["title_template"].replace("<spec-key>", header_values["spec"]))
            lines.append("")
            for key in fmt["header_keys"]:
                lines.append("- %s: %s" % (key, header_values[key]))
            lines.append("")
            lines.append("| " + " | ".join(fmt["columns"]) + " |")
            lines.append("|" + "|".join("---" for _ in fmt["columns"]) + "|")
        seq = len(journal.rows) + 1
        for row in new_rows:
            values = {
                "seq": seq,
                "observed_at": now,
                "event_at": row["event_at"],
                "stage": row["stage"],
                "event": row["event"],
                "command": row["command"],
                "artifact": row["artifact"],
                "exit": row["exit"],
                "evidence": row["evidence"],
            }
            lines.append(render_cells([values[column] for column in fmt["columns"]], fmt))
            seq += 1
        if lines:
            handle.write("\n".join(lines) + "\n")
            handle.flush()
        print(json.dumps({"action": "append", "journal": rel(journal_path, repo),
                          "appended": len(new_rows), "seq_last": seq - 1}))
        return 0
    finally:
        handle.close()


def action_check(args, repo):
    fmt = load_format(repo)
    fmt["stages"] = load_stages(repo)
    journal_path = Path(args.spec_dir).resolve() / fmt["filename"]
    if not journal_path.is_file():
        raise EngineError("input-error: journal absent: %s" % rel(journal_path, repo))
    journal = Journal(journal_path, repo, fmt)
    findings = sorted(set(journal.findings), key=lambda item: (item[1], item[0]))
    name = rel(journal_path, repo)
    for code, line_no in findings:
        print("%s: %s:%d" % (code, name, line_no))
    if findings:
        return 1
    print("%s: 0 findings" % name)
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser():
    parser = argparse.ArgumentParser(
        description="Project carrier facts into the sdd-observer journal, or validate one.")
    _sig_configure(
        parser,
        effects="append writes only the journal under --spec-dir; check writes nothing",
        codes="append: 0 appended or nothing new, 2 input or identity error, 3 concurrent writer "
              "refused; check: 0 no finding, 1 finding(s), 2 input error",
    )
    parser.add_argument("--action", choices=("append", "check"), required=True,
                        help="`append` projects carrier facts; `check` validates a journal")
    parser.add_argument("--spec-dir", default=None, help="the line's spec directory")
    parser.add_argument("--spine", default=None, help="the line's state spine (append)")
    parser.add_argument("--state-dir", default=None, help="the runner state directory (append)")
    parser.add_argument("--repo", default=None, help="repository root for path pointers")
    parser.add_argument("--line-id", default=None, help="the line's id (append)")
    parser.add_argument("--run-id", default=None, help="the line's run id (append)")
    parser.add_argument("--execution-label", default=None,
                        help="this execution's three-segment dispatch label (append)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--settle", action="store_true",
                       help="close this execution with one observer-settle row")
    group.add_argument("--final", action="store_true",
                       help="close the line: line-terminal and observer-settle rows")
    return parser


def main(argv=None):
    _sig_guard(argv, declared=[
        "--action", "--spec-dir", "--spine", "--state-dir", "--repo", "--line-id", "--run-id",
        "--execution-label", "--settle", "--final",
    ])
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.repo:
        repo = Path(args.repo).resolve()
    elif declaration_reader is not None:
        # The mirror form `.specify/scripts/python/` resolves to the project root, not `.specify`.
        repo = Path(declaration_reader.find_repo(Path(__file__))).resolve()
    else:  # pragma: no cover - the degraded copy still answers help/version
        repo = Path(__file__).resolve().parents[2]
    try:
        if args.action == "append":
            missing = [name for name in ("spec_dir", "spine", "state_dir", "line_id", "run_id",
                                         "execution_label") if not getattr(args, name)]
            if missing:
                raise EngineError("input-error: append needs --%s"
                                  % ", --".join(name.replace("_", "-") for name in missing))
            return action_append(args, repo)
        if args.spec_dir is None:
            raise EngineError("input-error: check needs --spec-dir")
        return action_check(args, repo)
    except EngineError as error:
        print("journal-utils: %s" % error.label, file=sys.stderr)
        return error.code
    except Exception as error:  # the closed exit set has no crash code: report an input error
        print("journal-utils: input-error: unexpected failure: %s" % error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
