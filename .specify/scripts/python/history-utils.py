#!/usr/bin/env python3
"""Utilities for /speckit.history — locate, extract, and track AI-tool
conversation history for the current tool and project.

Design notes
------------
* Only *locating* and *extracting* the raw session text is deterministic, so it
  lives here. Summarisation / theme aggregation is the AI's job (the command
  prompt drives it).
* Multi-tool support is pluggable via ``STORE_RESOLVERS``. Claude Code is fully
  supported today (JSONL session store). Other tools resolve to
  ``supported: false`` with an honest hint about where their history lives, so
  the command can report clearly instead of guessing.
* All actions print a single JSON object to stdout.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional


# --------------------------------------------------------------------------- #
# Tool → session-store resolution
# --------------------------------------------------------------------------- #

def _encode_claude_project_dir(project_path: Path) -> str:
    """Claude Code encodes a project's absolute path into its history dir name
    by replacing ``/``, ``.`` and ``_`` with ``-``.

    e.g. /storage/project/cloud-native-ai/spec-kit
         -> -storage-project-cloud-native-ai-spec-kit
    """
    return re.sub(r"[/._]", "-", str(project_path))


def resolve_claude(project_path: Path) -> Dict[str, object]:
    """Locate the Claude Code session store for ``project_path``."""
    base = Path.home() / ".claude" / "projects"
    encoded = _encode_claude_project_dir(project_path.resolve())
    store = base / encoded

    if not store.is_dir() and base.is_dir():
        # Fuzzy fallback: match by encoded basename suffix (handles edge cases
        # in path encoding). Never match sub-scope variants (e.g. "...--specify").
        candidates = [
            d for d in base.iterdir()
            if d.is_dir() and d.name == encoded
        ]
        if candidates:
            store = candidates[0]

    supported = store.is_dir()
    session_count = len(list(store.glob("*.jsonl"))) if supported else 0
    return {
        "supported": supported,
        "session_store": str(store),
        "session_count": session_count,
        "note": (
            "Claude Code JSONL session store."
            if supported
            else f"Expected Claude history at {store}, but it does not exist."
        ),
    }


# Tools without a resolver yet: honest hint about where history *might* live,
# marked unsupported so the command reports instead of guessing/parsing wrongly.
UNSUPPORTED_TOOL_HINTS: Dict[str, str] = {
    "codex": "~/.codex/sessions (rollout logs) — format not yet adapted.",
    "copilot": "VS Code Copilot Chat history is stored in the editor workspace state (not a plain-text local store) — not yet adapted.",
    "qoder": "~/.qoder or the Qoder app data dir — format not yet adapted.",
    "opencode": "opencode local session store — format not yet adapted.",
    "qwen": "~/.qwen session store — format not yet adapted.",
    "hermes": "~/.hermes session store — format not yet adapted.",
    "iflow": "~/.iflow session store — format not yet adapted.",
}

STORE_RESOLVERS: Dict[str, Callable[[Path], Dict[str, object]]] = {
    "claude": resolve_claude,
}

# Directory signals used to guess the current tool when --tool is omitted.
_TOOL_DIR_SIGNALS = {
    "claude": ".claude",
    "copilot": ".github",
    "qoder": ".qoder",
    "opencode": ".opencode",
    "qwen": ".qwen",
    "codex": ".codex",
    "hermes": ".hermes",
    "iflow": ".iflow",
}


# --------------------------------------------------------------------------- #
# Session text extraction (strip tool-call / injected noise)
# --------------------------------------------------------------------------- #

def _text_of(content) -> str:
    """Return only human/assistant *text* from a message content field,
    dropping tool_use / tool_result / thinking blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out: List[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                out.append(block.get("text", ""))
        return "\n".join(out)
    return ""


def _scrub(text: str) -> str:
    """Remove harness-injected blocks that carry no conversational value."""
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S)
    text = re.sub(r"<local-command-stdout>.*?</local-command-stdout>", "", text, flags=re.S)
    text = re.sub(r"<local-command-caveat>.*?</local-command-caveat>", "", text, flags=re.S)
    return text.strip()


def _clean_oneline(text: str, limit: int = 120) -> str:
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _extract_first_ask(text: str) -> str:
    """Best-effort first real user ask (handles /command args)."""
    m = re.search(r"<command-args>(.*?)</command-args>", text, re.S)
    if m and m.group(1).strip():
        return "[cmd] " + _clean_oneline(m.group(1), 110)
    return _clean_oneline(text, 120)


def parse_session(path: Path) -> Dict[str, object]:
    """Parse one JSONL session into title + cleaned role-tagged transcript."""
    title = ""
    first_user = ""
    parts: List[str] = []
    n_user = n_asst = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = d.get("type")
        if t == "ai-title":
            title = d.get("aiTitle", "") or title
        elif t in ("user", "assistant"):
            msg = d.get("message", {}) or {}
            role = msg.get("role", t)
            txt = _scrub(_text_of(msg.get("content")))
            if not txt or txt.startswith("Caveat:"):
                continue
            if t == "user":
                n_user += 1
                if not first_user and "<command-name>" not in txt and "<local-command-stdout>" not in txt:
                    first_user = _extract_first_ask(txt)
                elif not first_user and "<command-args>" in txt:
                    first_user = _extract_first_ask(txt)
            else:
                n_asst += 1
            parts.append(f"### {role.upper()}\n{txt}\n")
    body = "\n".join(parts)
    return {
        "title": title,
        "first_user": first_user,
        "n_user": n_user,
        "n_asst": n_asst,
        "chars": len(body),
        "body": body,
    }


# --------------------------------------------------------------------------- #
# Manifest (incremental tracking)
# --------------------------------------------------------------------------- #

def _manifest_path(output_dir: Path) -> Path:
    return output_dir / ".manifest.json"


def read_manifest(output_dir: Path) -> Dict[str, object]:
    p = _manifest_path(output_dir)
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"version": 1, "tool": None, "sessions": {}}


def write_manifest(output_dir: Path, manifest: Dict[str, object]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _manifest_path(output_dir).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _now_iso() -> str:
    return datetime.datetime.now().replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #

def _project_root(arg: Optional[str]) -> Path:
    """Locate the project workspace root that owns the ``.specify/`` store.

    Priority: explicit CLI argument > script self-location (an engine copy
    installed under ``*/.specify/scripts/`` anchors its parent project) >
    nearest CWD ancestor containing ``.specify/`` > CWD itself. Self-location
    must outrank the walk-up: when the agent's CWD sits inside a skill
    directory that contains a stray nested ``.specify/`` (created by an
    earlier bug), the walk-up would capture that nested tree and split the
    store. Falling back to bare CWD is only a last resort outside any project.
    """
    if arg:
        return Path(arg).resolve()
    script = Path(__file__).resolve()
    parts = script.parts
    for i, part in enumerate(parts):
        if part == ".specify" and i + 1 < len(parts) and parts[i + 1] == "scripts":
            return Path(*parts[:i])
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".specify").is_dir():
            return candidate
    return cwd


def _guess_tool(project_path: Path) -> Optional[str]:
    present = [k for k, d in _TOOL_DIR_SIGNALS.items() if (project_path / d).is_dir()]
    # Prefer a resolvable tool if exactly one is; else if a single signal, use it.
    resolvable = [k for k in present if k in STORE_RESOLVERS]
    if len(resolvable) == 1:
        return resolvable[0]
    if len(present) == 1:
        return present[0]
    return None


def action_locate(args) -> Dict[str, object]:
    project = _project_root(args.project)
    output_dir = project / ".specify" / "history"
    tool = args.tool or _guess_tool(project)

    result: Dict[str, object] = {
        "action": "locate",
        "tool": tool,
        "project_path": str(project),
        "project_name": project.name,
        "output_dir": str(output_dir),
        "manifest_path": str(_manifest_path(output_dir)),
        "supported": False,
        "session_store": None,
        "session_count": 0,
        "supported_tools": sorted(STORE_RESOLVERS.keys()),
    }

    if tool is None:
        result["note"] = (
            "Could not determine the current tool. Pass --tool <key> "
            "(one of: %s, or an unsupported tool to see its status)."
            % ", ".join(sorted(_TOOL_DIR_SIGNALS.keys()))
        )
        return result

    resolver = STORE_RESOLVERS.get(tool)
    if resolver is None:
        result["note"] = UNSUPPORTED_TOOL_HINTS.get(
            tool, f"Tool '{tool}' is not recognised."
        )
        result["hint"] = "History extraction for this tool is not implemented yet."
        return result

    result.update(resolver(project))
    return result


def action_extract(args) -> Dict[str, object]:
    project = _project_root(args.project)
    output_dir = project / ".specify" / "history"
    work_dir = output_dir / ".work"
    tool = args.tool or _guess_tool(project)

    resolver = STORE_RESOLVERS.get(tool or "")
    if resolver is None:
        return {
            "action": "extract",
            "tool": tool,
            "supported": False,
            "note": UNSUPPORTED_TOOL_HINTS.get(tool or "", "Unsupported or unknown tool."),
            "sessions": [],
        }

    loc = resolver(project)
    if not loc.get("supported"):
        return {"action": "extract", "tool": tool, "supported": False,
                "note": loc.get("note"), "sessions": []}

    manifest = read_manifest(output_dir)
    processed = set((manifest.get("sessions") or {}).keys())

    store = Path(str(loc["session_store"]))
    work_dir.mkdir(parents=True, exist_ok=True)

    inventory: List[Dict[str, object]] = []
    for f in sorted(store.glob("*.jsonl")):
        sid = f.stem
        parsed = parse_session(f)
        is_processed = sid in processed
        entry = {
            "sid": sid,
            "short": sid[:8],
            "title": parsed["title"],
            "first_user": parsed["first_user"],
            "chars": parsed["chars"],
            "n_user": parsed["n_user"],
            "n_asst": parsed["n_asst"],
            "mtime": datetime.datetime.fromtimestamp(f.stat().st_mtime)
            .replace(microsecond=0).isoformat(),
            "processed": is_processed,
            "work_file": None,
        }
        # Write cleaned transcript for sessions the AI will summarise.
        if args.full or not is_processed:
            wf = work_dir / f"{sid}.txt"
            header = f"SESSION {sid}  TITLE: {parsed['title']}\n\n"
            wf.write_text(header + str(parsed["body"]), encoding="utf-8")
            entry["work_file"] = str(wf)
        inventory.append(entry)

    inventory.sort(key=lambda e: e["mtime"])
    total_chars = sum(e["chars"] for e in inventory)
    pending = [e for e in inventory if e["work_file"]]
    return {
        "action": "extract",
        "tool": tool,
        "supported": True,
        "session_store": str(store),
        "output_dir": str(output_dir),
        "work_dir": str(work_dir),
        "total_sessions": len(inventory),
        "pending_sessions": len(pending),
        "total_chars": total_chars,
        "full": bool(args.full),
        "sessions": inventory,
    }


def action_manifest_read(args) -> Dict[str, object]:
    output_dir = _project_root(args.project) / ".specify" / "history"
    manifest = read_manifest(output_dir)
    return {"action": "manifest-read", **manifest}


def action_manifest_update(args) -> Dict[str, object]:
    output_dir = _project_root(args.project) / ".specify" / "history"
    manifest = read_manifest(output_dir)
    if manifest.get("tool") is None:
        manifest["tool"] = args.tool
    sessions = manifest.setdefault("sessions", {})

    sids: List[str] = []
    if args.sids:
        sids.extend([s for s in re.split(r"[,\s]+", args.sids) if s])
    if args.sids_file:
        sids.extend(
            [s.strip() for s in Path(args.sids_file).read_text().splitlines() if s.strip()]
        )

    now = _now_iso()
    for sid in sids:
        sessions[sid] = {"processed_at": now}
    manifest["last_run"] = now
    write_manifest(output_dir, manifest)
    return {
        "action": "manifest-update",
        "recorded": len(sids),
        "total_processed": len(sessions),
        "manifest_path": str(_manifest_path(output_dir)),
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="History utilities for /speckit.history")
    p.add_argument(
        "--action",
        choices=["locate", "extract", "manifest-read", "manifest-update"],
        default="locate",
    )
    p.add_argument("--tool", default=None, help="Tool key (claude, codex, ...). Auto-detected if omitted.")
    p.add_argument("--project", default=None, help="Project root (defaults to CWD).")
    p.add_argument("--full", action="store_true", help="Extract all sessions, including already-processed.")
    p.add_argument("--sids", default=None, help="Comma/space-separated session ids (manifest-update).")
    p.add_argument("--sids-file", default=None, help="File of session ids, one per line (manifest-update).")
    p.add_argument("--json", action="store_true", help="Emit JSON (default output is always JSON).")
    return p


_DISPATCH = {
    "locate": action_locate,
    "extract": action_extract,
    "manifest-read": action_manifest_read,
    "manifest-update": action_manifest_update,
}


def main() -> None:
    args = _build_parser().parse_args()
    result = _DISPATCH[args.action](args)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
