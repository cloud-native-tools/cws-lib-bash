#!/usr/bin/env python3
"""skill-shape.py — measure whether a SKILL.md is still a contract (L1) or has become a manual.

Turns the slimming discipline into an objective, checkable verdict. Thresholds are
derived from the anti-pattern catalogue and the L0-L3 progressive-disclosure budget in
`../references/skill-slimming-principles.md`; every finding names the rule it comes from.

Usage
-----
    skill-shape.py <path/to/SKILL.md> [--budget-tokens N] [--json] [--quiet]

Exit codes
----------
    0   pass              — body is contract-shaped
    10  slim-recommended  — at least one blocking finding; slim before finishing the loop
    2   usage error

Why this exists
---------------
The slimming rule used to be prose-only ("evaluate whether sections should be moved
out"), with the quantitative facts living one level down in L2. A run that never opened
the reference never saw a number, so "is it slim enough?" had no verdict and the rule was
silently skipped while the body grew. Deterministic logic belongs in code.

Thresholds (all tunable; defaults cite their source)
----------------------------------------------------
    L1 token budget      <= 5000   progressive-disclosure budget, applied to the
                                   *controllable* body (see below)
    fence-line ratio     <= 25%    "code block longer than 5 lines belongs in a reference"
    non-diagram fences   <= 2      same catalogue entry, allowing a couple of skeletons
    example sections     none      worked examples are L2 material, not contract
    H2 section lines      > 40     reported as a *warning* only (see calibration)

Controllable vs mandated: some sections are canonical blocks that contract tests assert are
present inline (`## Feedback`, `## Agent-Specific Configuration`). Their tokens are reported
but excluded from the budget check — an author cannot slim them, and gating on a number nobody
can move produces a permanently red gate that trains people to ignore it. The budget therefore
binds the part the author actually controls.

Calibration: thresholds were measured against the whole 26-skill library before being
wired as a gate. Blocking on H2-section length flagged 17/26 skills — a gate that fires on
two thirds of the corpus trains agents to ignore it, so section length is a warning and the
four discriminating rules above stay blocking (9/26 flagged, and they are the genuine
offenders: 23.6K / 13.8K / 13.1K / 7.8K-token bodies). Re-calibrate before changing a
severity: a gate is only useful if passing it means something.

Token estimate: CJK codepoints count as 1 token each; remaining characters are counted at
4 chars/token. This is an estimate, not a tokenizer — it is stable enough to compare a
body against a budget and to compare before/after in an intervention ledger.
"""

import argparse
import json
import re
import sys
import unicodedata

CJK_RANGES = (
    (0x3000, 0x303F), (0x3040, 0x30FF), (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF), (0xF900, 0xFAFF), (0xFF00, 0xFFEF),
)

# Sections whose implementation-flavoured content is contract-mandated and therefore
# exempt from the "no concrete CLI flags outside strict-requirements/conventions" rule
# (Principle 7.2). Feedback + Agent-Specific Configuration are canonical blocks that
# contract tests assert are present inline; security/red-line sections are contract content
# by definition (a destructive-operation prohibition must name the flag it forbids).
FLAG_EXEMPT_SECTIONS = re.compile(
    r"feedback|agent-specific configuration|strict requirement|hard constraint"
    r"|constraints|conventions|security|red line|严格要求|硬约束|约定|安全|红线",
    re.IGNORECASE,
)
EXAMPLE_SECTION = re.compile(
    r"^(examples?|usage examples?|worked examples?|示例|用法示例|例子)\b",
    re.IGNORECASE,
)
# Canonical blocks that contract tests assert are present inline. Their content is not the
# author's to slim, so it is reported but excluded from the token budget.
MANDATED_SECTION = re.compile(
    r"^(feedback|agent-specific configuration)\s*$", re.IGNORECASE
)
INSTALL_SECTION = re.compile(r"^(installation|setup|install|安装|环境准备)\b", re.IGNORECASE)
DIAGRAM_HINT = re.compile(r"[─│└├┌┐┘┬┴┼→←↑↓]|^\s*(graph|sequenceDiagram|flowchart)\b")
SYMPTOM_TABLE = re.compile(
    r"\|\s*(symptom|症状)\s*\|.*\|\s*(fix|修复|处置)\s*\|", re.IGNORECASE
)
FLAG_TOKEN = re.compile(r"(?<![\w-])--[a-zA-Z][a-zA-Z0-9-]{1,}")


def is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in CJK_RANGES)


def estimate_tokens(text: str) -> int:
    cjk = sum(1 for ch in text if is_cjk(ch))
    rest = len(text) - cjk
    return cjk + round(rest / 4)


def parse(text: str):
    """Split the body into fences and H2 sections (frontmatter excluded from sections)."""
    lines = text.split("\n")
    fences, sections = [], []
    cur_fence = None
    cur_sec = {"name": "(preamble)", "start": 1, "lines": 0}
    in_frontmatter = lines[:1] == ["---"]
    fm_end = 0
    if in_frontmatter:
        for i, ln in enumerate(lines[1:], start=2):
            if ln.strip() == "---":
                fm_end = i
                break

    for idx, ln in enumerate(lines, start=1):
        if idx <= fm_end:
            continue
        stripped = ln.strip()
        if stripped.startswith("```"):
            if cur_fence is None:
                cur_fence = {"start": idx, "lang": stripped[3:].strip(), "body": []}
            else:
                cur_fence["end"] = idx
                fences.append(cur_fence)
                cur_fence = None
            continue
        if cur_fence is not None:
            cur_fence["body"].append(ln)
            continue
        if ln.startswith("## "):
            sections.append(cur_sec)
            cur_sec = {"name": ln[3:].strip(), "start": idx, "lines": 0}
        else:
            cur_sec["lines"] += 1
    sections.append(cur_sec)
    return lines, fences, sections, fm_end


def analyse(path: str, budget: int) -> dict:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    lines, fences, sections, fm_end = parse(text)
    total = len(lines)
    body_text = "\n".join(lines[fm_end:])

    fence_lines = sum((f.get("end", f["start"]) - f["start"] + 1) for f in fences)
    est = estimate_tokens(body_text)
    ratio = round(fence_lines * 100 / total) if total else 0

    # Tokens sitting inside contract-mandated canonical blocks (not slimmable by the author).
    mandated, mandated_names = 0, []
    for s_i, s in enumerate(sections):
        if not MANDATED_SECTION.match(s["name"]):
            continue
        end = sections[s_i + 1]["start"] if s_i + 1 < len(sections) else total + 1
        mandated += estimate_tokens("\n".join(lines[s["start"] - 1:end - 1]))
        mandated_names.append(s["name"])
    controllable = max(est - mandated, 0)

    # attribute each fence to its enclosing section, and classify diagram vs code
    long_fences = []
    for f in fences:
        content = [b for b in f["body"] if b.strip()]
        joined = "\n".join(f["body"])
        diagram = bool(DIAGRAM_HINT.search(joined)) or f["lang"] in ("text", "mermaid")
        if len(content) > 5 and not diagram:
            sec = "(preamble)"
            for s in sections:
                if s["start"] <= f["start"]:
                    sec = s["name"]
            long_fences.append(
                {"line": f["start"], "lines": len(content), "lang": f["lang"] or "-",
                 "section": sec}
            )

    findings = []

    def add(rule, severity, detail, blocking):
        findings.append({"rule": rule, "severity": severity, "detail": detail,
                         "blocking": blocking})

    if controllable > budget:
        add("l1-token-budget", "over",
            f"可控正文 ≈ {controllable} tokens > 预算 {budget}"
            + (f"（全文 {est}，已扣除契约强制块 {mandated}：{mandated_names}）"
               if mandated else "（L1 在触发时整体载入，超预算会稀释硬约束）"),
            True)
    if ratio > 25:
        add("fence-ratio", "over",
            f"代码围栏占正文 {ratio}%（{fence_lines}/{total} 行）> 25%：正文已偏向手册而非契约",
            True)
    if len(long_fences) > 2:
        add("long-fences", "over",
            f"{len(long_fences)} 段非图示代码块超过 5 行（上限 2）："
            + "；".join(f"L{x['line']}({x['lines']}行·{x['section']})"
                        for x in long_fences[:6]),
            True)
    over_sections = [s for s in sections if s["lines"] > 40]
    if over_sections:
        add("oversized-section", "warn",
            "；".join(f"{s['name']}={s['lines']}行" for s in over_sections)
            + "（单章节建议上限 40 行；工作流骨架可适当超出，但应检查是否夹带手册内容）",
            False)
    ex_sections = [s["name"] for s in sections if EXAMPLE_SECTION.match(s["name"])]
    if ex_sections:
        add("example-section", "over",
            f"存在示例章节 {ex_sections}：完整示例属于 references/（L2），契约层只留骨架",
            True)

    # non-blocking signals
    flag_hits = {}
    for s_i, s in enumerate(sections):
        if FLAG_EXEMPT_SECTIONS.search(s["name"]):
            continue
        end = sections[s_i + 1]["start"] if s_i + 1 < len(sections) else total + 1
        chunk = "\n".join(lines[s["start"]:end - 1])
        hits = set(FLAG_TOKEN.findall(chunk))
        if hits:
            flag_hits[s["name"]] = sorted(hits)
    if flag_hits:
        n = sum(len(v) for v in flag_hits.values())
        add("flags-outside-contract", "warn",
            f"{n} 个具体 CLI flag 出现在非约束章节："
            + "；".join(f"{k}({len(v)})" for k, v in list(flag_hits.items())[:5]),
            False)
    if SYMPTOM_TABLE.search(body_text):
        add("symptom-cause-fix-table", "warn", "存在 症状|原因|修复 形态的表格，应移入 references/", False)
    inst = [s["name"] for s in sections if INSTALL_SECTION.match(s["name"])]
    if inst:
        add("install-section", "warn", f"存在安装/环境准备章节 {inst}：环境工作应交还用户", False)

    blocking = [f for f in findings if f["blocking"]]
    return {
        "path": path,
        "verdict": "slim-recommended" if blocking else "pass",
        "metrics": {
            "total_lines": total,
            "est_tokens": est,
            "est_tokens_controllable": controllable,
            "est_tokens_mandated": mandated,
            "mandated_sections": mandated_names,
            "budget_tokens": budget,
            "fence_lines": fence_lines,
            "fence_ratio_pct": ratio,
            "fences": len(fences),
            "long_non_diagram_fences": len(long_fences),
            "sections": len([s for s in sections if s["name"] != "(preamble)"]),
            "largest_section": max(
                ((s["lines"], s["name"]) for s in sections), default=(0, "-")
            )[1],
        },
        "findings": findings,
        "long_fences": long_fences,
        "section_lines": {s["name"]: s["lines"] for s in sections if s["lines"]},
    }


def render(r: dict) -> str:
    m = r["metrics"]
    tok = (f"≈{m['est_tokens_controllable']} tokens 可控 / 预算 {m['budget_tokens']}"
           + (f"（全文 {m['est_tokens']}，契约强制块 {m['est_tokens_mandated']}）"
              if m["est_tokens_mandated"] else ""))
    out = [
        f"SKILL.md 形态检查 — {r['path']}",
        f"  判定        {r['verdict']}",
        f"  正文估算     {tok}（{m['total_lines']} 行）",
        f"  代码围栏     {m['fences']} 段 / {m['fence_lines']} 行 = {m['fence_ratio_pct']}%"
        f"，其中非图示超 5 行 {m['long_non_diagram_fences']} 段",
        f"  最大章节     {m['largest_section']}",
    ]
    if r["findings"]:
        out.append("  发现：")
        for f in r["findings"]:
            mark = "✗" if f["blocking"] else "!"
            out.append(f"    {mark} [{f['rule']}] {f['detail']}")
    else:
        out.append("  发现：无")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="skill-shape.py",
        description="度量 SKILL.md 是否仍是契约（L1），给出可校验判定。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("skill_md", help="SKILL.md 路径")
    ap.add_argument("--budget-tokens", type=int, default=5000)
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--quiet", action="store_true", help="只用退出码表达结果")
    args = ap.parse_args(argv)

    try:
        result = analyse(args.skill_md, args.budget_tokens)
    except OSError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    if not args.quiet:
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json
              else render(result))
    return 10 if result["verdict"] == "slim-recommended" else 0


if __name__ == "__main__":
    sys.exit(main())
