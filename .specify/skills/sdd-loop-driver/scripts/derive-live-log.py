#!/usr/bin/env python3
"""Derive an incrementally growing live log from a raw stream-json NDJSON feed.

Each meaningful non-terminal event yields one prefixed progress line carrying
its raw event sequence and receive timestamp. The terminal ``result`` text is
appended verbatim at EOF, so the last non-empty line equals the stage sentinel
only when the CLI emitted a terminal result. Malformed lines are tolerated and
never fabricate progress or completion.

``--finish`` reads the raw stream once and prints only the terminal result text
(exit 1 when no result exists), for runner recovery after a derivation failure.

Python >= 3.8, standard library only.
"""

import argparse
import json
import sys
import time


def one_line(text):
    return " ".join(str(text).split())


def progress_text(event):
    event_type = event.get("type")
    if event_type == "system":
        return "system:%s" % (event.get("subtype") or "event")
    if event_type == "assistant":
        message = event.get("message")
        texts = []
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        texts.append(item.get("text", ""))
            elif isinstance(content, str):
                texts.append(content)
            if not texts:
                texts.append(json.dumps(message, ensure_ascii=False))
        return "assistant: %s" % one_line(" ".join(str(item) for item in texts))
    if event_type in ("tool_use", "tool_result"):
        name = event.get("name") or event.get("tool_name") or ""
        return "%s: %s" % (event_type, one_line(name))
    if event_type:
        return one_line(event_type)
    return ""


def result_text_of(event):
    text = event.get("result")
    return text if isinstance(text, str) else None


def read_lines(stream):
    while True:
        line = stream.readline()
        if line == "":
            return
        yield line


def derive(stream, out):
    sequence = 0
    result = None
    for raw in read_lines(stream):
        raw = raw.rstrip("\n")
        if not raw.strip():
            continue
        sequence += 1
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "result":
            text = result_text_of(event)
            if text is not None:
                result = text
            continue
        line = progress_text(event)
        if not line:
            continue
        out.write("[evt=%d at=%.3f] %s\n" % (sequence, time.time(), line))
        out.flush()
    if result is not None:
        out.write(result)
        if not result.endswith("\n"):
            out.write("\n")
        out.flush()


def finish(stream, out):
    result = None
    for raw in read_lines(stream):
        raw = raw.rstrip("\n")
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "result":
            text = result_text_of(event)
            if text is not None:
                result = text
    if result is None:
        return 1
    out.write(result)
    if not result.endswith("\n"):
        out.write("\n")
    out.flush()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Derive a compact live log from a raw stream-json NDJSON stream.")
    parser.add_argument("--events", help="raw NDJSON file (default: stdin)")
    parser.add_argument("--out", help="live log output file (default: stdout)")
    parser.add_argument("--finish", action="store_true",
                        help="print only the terminal result text from the raw stream")
    args = parser.parse_args(argv)

    close_in = close_out = False
    source = sys.stdin
    sink = sys.stdout
    try:
        if args.events:
            source = open(args.events, "r", encoding="utf-8", errors="replace")
            close_in = True
        if args.out:
            sink = open(args.out, "w", encoding="utf-8")
            close_out = True
        if args.finish:
            return finish(source, sink)
        derive(source, sink)
        return 0
    except OSError as error:
        print("derive-live-log: %s" % error, file=sys.stderr)
        return 2
    finally:
        if close_in:
            source.close()
        if close_out:
            sink.close()


if __name__ == "__main__":
    sys.exit(main())
