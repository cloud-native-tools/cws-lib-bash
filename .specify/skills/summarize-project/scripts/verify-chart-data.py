#!/usr/bin/env python3
"""verify-chart-data.py — 甘特/里程碑图的**数据侧**校验（图元几何 ⇄ 记录层业务日期）。

职责边界（与 draw-plantuml 的 measure-svg-layout.py 分工，见 SKILL.md「脚本清单」）
--------------------------------------------------------------------------------
本脚本**只做通用绘图引擎做不了的检查**：需要**项目业务数据做真值**、必须拿记录层
（结构 B 任务日期 / 结构 C 里程碑锚定日期 / 进度百分比）与渲染出的图元几何逐条比对
的正确性校验。它回答的是「图画对了吗」——条形起止是否落在记录层日期上、里程碑菱形
是否落在锚定日上、进行中条形的结束边界是否与基准日自洽。

**通用几何量测一律委托 draw-plantuml**（`skills/draw-plantuml/scripts/measure-svg-layout.py`
「量测自检：三条几何判据」）：长宽比、正文有效字号 / 内联可读性分档、标签越过时间轴
右边界（溢出）、A/B 排期是否被改写——这些**不需要项目数据、纯几何/版面**的判据是绘图
技能的权威量测，本脚本**不再重复实现**（曾经的 C2/C3/C4/C5/C7/C8 已删除，避免两套
重复引擎并存）。渲染后请先跑 measure-svg-layout.py 过版面判据，再跑本脚本过数据侧判据。

只读一张已渲染 SVG，与记录层期望值（JSON）逐条比对，输出机器可读结论。
本脚本不修改任何文件、不调用渲染器、不写入项目目录。

用法：
    python3 verify-chart-data.py --svg <图.svg> --kind gantt     --expect <expect.json> [--json]
    python3 verify-chart-data.py --svg <图.svg> --kind milestone --expect <expect.json> [--json]

expect.json 结构（日期一律 yyyy-mm-dd，取自记录层结构 B/C）：
{
  "project_start": "2026-01-05",
  "today":         "2026-07-14",
  "bars": [
    {"name": "需求梳理", "start": "2026-01-05", "end": "2026-02-13", "percent": 100},
    {"name": "服务开发", "start": "2026-06-15", "end": "2026-07-13", "percent": 40}
  ],
  "milestones": [ {"name": "M1 联调完成", "date": "2026-07-13"} ]
}
- bars 顺序必须与源码中任务条（含阶段汇总条）的声明顺序一致；阶段汇总条也列入（percent 可省）。

退出码：0 = 全部 PASS（可含 INFO）；1 = 存在 FAIL；2 = 用法/解析错误。
"""

import argparse
import datetime
import json
import re
import sys
import pathlib

ATTR = re.compile(r'([\w:-]+)="([^"]*)"')
RECT = re.compile(r"<rect\b[^>]*/?>")
POLY = re.compile(r"<polygon\b[^>]*/?>")
VIEWBOX = re.compile(r'viewBox="0 0 ([\d.]+) ([\d.]+)"')


def attrs(s):
    return dict(ATTR.findall(s))


def fnum(d, k, default=0.0):
    try:
        return float(d.get(k, default))
    except (TypeError, ValueError):
        return default


def parse_svg(path):
    """抽取数据侧校验所需的最小几何：viewBox + 条形描边轮廓 + 里程碑菱形。

    通用版面量（字号、标签、时间轴右缘、留白）由 measure-svg-layout.py 负责，本函数
    刻意不再解析文本/today 竖带/时间轴背景带，避免与绘图引擎的量测重复。
    """
    raw = pathlib.Path(path).read_text(encoding="utf-8")
    m = VIEWBOX.search(raw)
    if not m:
        raise SystemExit("解析失败：SVG 缺少 viewBox（渲染产物可能不完整）")
    W, H = float(m.group(1)), float(m.group(2))

    bars = []
    for mm in RECT.finditer(raw):
        d = attrs(mm.group(0))
        r = dict(x=fnum(d, "x"), y=fnum(d, "y"), w=fnum(d, "width"), h=fnum(d, "height"))
        # 条形的权威几何 = 描边轮廓（fill="none"），非"已完成填充块"；排除贯穿全宽的背景列
        if d.get("fill", "") == "none" and r["w"] < W * 0.999:
            bars.append(r)

    diamonds, seen = [], set()
    for mm in POLY.finditer(raw):
        d = attrs(mm.group(0))
        nums = [float(v) for v in re.findall(r"-?[\d.]+", d.get("points", ""))]
        pts = list(zip(nums[0::2], nums[1::2]))
        if len(pts) != 4:
            continue
        xs, ys = sorted(p[0] for p in pts), sorted(p[1] for p in pts)
        # 只认菱形（里程碑）：x/y 都呈 [min, c, c, max] 形态；依赖箭头三角形不满足
        if not (xs[0] < xs[1] and abs(xs[1] - xs[2]) < 1e-6 and xs[2] < xs[3]
                and ys[0] < ys[1] and abs(ys[1] - ys[2]) < 1e-6 and ys[2] < ys[3]):
            continue
        key = (round(xs[1], 3), round(ys[1], 3))
        if key in seen:
            continue
        seen.add(key)
        diamonds.append(dict(cx=xs[1], cy=ys[1], x1=xs[3]))

    bars.sort(key=lambda r: r["y"])
    diamonds.sort(key=lambda r: r["cy"])
    return dict(W=W, H=H, bars=bars, diamonds=diamonds)


def d2n(s):
    return datetime.date.fromisoformat(s)


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, code, msg, fix=""):
        self.items.append(dict(level=level, code=code, msg=msg, fix=fix))

    ok = lambda self, c, m: self.add("PASS", c, m)
    fail = lambda self, c, m, f="": self.add("FAIL", c, m, f)
    info = lambda self, c, m, f="": self.add("INFO", c, m, f)

    @property
    def failed(self):
        return any(i["level"] == "FAIL" for i in self.items)


# ── D1 日期定位正确性（记录层日期 → SVG 条形/菱形几何逐条量算） ────────────────
# 数据侧校验：只有拿到记录层的真实日期，才能判「这根条画在了对的位置」。通用引擎
# 没有项目日期，无法做此检查——这正是本脚本存在的理由。
def check_dates(svg, exp, rep):
    bars, ebars = svg["bars"], exp.get("bars", [])
    if not ebars:
        rep.info("D1", "expect.json 未给 bars，跳过日期定位量算")
        return None
    if len(bars) != len(ebars):
        rep.fail("D1", "条形数量不符：SVG %d 条 / 记录层 %d 条" % (len(bars), len(ebars)),
                 "核对是否有条目漏画、或图集拆分后 expect.json 未同步")
        return None
    start = d2n(exp["project_start"])
    days = [(d2n(e["start"]) - start).days for e in ebars]
    spans = [(d2n(e["end"]) - d2n(e["start"])).days + 1 for e in ebars]
    xs = [b["x"] for b in bars]

    # 最小二乘拟合 x = A + W*day（W = 一天的像素宽度，与 printscale/zoom/scale 无关地自适应）
    n = len(days)
    if n < 2 or max(days) == min(days):
        rep.info("D1", "条形不足 2 个或起点相同，无法拟合时间轴比例，跳过日期定位量算")
        return None
    md, mx = sum(days) / n, sum(xs) / n
    num = sum((days[i] - md) * (xs[i] - mx) for i in range(n))
    den = sum((days[i] - md) ** 2 for i in range(n))
    Wd = num / den
    A = mx - Wd * md
    if Wd <= 0:
        rep.fail("D1", "时间轴比例拟合异常（W=%.2f ≤ 0）" % Wd,
                 "确认 expect.json 的 bars 顺序与源码声明顺序一致")
        return None
    inset = sum((spans[i] * Wd - bars[i]["w"]) for i in range(n)) / n

    bad = []
    for i, e in enumerate(ebars):
        res_start = (xs[i] - (A + Wd * days[i])) / Wd
        res_span = ((spans[i] * Wd - inset) - bars[i]["w"]) / Wd
        if abs(res_start) > 0.5 or abs(res_span) > 0.5:
            bad.append((e.get("name", "#%d" % i), res_start, res_span, bars[i]["w"], spans[i] * Wd - inset))
    rep.info("D1", "时间轴比例 W=%.2f px/天，条形内缩 %.1f px（拟合自 %d 条）" % (Wd, inset, n))
    if bad:
        for name, rs, rp, aw, ew in bad:
            rep.fail("D1", "「%s」起点偏移 %+.2f 天、条宽偏差 %+.2f 天（实测宽 %.0f / 应为 %.0f）"
                     % (name, rs, rp, aw, ew),
                     "对照记录层日期修正源码；若源码正确则说明渲染器改写了排期（检查资源均衡、前向引用、closed 日）")
    else:
        rep.ok("D1", "全部 %d 条条形起点与条宽与记录层日期一致（残差 < 0.5 天）" % n)

    # 里程碑菱形定位：位置是否等于记录层锚定日期（同样是数据侧、通用引擎做不了）
    emil = exp.get("milestones", [])
    dm = svg["diamonds"]
    if emil and len(dm) == len(emil):
        for e, dd in zip(emil, dm):
            want = A + Wd * ((d2n(e["date"]) - start).days) + Wd / 2
            res = (dd["cx"] - want) / Wd
            if abs(res) > 0.7:
                rep.fail("D1", "里程碑「%s」定位偏移 %+.2f 天" % (e["name"], res), "核对 happens 锚定与换算日期")
        rep.ok("D1", "%d 个里程碑菱形定位与记录层锚定日期一致" % len(emil))
    elif emil:
        rep.fail("D1", "里程碑数量不符：SVG %d 个 / 记录层 %d 个" % (len(dm), len(emil)),
                 "核对 happens 条目是否被逐条复制")
    return dict(W=Wd, A=A, inset=inset)


# ── D2 进行中条形的结束边界与进度前沿（相对基准日的业务自洽） ──────────────────
# 数据侧校验：需要记录层的 percent 与 end 日期 + 基准日，才能判「进行中条是否读作
# 已逾期」「进度前沿领先/落后基准日几天」。纯几何引擎没有这些业务真值。
def check_progress(svg, exp, rep, geo):
    if not geo or not exp.get("today"):
        return
    W_, A = geo["W"], geo["A"]
    start, today = d2n(exp["project_start"]), d2n(exp["today"])
    tday = (today - start).days
    for i, e in enumerate(exp.get("bars", [])):
        p = e.get("percent")
        if p is None or p in (0, 100):
            continue
        if d2n(e["end"]) < today:
            rep.fail("D2", "进行中条目「%s」结束日期 %s 早于基准日 %s：条形止于 today 线左侧，读者读作"
                     "「已逾期且无计划」" % (e["name"], e["end"], exp["today"]),
                     "记录层为该条目补一个 ≥ 基准日的计划结束日（可标 `（推断）`）并在元信息登记假设")
            continue
        b = svg["bars"][i]
        front = b["x"] + b["w"] * (p / 100.0)
        drift = (front - (A + W_ * tday)) / W_
        rep.info("D2", "「%s」进度前沿距基准日 %+.1f 天（%s）"
                 % (e["name"], drift, "领先" if drift >= 0 else "落后"),
                 "把该结论写进图说第三要素，勿只贴图")


def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.splitlines()[0])
    ap.add_argument("--svg", required=True)
    ap.add_argument("--kind", default="gantt", choices=["gantt", "milestone", "wbs", "mindmap"])
    ap.add_argument("--expect")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    svg = parse_svg(a.svg)
    rep = Report()

    if a.kind in ("wbs", "mindmap"):
        rep.info("D0", "%s 图无时间轴/记录层日期真值，本脚本无数据侧检查项；"
                 "版面/可读性判据请跑 draw-plantuml 的 measure-svg-layout.py" % a.kind)
    elif not a.expect:
        rep.info("D0", "未提供 --expect（记录层期望值 JSON），无法做数据侧校验；"
                 "仅版面判据时请改跑 measure-svg-layout.py")
    else:
        exp = json.loads(pathlib.Path(a.expect).read_text(encoding="utf-8"))
        geo = check_dates(svg, exp, rep)
        check_progress(svg, exp, rep, geo)

    if a.json:
        print(json.dumps(dict(svg=a.svg, kind=a.kind, viewBox=[svg["W"], svg["H"]],
                              failed=rep.failed, items=rep.items), ensure_ascii=False, indent=2))
    else:
        print("=== 数据侧校验：%s (%s) viewBox %.0f×%.0f ===" % (a.svg, a.kind, svg["W"], svg["H"]))
        print("（通用版面量测委托 draw-plantuml/measure-svg-layout.py，本脚本只比对图元几何 ⇄ 记录层日期）")
        for i in rep.items:
            print("[%s] %s %s" % (i["level"], i["code"], i["msg"]))
            if i["fix"]:
                print("        → %s" % i["fix"])
        print("=== 结论：%s ===" % ("存在 FAIL，图元与记录层日期不符" if rep.failed else "全部通过"))
    return 1 if rep.failed else 0


if __name__ == "__main__":
    sys.exit(main())
