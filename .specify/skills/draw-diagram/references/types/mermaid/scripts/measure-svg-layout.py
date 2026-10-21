#!/usr/bin/env python3
"""measure-svg-layout.py — 量测已渲染 SVG 的版面几何，供 WBS / 甘特图的
「可读性与版面」自检使用（清晰度、长宽比、标签溢出、A/B 是否改写排期）。

为什么需要它：这些判据都必须**量出来**，凭直觉或查表会得出错误结论——
  • 有效字号 = font-size × 目标显示宽度 ÷ viewBox 宽度；放大 zoom 会同时放大
    画布，有效字号不变，所以"图太小就调大 zoom"是无效动作。
  • `viewBox 宽 − 最右元素 x` 结构性 ≈ 0（渲染引擎 紧贴内容裁画布），
    不能用来判断标签是否越界；甘特图要用「时间轴右边界 → 最右标签」的溢出量。
  • 判断某个写法是否改写了排期，唯一可靠办法是 A/B 两次渲染比对条形几何
    （--compare），肉眼看图或只量彩色块都会误判。

用法:
  measure-svg-layout.py <a.svg> [--display-width 1400] [--min-font-px 12]
  measure-svg-layout.py <a.svg> --compare <b.svg>

输出: stdout 一段 JSON。退出码 0 表示量测成功（不代表图"合格"，
      合格与否看 JSON 里的 checks / verdict 字段）。
"""

import argparse
import json
import re
import sys
from collections import Counter

TEXT_RE = re.compile(r"<text\s([^>]*)>(.*?)</text>", re.S)
RECT_RE = re.compile(r"<rect\s([^>]*?)/>")
LINE_RE = re.compile(r"<line\s([^>]*?)/>")
ATTR_RE = re.compile(r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)="([^"]*)"')


def attrs(chunk):
    return dict(ATTR_RE.findall(chunk))


def num(d, k, default=None):
    try:
        return float(d[k])
    except (KeyError, TypeError, ValueError):
        return default


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def view_box(svg):
    m = re.search(r'viewBox="([\d.\s-]+)"', svg)
    if not m:
        return None, None
    parts = [float(p) for p in m.group(1).split()]
    return parts[2], parts[3]


def diagram_type(svg):
    m = re.search(r'data-diagram-type="([A-Z]+)"', svg)
    if m:
        return m.group(1)
    for tag, kind in (("wbs", "WBS"), ("gantt", "GANTT"), ("mindmap", "MINDMAP")):
        if "@start" + tag in svg:
            return kind.upper()
    return "OTHER"


def texts(svg):
    out = []
    for chunk, body in TEXT_RE.findall(svg):
        a = attrs(chunk)
        x = num(a, "x")
        fs = num(a, "font-size")
        tl = num(a, "textLength", 0.0)
        if x is None or fs is None:
            continue
        label = re.sub(r"<[^>]*>", "", body)
        out.append({"x": x, "right": x + (tl or 0.0), "size": fs, "text": label})
    return out


def filled_rects(svg):
    """所有实心色块（甘特条形段、WBS 节点底色）。用于 A/B 几何比对。"""
    out = []
    for chunk in RECT_RE.findall(svg):
        a = attrs(chunk)
        fill = a.get("fill", "")
        if fill in ("", "none"):
            continue
        x, w = num(a, "x"), num(a, "width")
        y, h = num(a, "y"), num(a, "height")
        if None in (x, w, y, h):
            continue
        out.append((round(x, 2), round(y, 2), round(w, 2), round(h, 2), fill))
    return out


def bar_rects(svg):
    """只取"条形段"色块：取实心色块中出现次数最多的那一档高度。
    这样可排除贯穿全高的背景列（周末闭合列、着色区间、today 竖线）与图例色块——
    否则给时间轴加一段留白着色区间也会被误判成"排期被改写"。"""
    rects = filled_rects(svg)
    if not rects:
        return [], None
    modal = Counter(r[3] for r in rects).most_common(1)[0][0]
    return [r for r in rects if r[3] == modal], modal


def vertical_grid_x(svg):
    xs = []
    for chunk in LINE_RE.findall(svg):
        a = attrs(chunk)
        x1, x2 = num(a, "x1"), num(a, "x2")
        y1, y2 = num(a, "y1"), num(a, "y2")
        if None in (x1, x2, y1, y2):
            continue
        if abs(x1 - x2) < 0.01 and abs(y2 - y1) > 1:
            xs.append(x1)
    return sorted(set(xs))


def measure(path, display_width, min_font_px):
    svg = read(path)
    vw, vh = view_box(svg)
    if not vw:
        raise SystemExit("cannot parse viewBox from %s" % path)
    tx = texts(svg)
    sizes = Counter(round(t["size"], 2) for t in tx)
    body = sizes.most_common(1)[0][0] if sizes else 0.0
    smallest = min(sizes) if sizes else 0.0
    ratio = display_width / vw

    report = {
        "svg": path,
        "diagramType": diagram_type(svg),
        "viewBox": {"w": vw, "h": vh},
        "aspect": round(vw / vh, 3) if vh else None,
        "font": {
            "sizesInViewBoxUnits": {str(k): v for k, v in sorted(sizes.items())},
            "distinctSizes": len(sizes),
        },
        "display": {
            "widthPx": display_width,
            "effectiveBodyFontPx": round(body * ratio, 2),
            "effectiveSmallestFontPx": round(smallest * ratio, 2),
            "minFontPxThreshold": min_font_px,
            "readable": bool(body * ratio >= min_font_px),
            "widthPxNeededForBodyThreshold": int(round(min_font_px * vw / body)) if body else None,
        },
        "checks": [],
    }

    if not report["display"]["readable"]:
        report["checks"].append(
            "FAIL readability: 正文有效字号在 %dpx 宽下只有 %.1fpx（阈值 %dpx）。"
            "改粗刻度 / 减内容 / 拆图，或按 %dpx 宽内联并提供大图链接；"
            "放大 zoom 无效——画布同比变大，有效字号不变。"
            % (display_width, body * ratio, min_font_px,
               report["display"]["widthPxNeededForBodyThreshold"] or 0)
        )
    elif smallest * ratio < min_font_px:
        report["checks"].append(
            "WARN readability: 正文可读，但最小字号只有 %.1fpx（阈值 %dpx）——"
            "把最小的那档字号（note/legend/刻度）上调一档。"
            % (smallest * ratio, min_font_px)
        )
    if report["aspect"] and not (0.8 <= report["aspect"] <= 2.2):
        report["checks"].append(
            "WARN aspect: 长宽比 %.2f:1 偏离 0.8~2.2 的舒适区间，成图会显得细长或瘦高。"
            % report["aspect"]
        )

    if report["diagramType"] == "GANTT":
        grid = vertical_grid_x(svg)
        timeline_right = max(grid) if grid else None
        label_right = max((t["right"] for t in tx), default=0.0)
        g = {
            "timelineRightX": timeline_right,
            "timelineColumns": max(len(grid) - 1, 0),
            "rightMostLabelEnd": round(label_right, 2),
            "viewBoxSlack": round(vw - label_right, 2),
        }
        if timeline_right:
            overflow = label_right - timeline_right
            g["labelOverflowUnits"] = round(overflow, 2)
            g["labelOverflowPctOfTimeline"] = round(100.0 * overflow / timeline_right, 2)
            if overflow > 0:
                report["checks"].append(
                    "WARN label overflow: 最右标签越过时间轴右边界 %.0f 单位（%.1f%% 时间轴宽），"
                    "标签悬在网格之外。缩短标签（如责任人 ≤4 字）或让时间范围右侧留出空档。"
                    % (overflow, g["labelOverflowPctOfTimeline"])
                )
        heights = Counter(r[3] for r in filled_rects(svg))
        g["modalSegmentHeight"] = heights.most_common(1)[0][0] if heights else None
        g["filledSegments"] = sum(heights.values())
        report["gantt"] = g
        report["checks"].append(
            "NOTE 条形量测: 一根进行中条形 = 状态色块(=完成比例) + 白色余量，"
            "外层 fill=\"none\" 的描边才是整条；量起止务必量外框/整条，只量色块会得出错误结论。"
        )

    if not report["checks"]:
        report["checks"].append("OK: 可读性与长宽比均在阈值内。")
    return report


def compare(a_path, b_path):
    a, b = read(a_path), read(b_path)
    avw, avh = view_box(a)
    bvw, bvh = view_box(b)
    ra, ha = bar_rects(a)
    rb, hb = bar_rects(b)
    ga = [(r[0], r[2]) for r in ra]
    gb = [(r[0], r[2]) for r in rb]
    same = Counter(ga) == Counter(gb)
    only_a = sorted((Counter(ga) - Counter(gb)).elements())
    only_b = sorted((Counter(gb) - Counter(ga)).elements())

    # 整体平移 ≠ 排期改写：画布变宽（如放大 title 字号）会把全部内容同量右移，
    # 此时宽度序列不变、x 差值恒定。必须单独识别，否则会误判成"排期被改写"。
    shift = None
    sa, sb = sorted(ga), sorted(gb)
    if not same and len(sa) == len(sb) and [w for _, w in sa] == [w for _, w in sb]:
        deltas = [b[0] - a_[0] for a_, b in zip(sa, sb)]
        if deltas and max(deltas) - min(deltas) < 1.0:
            shift = round(sum(deltas) / len(deltas), 2)

    if same:
        verdict = "两侧条形的 x/width 完全一致 → 该写法不改写排期定位（只影响版面/装饰）。"
    elif shift is not None:
        verdict = ("全部条形等量平移 %.0f 单位、宽度不变 → 排期未变，只是画布变宽/内容整体偏移；"
                   "但 aspect 与有效字号已改变，需重新量测。" % shift)
    else:
        verdict = "条形 x/width 有差异 → 该写法**改写了排期**，务必逐条核对日期。"

    out = {
        "a": a_path,
        "b": b_path,
        "viewBox": {"a": [avw, avh], "b": [bvw, bvh]},
        "barSegmentHeight": {"a": ha, "b": hb},
        "barSegmentCount": {"a": len(ga), "b": len(gb)},
        "widthDeltaPct": round(100.0 * (bvw - avw) / avw, 2) if avw else None,
        "heightDeltaPct": round(100.0 * (bvh - avh) / avh, 2) if avh else None,
        "bExtraHeightShare": round(100.0 * (bvh - avh) / bvh, 2) if bvh else None,
        "segmentGeometryIdentical": same,
        "uniformShiftUnits": shift,
        "scheduleChanged": bool(not same and shift is None),
        "segmentsOnlyInA": only_a[:12],
        "segmentsOnlyInB": only_b[:12],
        "verdict": verdict,
    }
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("svg")
    ap.add_argument("--compare", metavar="OTHER.svg", default=None,
                    help="A/B 比对另一张 SVG：条形几何是否一致、画布尺寸变化")
    ap.add_argument("--display-width", type=int, default=1400,
                    help="目标显示宽度(px)，用于折算有效字号（默认 1400）")
    ap.add_argument("--min-font-px", type=int, default=12,
                    help="可读的最小有效字号(px)，默认 12")
    args = ap.parse_args()

    if args.compare:
        result = compare(args.svg, args.compare)
    else:
        result = measure(args.svg, args.display_width, args.min_font_px)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
