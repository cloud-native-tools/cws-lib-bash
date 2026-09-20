#!/usr/bin/env python3
"""redline-check.py — attribute-triggered red-line conformance probe for a target Skill.

Implements the deterministic half of the red-line framework owned by
``../references/red-lines.md``:

    1. attribute collection   — classify the target Skill from its own text/scripts
    2. red-line selection      — map each collected attribute to the red lines it fires
    3. trigger judgment        — scan for violation vs compliance signals, emit a verdict

Step 4 (remediation) is judgment + MUST-DO and stays with the caller; this script only
reports which red lines are triggered and what their mandatory remediation is.

Design boundaries (see red-lines.md § "What this probe decides vs what stays judgment"):
  * Deterministic here: which attributes are present, which red lines therefore apply,
    and which static signals appear where.
  * Judgment (caller): whether a flagged signal is a *sanctioned, announced exception*
    (e.g. a human-in-the-loop login window) or a real violation that must be fixed.
    A "review" verdict is therefore "remediation required unless proven sanctioned",
    never an auto-conviction.

Negation guard (avoids flagging the prohibition text itself): a violation token on a line
that also carries a prohibition/negation marker (never / do not / MUST NOT / 禁止 / 绝不 /
不得 / 严禁 / avoid ...) is classified as a *prohibition statement* (compliance evidence),
NOT a violation. This is why a Skill that correctly documents "never call bringToFront()"
does not fail.

Policy self-exclusion: files whose basename is ``redline-check.py`` or ``red-lines.md`` are
skipped — the framework's own checker and policy doc talk *about* automation red lines and
are not evidence that the host Skill performs automation.

Usage
-----
    redline-check.py <path/to/SKILL.md> [--scan-all] [--file-only] [--json] [--quiet]

    <SKILL.md>   target Skill. Default scope is the Skill's own behavior contract:
                 SKILL.md + scripts/ (+ root-level *.sh/*.py). Encyclopedic L2
                 references (API listings, "rejected mechanism" tables) are excluded
                 from the gate because they *document* capabilities rather than
                 *perform* them, and grepping them produces noise.
    --scan-all   also scan references/ (deeper audit; knowingly noisier — every
                 documented mention of a focus-stealing API becomes a judgment item)
    --file-only  scan only the given SKILL.md
    --json       machine-readable verdict
    --quiet      exit code only

Verdict model (exit code driven by MITIGATION PRESENCE, not raw signal count):
    not-applicable  attribute absent — the red line does not fire
    gap             attribute present but the Skill carries ZERO focus-safe vocabulary
                    -> it drives automation with no mitigation: MANDATORY remediation
    review          attribute present, mitigation present, but un-negated HARD focus-steal
                    signals remain -> verify each is a sanctioned/announced exception, else fix
    compliant       attribute present, mitigation present, no un-negated hard signal

Exit codes
----------
    0   PASS      — every red line is not-applicable or compliant
    1   TRIGGERED — >=1 red line is gap/review; remediation is MANDATORY (or prove sanctioned)
    2   usage error
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Attribute model — deterministic signals that a Skill *performs* a surface.
# Kept narrow on purpose: mentioning "automation" in the abstract must NOT fire.
# ---------------------------------------------------------------------------
ATTRIBUTES = {
    "automation": {
        "desc": "drives a GUI/browser/desktop automation surface that maps real windows",
        "signals": [
            r"playwright", r"puppeteer", r"selenium", r"browser-use",
            r"connect[_ ]?over[_ ]?cdp", r"connectOverCDP", r"remote-debugging-port",
            r"chromium\.launch", r"\bnewPage\b", r"bringToFront", r"bring_to_front",
            r"chrome_open", r"open\s+-[a-zA-Z]*n?a?\b.*Chrome", r"Google Chrome\.app",
            r"osascript", r"AppleScript", r"\bPeekaboo\b", r"\bCUA\b", r"pyautogui",
            r"xdotool", r"wmctrl", r"--start-maximized", r"--start-fullscreen", r"--kiosk",
            r"headless\s*[:=]\s*(true|false|True|False)",
        ],
    },
    # Collected and reported, but NO red line is bound to it yet — adding one requires
    # passing the admission criteria in red-lines.md. Demonstrates that "attribute present"
    # is decoupled from "red line fires".
    "sensitive-info": {
        "desc": "handles credentials / tokens / cookies / PII / secrets",
        "signals": [
            r"\bcredential", r"\bsecret", r"\btoken\b", r"\bcookie", r"password",
            r"api[_-]?key", r"凭据", r"密钥", r"敏感信息", r"登录态",
        ],
    },
}

# Prohibition / negation markers: a violation token on a line carrying one of these is a
# prohibition statement (compliance evidence), not a violation.
NEGATION = re.compile(
    r"\b(never|no[t]?\b|don'?t|do not|must not|mustn'?t|forbid(?:den|s)?|avoid|prohibit\w*"
    r"|refrain|without)\b|禁止|绝不|绝不可|不得|不应|不用|勿|严禁|避免|红线|不抢|不置前|不激活",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Red-line registry — the executable SSOT for detection. ONLY true red lines belong
# here (see red-lines.md § Admission criteria); general constraints must NOT be added.
# ---------------------------------------------------------------------------
RED_LINES = [
    {
        "id": "RL-FOCUS-01",
        "attribute": "automation",
        "invariant": ("No automation method may steal the user's system focus or pop a "
                      "window/tab in front of their work (causes mistyped input and "
                      "interrupts real work)."),
        "violation": [
            # (pattern, note, kind) — kind "hard" always triggers when un-negated; kind
            # "soft" is a context signal that triggers only when the skill shows NO
            # focus-safe vocabulary at all (a documented, announced headed/direct-binary
            # exception inside an otherwise focus-safe skill is presumed sanctioned).
            (r"bringToFront|bring_to_front",
             "re-activates the window; capture is CDP-based and needs no focus", "hard"),
            (r"--start-maximized|--start-fullscreen|--kiosk",
             "claims the whole screen", "hard"),
            (r"osascript[^\n]*\bactivate\b|tell application[^\n]*\bactivate\b",
             "AppleScript activate steals foreground", "hard"),
            (r"\b(xdotool|wmctrl)\s+(?:window\w+|search|activate|-[a-zA-Z])",
             "invokes xdotool/wmctrl window activation (racy, fires after the WM already activated)", "hard"),
            (r"nohup\s+[^\n]*Chrome|\"\$\{CHROME_MACOS\}\"|Google Chrome\.app/Contents/MacOS",
             "direct binary launch activates Chrome on macOS", "soft"),
            (r"open\s+-[a-zA-Z]*a\b(?![^\n]*\s-g)",
             "`open` without -g brings the app to the foreground", "soft"),
            (r"headless\s*[:=]\s*(false|False)",
             "headed launch maps a real window (F2 — must be announced + focus-safe)", "soft"),
        ],
        "compliance": [
            r"open\s+-g", r"chrome_open_\w*_quiet", r"chrome_open_quiet",
            r"headless\s*[:=]\s*(true|True)", r"connect[_ ]?over[_ ]?cdp|connectOverCDP",
            r"focus-safe|focus red line|焦点红线|不抢焦点|不置前|never call[^\n]*bringToFront",
            r"xvfb-run", r"announce",
        ],
        "remediation": ("Route every launch/attach through a focus-safe path: background "
                        "`open -g` (macOS) or headless/virtual-display; attach to a running "
                        "instance instead of relaunching; reuse background tabs; never call "
                        "bringToFront(); keep any genuinely-headed window announced, small and "
                        "fixed. Foreground/direct-binary launch is allowed ONLY as an announced "
                        "human-in-the-loop exception and must be gated + documented as such."),
        "refs": ["browser-utils references/focus-safe-launch.md",
                 "profiles-browsers SKILL.md § 焦点红线"],
    },
]

SKIP_DIRS = {"node_modules", "__pycache__", ".git",
             ".venv", "venv", ".mypy_cache", ".pytest_cache"}
POLICY_DENYLIST = {"redline-check.py", "red-lines.md"}
SCAN_EXT = {".md", ".py", ".sh", ".js", ".ts",
            ".mjs", ".cjs", ".yaml", ".yml", ".json"}


def _iter_files(root: str, file_only: bool, scan_all: bool, entry: str):
    if file_only:
        yield entry
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        # Default gate scope excludes references/ (encyclopedic L2 docs); --scan-all includes them.
        if not scan_all and os.path.basename(dirpath) == "references":
            dirnames[:] = []
            continue
        for fn in filenames:
            if fn in POLICY_DENYLIST:
                continue
            if os.path.splitext(fn)[1].lower() in SCAN_EXT:
                yield os.path.join(dirpath, fn)


def collect_attributes(texts: dict) -> dict:
    """Deterministic attribute collection over {path: content}."""
    found = {}
    for attr, spec in ATTRIBUTES.items():
        pats = [re.compile(p, re.IGNORECASE) for p in spec["signals"]]
        hits = []
        for path, body in texts.items():
            for m in set(p.search(body) for p in pats if p.search(body)):
                hits.append({"file": path, "match": m.group(0)[:60]})
        found[attr] = {"desc": spec["desc"], "present": bool(hits),
                       "evidence": hits[:8], "evidenceCount": len(hits)}
    return found


def evaluate(texts: dict, attributes: dict) -> list:
    results = []
    for rl in RED_LINES:
        attr = rl["attribute"]
        entry = {"id": rl["id"], "attribute": attr, "invariant": rl["invariant"],
                 "remediation": rl["remediation"], "refs": rl["refs"]}
        if not attributes.get(attr, {}).get("present"):
            entry["status"] = "not-applicable"
            entry["reason"] = f"attribute '{attr}' not detected — red line does not fire"
            results.append(entry)
            continue
        vpats = [(re.compile(p, re.IGNORECASE), note, kind)
                 for p, note, kind in rl["violation"]]
        cpats = [re.compile(p, re.IGNORECASE) for p in rl["compliance"]]
        hard, soft, prohibitions, compliance = [], [], [], []
        for path, body in texts.items():
            lines = body.split("\n")
            for i, line in enumerate(lines):
                ln_no = i + 1
                # Negation window ±2 lines: prohibitions and comment explanations often wrap
                # onto an adjacent line ("never call\n  bringToFront()", "--kiosk …\n never passed").
                window = "\n".join(lines[max(0, i - 2):min(len(lines), i + 3)])
                negated = bool(NEGATION.search(window))
                for pat, note, kind in vpats:
                    if pat.search(line):
                        rec = {"file": path, "line": ln_no, "note": note, "kind": kind,
                               "text": line.strip()[:120]}
                        if negated:
                            prohibitions.append(rec)
                        elif kind == "hard":
                            hard.append(rec)
                        else:
                            soft.append(rec)
                for pat in cpats:
                    if pat.search(line):
                        compliance.append({"file": path, "line": ln_no})
        # A soft signal only matters when the skill shows no focus-safe vocabulary at all;
        # with mitigation present, soft signals are presumed-sanctioned context, listed only.
        context = soft if compliance else []
        entry["hardSignals"] = hard[:20]
        entry["hardSignalCount"] = len(hard)
        entry["contextSignals"] = context[:20]
        entry["contextSignalCount"] = len(context)
        entry["prohibitionStatements"] = len(prohibitions)
        entry["complianceMarkers"] = len(compliance)
        if not compliance:
            # Drives automation with ZERO focus-safe vocabulary -> unmitigated red-line gap.
            entry["status"] = "gap"
            entry["violations"] = (hard + soft)[:20]
            entry["violationCount"] = len(hard) + len(soft)
            entry["reason"] = ("attribute present but NO focus-safe mitigation vocabulary found "
                               f"({len(hard)} hard + {len(soft)} soft signal(s), 0 compliance "
                               "markers) — red-line gap, remediation MANDATORY")
        elif hard:
            entry["status"] = "review"
            entry["violations"] = hard[:20]
            entry["violationCount"] = len(hard)
            entry["reason"] = (f"mitigation present but {len(hard)} un-negated HARD focus-steal "
                               "signal(s) remain — verify each is a sanctioned, announced "
                               "exception, otherwise remediate (MANDATORY)")
        else:
            entry["status"] = "compliant"
            entry["violations"] = []
            entry["violationCount"] = 0
            entry["reason"] = ("attribute present; focus-safe mitigation carried "
                               f"({len(compliance)} compliance marker(s), {len(prohibitions)} "
                               f"prohibition statement(s), {len(context)} sanctioned context signal(s))")
        results.append(entry)
    return results


def load_texts(entry: str, file_only: bool, scan_all: bool) -> dict:
    root = os.path.dirname(os.path.abspath(entry)) or "."
    texts = {}
    for path in _iter_files(root, file_only, scan_all, os.path.abspath(entry)):
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                texts[path] = fh.read()
        except OSError:
            continue
    return texts


def render(report: dict) -> str:
    out = [f"红线检查 / red-line check — {report['target']}"]
    attrs = report["attributes"]
    out.append("  属性 attributes:")
    for name, a in attrs.items():
        out.append(f"    {'●' if a['present'] else '○'} {name}: {a['desc']} "
                   f"({a['evidenceCount']} signal(s))")
    triggered = 0
    out.append("  红线 red lines:")
    for r in report["redLines"]:
        mark = {"not-applicable": "—", "compliant": "✓",
                "review": "✗", "gap": "✗"}[r["status"]]
        out.append(
            f"    {mark} [{r['id']}] {r['status']} (attr={r['attribute']}) — {r['reason']}")
        if r["status"] in ("review", "gap"):
            triggered += 1
            out.append(f"      invariant   : {r['invariant']}")
            out.append(f"      remediation : {r['remediation']} (MANDATORY)")
            for v in r.get("violations", [])[:8]:
                out.append(
                    f"      evidence  : [{v.get('kind', '?')}] {v['file']}:{v['line']} — {v['note']}")
                out.append(f"                  {v['text']}")
    verdict = "TRIGGERED — remediation required" if triggered else "PASS — no red line triggered"
    out.append(f"  判定 verdict: {verdict}")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="redline-check.py",
        description="Attribute-triggered red-line conformance probe for a target Skill.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__,
    )
    ap.add_argument("skill_md", help="path to the target SKILL.md")
    ap.add_argument("--scan-all", action="store_true",
                    help="also scan references/ (deeper, noisier audit)")
    ap.add_argument("--file-only", action="store_true",
                    help="scan only the SKILL.md, not its directory")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.skill_md):
        print(json.dumps(
            {"error": f"not a file: {args.skill_md}"}), file=sys.stderr)
        return 2

    texts = load_texts(args.skill_md, args.file_only, args.scan_all)
    attributes = collect_attributes(texts)
    red_lines = evaluate(texts, attributes)
    triggered = any(r["status"] in ("gap", "review") for r in red_lines)
    report = {
        "target": args.skill_md,
        "filesScanned": len(texts),
        "attributes": attributes,
        "redLines": red_lines,
        "verdict": "triggered" if triggered else "pass",
    }
    if not args.quiet:
        print(json.dumps(report, ensure_ascii=False, indent=2)
              if args.json else render(report))
    return 1 if triggered else 0


if __name__ == "__main__":
    sys.exit(main())
