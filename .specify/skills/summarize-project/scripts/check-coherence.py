#!/usr/bin/env python3
"""落盘前自洽性门禁检查器（summarize-project / consistency-rules.md CG-2..CG-8 + CG-COVERAGE）。

用途：在项目总结报告落盘**之前**跑一遍，机械检出"叙述与图元矛盾""图例与图元不覆盖"
"百分比无分母 / 算式不自洽""基准日不唯一""日期格式违规""WBS 节点超限""分解树覆盖
未声明 / 覆盖闭合等式不成立""目录自包含违规（相对路径引用的文件不在交付目录内 /
目录外引用 / 外链 URL）"等自洽性缺陷。以报告所在目录为交付目录根。

用法：
    python3 check-coherence.py <report.md> [--json] [--strict]

退出码：
    0  无 FAIL 项（可能有 WARN）
    1  存在 FAIL 项（--strict 时 WARN 也算失败）
    2  用法/读取错误

设计边界（重要）：
  * 本脚本只做**可机械判定**的核对。CG-1（图说计数 ⇄ 图元计数）需要人工比对——
    脚本会把每张图的**逐条状态计数**打印出来，人工只需拿图说里的数字逐个对上。
  * CG-5 / CG-7 / CG-9 / CG-10 依赖记录层与元信息语义，仍由 checklist 人工过检。
  * 脚本**只读**报告文件，不修改任何内容。

降噪纪律（v2，与噪声源一一对应）：
  * 数字/日期/编号类检查一律在 **prose**（正文）上做——正文 = 报告去掉 ```代码块```
    与内联 `<svg>…</svg>` 后的文本。这样甘特源码的 `is N% complete`、内联 SVG 的
    `width="100%"` 与坐标数字**不再**被误报为"裸百分比 / 裸编号"。
  * WBS 专属规则（CG-6 节点上限、部分着色 WBS-PARTIAL）**只作用于 `@startwbs` 块**；
    特性脑图（`@startmindmap`）天然节点多、分组节点用中性色不着状态类，套 WBS 规则会
    产生假 FAIL，故对脑图不判这两项（其可读性由 draw-plantuml 的字号量测负责）。
  * 裸百分比检测容忍 `分子 / …注记… 分母（P%）` 写法（如「已记录 21 / 全部 23 条（91%）」），
    只要邻近上下文里出现了分子/分母就不报。
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

# 统一四态色板（与 reporting-playbook.md「跨层图表呈现公约」§1.1 一致）
# 工作项四态用浅色（节点/条形内有深色文字），里程碑三态用饱和色（菱形是小图元）。
PALETTE = {
    "#C6E9CB": "completed",
    "#BBD8EE": "in-progress",
    "#EF9A9A": "delayed",
    "#ECEFF1": "not-started",
    "#43A047": "milestone-achieved",
    "#FFD54F": "milestone-pending",
    "#E53935": "milestone-at-risk",
    "#1565C0": "today-line",
}
# WBS 样式类 → 状态语义
WBS_CLASSES = {"done": "completed", "doing": "in-progress", "late": "delayed", "todo": "not-started"}
STATE_NAMES = set(WBS_CLASSES.values())

WBS_NODE_RE = re.compile(r"(?m)^\*{2,}.*$")          # 深度 >=2 的节点（根节点 `*` 不计）
HAPPENS_RE = re.compile(r"(?m)^\[.*?\]\s+happens\b")
STATUS_TAG_RE = re.compile(r"<<(done|doing|late|todo)>>")
# 分解树覆盖完整性的显式声明标记（§11）——刻意收紧，避开「人员维度覆盖率」「该工作项
# 覆盖的各 spec」等无关"覆盖"字样；只有明确声明分解树覆盖完整性/残差清单才算数
COVERAGE_MARKER = re.compile(r"分解树覆盖|覆盖完整性|残差清单|未归属工作项|归属残差|覆盖残差")


def prose_of(text: str) -> str:
    """正文 = 报告去掉所有 ```围栏代码块``` 与内联 `<svg>…</svg>` 后的文本。

    数字/日期/编号类检查在正文上进行：甘特源码里的 `is N% complete`、内联 SVG 的
    `width="100%"` 与路径坐标数字都属于"图元/渲染产物"，不是"报告的事实声明"，
    留在检查输入里只会制造噪声（上一轮 71 条 WARN 的主因）。
    """
    t = re.sub(r"```.*?```", "", text, flags=re.S)          # 全部围栏代码块（含 plantuml）
    t = re.sub(r"<svg\b.*?</svg>", "", t, flags=re.S)       # 内联渲染 SVG
    return t


def block_kind(src: str) -> str:
    if "@startwbs" in src:
        return "wbs"
    if "@startmindmap" in src:
        return "mindmap"
    if "@startgantt" in src:
        return "gantt"
    return "other"


class Findings:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, level: str, code: str, msg: str) -> None:
        self.items.append({"level": level, "code": code, "message": msg})

    def fail(self, code: str, msg: str) -> None:
        self.add("FAIL", code, msg)

    def warn(self, code: str, msg: str) -> None:
        self.add("WARN", code, msg)

    def counts(self) -> collections.Counter:
        return collections.Counter(i["level"] for i in self.items)


def split_block(src: str) -> tuple[str, str]:
    """把一个 plantuml 块拆成 (图元正文, 图例文本)。

    图元正文排除 <style>...</style> 定义块、legend 区、注释行——这样"样式类里声明过
    的颜色"不会被误算成"图中出现过该状态的条目"。
    """
    lines = src.splitlines()
    legend_lines = [l for l in lines if re.match(r"\s*\|", l) or "<back:" in l]
    style = re.search(r"<style>.*?</style>", src, re.S)
    stripped = src[: style.start()] + src[style.end() :] if style else src
    body_lines = [
        l
        for l in stripped.splitlines()
        if not re.match(r"\s*('|legend\b|end ?legend|endlegend|\|)", l) and "<back:" not in l
    ]
    return "\n".join(body_lines), "\n".join(legend_lines)


def count_elements(body: str) -> collections.Counter:
    """逐条统计图元的状态数量：WBS 数 <<class>> 标签，甘特数 `is colored in #HEX`。

    里程碑的 pending 是**默认色**（`<style>` 的 milestone 统一琥珀色），源码里不会写
    `is colored in #FFD54F`；因此 pending 数须由 `happens` 总数减去显式着色为
    achieved / at-risk 的条数推出，否则会对合法图例误报 CG-2。
    """
    cnt: collections.Counter = collections.Counter()
    for tag, name in WBS_CLASSES.items():
        n = len(re.findall(rf"<<{tag}>>", body))
        if n:
            cnt[name] += n
    for hexv, name in PALETTE.items():
        if name == "today-line":
            continue
        n = len(re.findall(rf"is colored in\s*{re.escape(hexv)}", body, re.I))
        if n:
            cnt[name] += n
    total_ms = len(HAPPENS_RE.findall(body))
    if total_ms:
        implicit_pending = total_ms - cnt.get("milestone-achieved", 0) - cnt.get("milestone-at-risk", 0)
        if implicit_pending > 0:
            cnt["milestone-pending"] = max(cnt.get("milestone-pending", 0), implicit_pending)
    return cnt


def check_blocks(text: str, f: Findings, report: dict) -> None:
    blocks = re.findall(r"```plantuml\n(.*?)```", text, re.S)
    report["blocks"] = []
    report["has_wbs"] = False
    if not blocks:
        f.fail("CG-0", "没有任何 plantuml 图源（assets/ 无 .puml 且正文无源码块）→ 图源⇄渲染产物须同名配对交付")
        return
    for idx, src in enumerate(blocks, 1):
        kind = block_kind(src)
        body, legend = split_block(src)
        nodes = WBS_NODE_RE.findall(src)
        happens = HAPPENS_RE.findall(body)
        cnt = count_elements(body)
        untagged = [l for l in nodes if not STATUS_TAG_RE.search(l)]
        info = {
            "block": idx,
            "kind": kind,
            "wbs_nodes": len(nodes),
            "happens": len(happens),
            "element_state_counts": dict(cnt),
            "untagged_nodes": len(untagged),
        }
        report["blocks"].append(info)
        if kind == "wbs":
            report["has_wbs"] = True

        # CG-2 图例 ⇄ 图元双向覆盖
        for hexv, name in PALETTE.items():
            if name == "today-line":
                continue
            in_body = cnt.get(name, 0) > 0 or bool(re.search(re.escape(hexv), body, re.I))
            in_legend = bool(re.search(re.escape(hexv), legend, re.I))
            if in_legend and not in_body:
                # 豁免：该图例行显式标注「（本图无）」= 作者已确认并向读者声明
                exempt = any(
                    re.search(re.escape(hexv), l, re.I) and "（本图无）" in l
                    for l in legend.splitlines()
                )
                if not exempt:
                    f.fail(
                        "CG-2",
                        f"块{idx}：图例声明了 {hexv}（{name}）但图元中无任何该状态条目"
                        f" → 默认修法：按零实例退化删掉该图例行（并删掉对应样式类）；仅当用户显式要求保留完整状态对照时，才改为在该图例行加「（本图无）」标注并记入元信息",
                    )
            if in_body and legend and not in_legend:
                f.fail("CG-2", f"块{idx}：图元中有 {name}（{hexv}）但图例未解释")
        if cnt and not legend:
            f.fail("CG-2", f"块{idx}：图中用颜色编码了状态却没有图例（有色即须有 legend）")

        # 以下两项是 WBS 专属规则：只作用于 @startwbs。
        # 特性脑图（@startmindmap）节点多、分组节点用中性 .group 色不打状态类，属正常，
        # 套用 WBS 的「节点≤15」「全打或全不打状态类」会制造假 FAIL（可读性交给字号量测）。
        if kind == "wbs":
            # 部分节点着色 = 未着色被读成某种状态（work-breakdown.md「信息缺失的降级」）
            if nodes and untagged and len(untagged) != len(nodes):
                f.fail(
                    "WBS-PARTIAL",
                    f"块{idx}：{len(untagged)}/{len(nodes)} 个 WBS 节点未打状态类"
                    f" → 须全部打或全部不打，避免「未着色=某种状态」误读",
                )
            # CG-6 单图节点上限（口径：深度 >=2 的节点，根节点不计）
            if len(nodes) > 15:
                f.fail(
                    "CG-6",
                    f"块{idx}：WBS 节点数 {len(nodes)} > 15 → 必须按 consistency-rules.md §3.3"
                    f" 图集拆分；禁止靠合并真实工作项压缩节点数（§3.2）",
                )
            elif len(nodes) > 12:
                f.warn("CG-6", f"块{idx}：WBS 节点数 {len(nodes)} 已超软建议上限 12")


def check_numbers(prose: str, f: Findings, report: dict) -> None:
    # CG-4a：裸百分比（邻近上下文无 `分子/分母` 形态；容忍中文注记/括号夹在分母与 % 之间）
    #
    # 豁免（v3）：**进度类表格单元格**里的百分比是引擎字段（`progress_pct`）的逐行转录，
    # 不是报告级统计声明——要求它写成"分子/分母"既无意义也会让每个任务/里程碑行都刷一条
    # WARN。判据：该百分比所在行是表格行（以 `|` 开头），且 ① 同行出现进度条格串 `█`/`░`，
    # 或 ② 该行上方最近的表头行含「进度 / 完成度 / 达成进度 / 达成度」列名。
    prose_lines = prose.splitlines(keepends=True)
    line_starts, _acc = [], 0
    for ln in prose_lines:
        line_starts.append(_acc)
        _acc += len(ln)

    def _progress_cell(pos: int) -> bool:
        idx = max(i for i, st in enumerate(line_starts) if st <= pos) if line_starts else -1
        if idx < 0:
            return False
        line = prose_lines[idx]
        if not line.lstrip().startswith("|"):
            return False
        if "█" in line or "░" in line:
            return True
        for back in range(idx - 1, max(-1, idx - 40), -1):
            prev = prose_lines[back]
            if not prev.lstrip().startswith("|"):
                break
            if re.search(r"进度|完成度|达成度", prev):
                return True
        return False

    bare = []
    for m in re.finditer(r"(?<![/\d])\d{1,3}(?:\.\d+)?%", prose):
        head = prose[max(0, m.start() - 24) : m.start()]
        # 命中任一即视为已给分子/分母：① 紧邻 `N/M=?`；② `N / …≤18 非斜杠字符…（` 收尾
        if re.search(r"\d+\s*/\s*\d+\s*=?\s*$", head) or re.search(r"\d+\s*/\s*[^/=%]{0,18}$", head):
            continue
        if _progress_cell(m.start()):
            continue
        bare.append({"value": m.group(0), "context": prose[max(0, m.start() - 40) : m.end()].replace("\n", " ")})
    report["bare_percentages"] = bare
    for b in bare:
        f.warn(
            "CG-4",
            f"疑似无分母百分比 {b['value']}（…{b['context'][-46:]}）"
            f" → 改写为「分子/分母 = xx.x%」，或人工确认为引用原文后登记入元信息",
        )

    # CG-4b：`N/M = P%` 算式自洽
    fracs = []
    for n, d, p in re.findall(r"(\d+)\s*/\s*(\d+)\s*=\s*(\d{1,3}(?:\.\d+)?)\s*%", prose):
        ni, di, pf = int(n), int(d), float(p)
        if di == 0:
            f.fail("CG-4", f"算式 {n}/{d} 分母为 0")
            continue
        calc = round(ni * 100 / di, 1)
        ok = abs(calc - pf) <= 0.15
        fracs.append({"numerator": ni, "denominator": di, "stated": pf, "actual": calc, "ok": ok})
        if not ok:
            f.fail("CG-4", f"算式不自洽：{n}/{d} 写作 {p}%，实算 {calc}%")
        if ni > di:
            f.fail("CG-4", f"算式不自洽：分子 {n} > 分母 {d}")
    report["fractions"] = fracs

    # CG-3：`a+b+c = T` 形态的加法闭合
    sums = []
    for m in re.finditer(r"(\d+(?:\s*\+\s*\d+){1,8})\s*=\s*(\d+)", prose):
        parts = [int(x) for x in re.findall(r"\d+", m.group(1))]
        total, stated = sum(parts), int(m.group(2))
        ok = total == stated
        sums.append({"parts": parts, "stated": stated, "actual": total, "ok": ok})
        if not ok:
            f.fail("CG-3", f"分桶加法不闭合：{m.group(1)} 实为 {total}，报告写 {stated}（差 {stated - total}）")
    report["sums"] = sums


def check_coverage(prose: str, f: Findings, report: dict) -> None:
    """CG-COVERAGE（§11 分解树覆盖完整性门禁的机械部分）。

    两件事：① 若报告含 WBS，必须**显式声明**分解树覆盖完整性（穷尽候选工作来源、残差
    清单、进度百分比分母集合＝分解树覆盖范围）——否则"121 项工作未归属任何工作项却未
    披露"这类缺口就会静默落盘；② 若报告写了覆盖闭合等式 `X − a − b − c = Y`，验算它。
    """
    # ② 覆盖闭合等式验算（先去括注 `（未排期）` 之类，再验 first − Σsub = last）
    cleaned = re.sub(r"[（(][^（()）]*[)）]", "", prose)
    closures = []
    for m in re.finditer(r"(?<![\d.\-])(\d+)\s*((?:[-−]\s*\d+\s*){1,8})=\s*(\d+)", cleaned):
        first = int(m.group(1))
        subs = [int(x) for x in re.findall(r"\d+", m.group(2))]
        last = int(m.group(3))
        ok = first - sum(subs) == last
        closures.append({"first": first, "subtract": subs, "stated": last, "actual": first - sum(subs), "ok": ok})
        if not ok:
            f.fail(
                "CG-COVERAGE",
                f"覆盖闭合等式不成立：{first} − {' − '.join(map(str, subs))} 实为 {first - sum(subs)}，报告写 {last}"
                f"（§9.2 差值必须有名有数）",
            )
    report["coverage_closures"] = closures

    # ① 覆盖完整性声明存在性
    if report.get("has_wbs") and not COVERAGE_MARKER.search(prose):
        f.fail(
            "CG-COVERAGE",
            "报告含功能分解树（WBS）却未声明**分解树覆盖完整性** → 须穷尽候选工作来源、"
            "给出残差清单、并声明进度百分比的分母集合＝分解树覆盖范围（consistency-rules.md §11）；"
            "即便无残差也须显式写「分解树覆盖：残差清单为空（覆盖率 100%）」",
        )


def check_dates(prose: str, f: Findings, report: dict) -> None:
    # CG-8 基准日唯一。字面量形态以 progress-presentation.md §7 固定小节为准：
    # `- 基准日 D0：<baseline>` —— 标签与日期之间允许出现 D0 指称符与空白，
    # 旧正则看不见 D0 形态，导致模板强制的写法反而 WARN"未找到基准日"。
    days = sorted(set(re.findall(
        r"(?:基准日|today)\s*(?:D0)?\s*[=＝:：]?\s*(\d{4}-\d{2}-\d{2})", prose)))
    report["baseline_dates"] = days
    if len(days) > 1:
        # 注意：按"不同取值"判 FAIL——同一基准日在多章重复出现（截至表述、
        # 图题、元信息）是模板要求的正常形态，不构成违规。
        f.fail("CG-8", f"报告中存在多个不同的基准日取值 {days} → 全报告只能有一个基准日 D0")
    elif not days:
        f.warn("CG-8", "未找到「基准日 D0：/ 基准日：/ today = yyyy-mm-dd」字面量（进行期项目须显式声明基准日）")

    # 日期格式公约
    bad = re.findall(r"\d{4}[/.]\d{1,2}[/.]\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日|\d{1,2}月\d{1,2}日", prose)
    report["bad_dates"] = bad
    for b in sorted(set(bad)):
        f.fail("DATE", f"非 yyyy-mm-dd 日期写法：{b}")


def check_selfcontained(text: str, f: Findings, report: dict, base_dir: pathlib.Path,
                        puml_files: list | None = None) -> None:
    """目录自包含检查：报告以相对路径引用交付目录内的渲染图片（`![…](assets/x.svg)`）。

    - 相对路径引用的文件必须**存在于交付目录内**（以报告所在目录为根）；
    - 引用交付目录外的文件（`..` 逃逸、绝对路径）或外链 URL（http/https 等）→ FAIL；
    - 每个 plantuml 源码块之后应有其渲染图引用（或渲染失败告示）；
    - assets 形态（源码落 `assets/*.puml`）：引用图 ⇄ `.puml` 图源同名双向配对
      （每张引用图有同名图源；每个图源被正文引用或有渲染失败告示）。
    """
    base = base_dir.resolve()
    imgs = re.findall(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", text)
    outside: list = []
    missing: list = []
    ok_refs: list = []
    for u in imgs:
        if u.startswith("data:"):
            ok_refs.append(u)  # data URI 自身即自包含
            continue
        if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*://", u) or u.startswith("//"):
            outside.append(u)  # 外链 URL
            continue
        if u.startswith("/"):
            outside.append(u)  # 绝对路径 = 目录外依赖
            continue
        target = (base / u).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            outside.append(u)  # `..` 逃逸出交付目录
            continue
        if not target.is_file():
            missing.append(u)
        else:
            ok_refs.append(u)
    report["image_refs"] = ok_refs
    report["image_refs_outside"] = outside
    report["image_refs_missing"] = missing
    for u in outside:
        f.fail("SELF", f"图片引用 `{u}` 指向交付目录外（绝对路径 / `..` 逃逸 / 外链 URL）→ 违反目录自包含")
    for u in missing:
        f.fail("SELF", f"相对路径图片引用 `{u}` 在交付目录内不存在 → 渲染产物缺失或路径写错")
    n_src = len(re.findall(r"```plantuml\n", text))
    n_img = len(ok_refs)
    n_svg = len(re.findall(r"<svg", text))  # 兼容旧单文件形态的内联 SVG
    n_warn = len(re.findall(r">\s*⚠\s*本图渲染失败", text))
    report["plantuml_blocks"] = n_src
    report["rendered_image_refs"] = n_img
    report["inline_svg"] = n_svg
    report["render_failed_notices"] = n_warn
    if n_img + n_svg + n_warn < n_src:
        f.fail(
            "SELF",
            f"{n_src} 个 plantuml 块，但只有 {n_img} 个渲染图引用 + {n_svg} 个内联 SVG + {n_warn} 条渲染失败告示"
            f" → 存在未渲染的裸源码块",
        )
    if puml_files:
        stems = {pf.stem for pf in puml_files}
        for u in ok_refs:
            if u.startswith("data:"):
                continue
            if pathlib.PurePosixPath(u).stem not in stems:
                f.fail("SELF", f"引用图 `{u}` 在 assets/ 内无同名 `.puml` 图源 → 图源⇄渲染产物须同名配对")
        # referenced = rendered refs (ok) + refs whose render artifact is missing
        # (already flagged) — both prove the .puml is referenced by the body.
        referenced_stems = {pathlib.PurePosixPath(u).stem
                            for u in ok_refs + missing}
        for pf in puml_files:
            if pf.stem not in referenced_stems:
                f.fail("SELF", f"assets/{pf.name} 未被正文渲染图引用（也无渲染失败告示）→ 图源⇄渲染产物须同名配对")


def check_id_namespace(prose: str, f: Findings, report: dict) -> None:
    """§9.1：禁止裸编号。在 prose（已剥离 plantuml/SVG）上检查——图源里的
    `today is 200 days after start`、SVG 路径坐标等计量数字不是编号，先剥离再查。"""
    UNIT = r"(?:\s*(?:days?|天|条|个|项|次|行|人|px|%|号|年|月|日|周))"
    bare_ids = set()
    for m in re.finditer(r"(?<![\w\-/.])(\d{3})(?![\w\-/.%])", prose):
        head = prose[max(0, m.start() - 3) : m.start()]
        tail = prose[m.end() : m.end() + 8]
        if re.search(r"[FSPTfspt]-$|第$|共$|约$", head):
            continue
        if re.match(UNIT, tail):
            continue
        bare_ids.add(m.group(1))
    report["bare_ids"] = sorted(bare_ids)
    if bare_ids:
        f.warn(
            "CG-ID",
            f"疑似裸编号 {sorted(bare_ids)[:10]} → 特性用 `F-NNN`、规格用 `S-<key>`、"
            f"报告自编工作项用 `P-`/`T-`，裸号会混淆命名空间（§9.1）",
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="summarize-project 落盘前自洽性门禁检查器")
    ap.add_argument("report", help="报告 Markdown 文件路径")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出机器可读结果")
    ap.add_argument("--strict", action="store_true", help="WARN 也视为失败")
    args = ap.parse_args()

    path = pathlib.Path(args.report)
    if not path.is_file():
        print(f"错误：找不到报告文件 {path}", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8")
    prose = prose_of(text)

    f = Findings()
    report: dict = {"report": str(path)}
    # 图源优先读 assets/*.puml（consistency-rules：源码只作为 .puml 文件交付，正文不出现
    # 源码块）；assets/ 无 .puml 时退回正文残留围栏块（旧单文件形态兼容）。
    assets_dir = path.parent / "assets"
    puml_files = sorted(assets_dir.glob("*.puml")) if assets_dir.is_dir() else []
    if puml_files:
        diagram_text = "\n".join(
            "```plantuml\n" + pf.read_text(encoding="utf-8") + "\n```"
            for pf in puml_files)
        residual = len(re.findall(r"```plantuml\n", text))
        if residual:
            f.fail("SELF", f"正文残留 {residual} 个 plantuml 源码块 → 源码只作为 assets/*.puml 交付")
    else:
        diagram_text = text
    check_blocks(diagram_text, f, report)  # 图元/图例：需要 plantuml 源码，用图源
    check_numbers(prose, f, report)        # 数字：用正文（已去代码块 + SVG）
    check_coverage(prose, f, report)       # 覆盖完整性：用正文
    check_dates(prose, f, report)          # 日期：用正文
    check_selfcontained(text, f, report, path.parent, puml_files)  # 目录自包含：相对引用须落在交付目录内，用全文
    check_id_namespace(prose, f, report)   # 裸编号：用正文

    c = f.counts()
    report["findings"] = f.items
    report["summary"] = {"fail": c.get("FAIL", 0), "warn": c.get("WARN", 0)}

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"== 自洽性门禁检查：{path} ==\n")
        for b in report.get("blocks", []):
            print(
                f"[块{b['block']} · {b['kind']}] WBS节点={b['wbs_nodes']} happens={b['happens']} "
                f"未打状态类={b['untagged_nodes']}"
            )
            print(f"        图元逐条状态计数: {b['element_state_counts'] or '（无状态编码）'}")
        print("\n-- CG-1 人工核对提示：把上面每张图的「图元逐条状态计数」与该图图说/叙述中的数字逐个对上 --")
        if report.get("fractions"):
            print("\n-- 算式核对 --")
            for fr in report["fractions"]:
                mark = "OK" if fr["ok"] else "FAIL"
                print(f"   {fr['numerator']}/{fr['denominator']} 写 {fr['stated']}% 实算 {fr['actual']}%  {mark}")
        if report.get("coverage_closures"):
            print("\n-- 覆盖闭合等式核对 --")
            for cl in report["coverage_closures"]:
                mark = "OK" if cl["ok"] else "FAIL"
                print(f"   {cl['first']} − {cl['subtract']} = {cl['stated']}（实算 {cl['actual']}）  {mark}")
        if report.get("baseline_dates"):
            print(f"\n-- 基准日字面量: {report['baseline_dates']} --")
        print("\n-- 发现项 --")
        if not f.items:
            print("   （无）")
        for i in f.items:
            print(f"   [{i['level']}] {i['code']}: {i['message']}")
        print(f"\n结论：FAIL={c.get('FAIL', 0)}  WARN={c.get('WARN', 0)}")
        print("提示：CG-5/CG-7/CG-9/CG-10 需按 consistency-rules.md §8 清单人工过检（本脚本不覆盖）。")

    if c.get("FAIL", 0) or (args.strict and c.get("WARN", 0)):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
