#!/usr/bin/env python3
"""Convert agent-CLI stream-json events into compact human-readable progress lines,
so a dispatched external subagent's work is visible while it runs.

Works with any CLI emitting the shared stream-json NDJSON event shape
(``qodercli --output-format stream-json``, ``claude --output-format stream-json``):
events of type ``assistant`` (message.content blocks), ``result``, and ``system``.

Usage:  <cli> -p "<prompt>" --output-format stream-json ... | stream-filter.py [label]
Reads NDJSON on stdin, writes one short line per meaningful event on stdout (line-buffered).
Line width can be tuned via STREAM_FILTER_WIDTH (default: 140).

Part of the External Dispatch Visibility Contract reference implementation;
see shared/definitions/subagent-definitions.md. Normally driven by dispatch.sh.
"""
import json
import os
import sys

label = sys.argv[1] if len(sys.argv) > 1 else "agent"
max_width = int(os.environ.get("STREAM_FILTER_WIDTH", "140"))


def clip(text, n=max_width):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def tool_brief(name, params):
    if not isinstance(params, dict):
        return name
    for key in ("file_path", "path", "pattern", "command", "notebook_path", "url", "prompt"):
        if key in params:
            return f"{name}({clip(params[key], 90)})"
    return name


for raw in sys.stdin:
    raw = raw.strip()
    if not raw:
        continue
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        continue

    etype = event.get("type")
    if etype == "assistant":
        for block in event.get("message", {}).get("content", []) or []:
            btype = block.get("type")
            if btype == "text" and block.get("text", "").strip():
                print(f"[{label}] {clip(block['text'])}", flush=True)
            elif btype == "tool_use":
                print(
                    f"[{label}] -> {tool_brief(block.get('name', '?'), block.get('input'))}",
                    flush=True,
                )
    elif etype == "result":
        print(
            f"[{label}] == DONE subtype={event.get('subtype')} "
            f"turns={event.get('num_turns')} cost_usd={event.get('total_cost_usd')} "
            f"duration_ms={event.get('duration_ms')}",
            flush=True,
        )
    elif etype == "system" and event.get("subtype") == "init":
        print(f"[{label}] == START session={clip(event.get('session_id'), 40)}", flush=True)
