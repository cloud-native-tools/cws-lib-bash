#!/usr/bin/env python3
"""progress-engine.py — 日期与进度的**唯一计算引擎**（summarize-project）。

定位
----
报告的 Markdown 文档**不承载任何日期/进度计算逻辑**：不比较两个日期的先后、不算天数差、
不判定延期、不算百分比、不做聚合平均。这些全部在本脚本内完成，Markdown 只**调用本脚本
并引用输出字段**（`status` / `schedule_status` / `delay_days` / `progress_pct` /
`progress_formula` / `gantt.today_offset_days` …）。

输入 = **SQLite 关系模型**（`data/project.db`，DDL 见 `schema/project.sql`）
----------------------------------------------------------------------
项目关键信息以关系模型建模：字段定义、取值域与实体关联由**数据库约束**保证（DDL 是字段
定义的权威，业务含义见 `references/required-info.md`）。本引擎**从数据库读取**，并**用 SQL
完成查询与聚合**——取数（多表 JOIN、行序）、日期天数差（`julianday`）、阶段与项目级聚合
（`GROUP BY`）、里程碑锚定解析与达成计数、时间轴排序（`ORDER BY`）都在 SQL 里做，Python
只把 SQL 结果落成输出字段与说明文本。

    python3 project-db.py --load data/project-input.yaml     # 表单 → SQLite（约束即校验）
    python3 progress-engine.py --db data/project.db --summary

实体与字段名与必要信息表逐字一致——`project` / `phases` / `work_items` / `milestones` /
`people` / `features` / `sources`，字段名即列名、也是实体间的外键（`phase_id` /
`owner_id` / `anchor_item_id` / `work_item_deps`）。

**向后兼容（不删任何字段）**：同结构的 JSON（`project-input/v1`，由
`project-db.py --export-json` 导出）与旧形态的扁平 `items[]`（`progress-engine/v1`）
仍被 `--input` 完整接受；同一份数据经 `--db` 与经 `--input` 必得同一份输出（除
`input` / `input_schema` 两个标签字段）。

数据库是**派生物**：落交付目录 `data/project.db`，默认每次运行由表单重建（用户需要基于
历史库演进时用 `project-db.py --update`）；**绝不写入被总结的目标项目的管理工件**。

基准日 D0 来自 `--baseline yyyy-mm-dd` 或库中 `project.baseline_date`（两者都给时以
`--baseline` 为准）—— 引擎**不读系统时钟**，保证同一份输入 + 同一基准日永远得到同一份
输出（可复现、可复核）。

关键诚实性约定
--------------
* **无计划完成日 ⇒ 无法判定延期**：`schedule_status = "unknown-schedule"`、
  `delay_days = null`，并在 `diagnostics.declarations` 给出可直接引用的声明句
  「无计划日期，无法判定延期」。**绝不**用 git 日期等推断基线硬判延期，也不据此上红色。
* **无可计数依据 ⇒ 进度为空**：`progress_pct = null` + `progress_basis = null`，
  由报告落成合法终态 `-（无可计数依据）`；引擎不编造任何百分比。
* **未映射状态 ⇒ unknown**：不猜三态；未映射字面量在 `diagnostics.unmapped_statuses`
  逐条列出（`--strict` 下直接报错退出）。
* **字段缺失 / 非法日期 / 外键断裂 ⇒ 报错退出（码 2）**，不静默跳过。

用法
----
    python3 progress-engine.py --db data/project.db --baseline 2026-04-06
    python3 progress-engine.py --db data/project.db                 # 基准日取库中 project.baseline_date
    python3 progress-engine.py --db data/project.db --out engine-out.json --summary
    python3 progress-engine.py --input data/progress-data.json      # 向后兼容：同结构 JSON
    python3 progress-engine.py --print-schema      # 打印字段契约与最小示例

退出码：0 成功；2 输入错误（缺字段 / 非法日期 / 悬空外键 / 重号 / 缺库 / --strict 未映射状态）。
本脚本只读输入（数据库以只读方式取数，除 `temp.` 临时表外不改任何持久化表），除 `--out`
指定的输出文件外不写任何文件。
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import pathlib
import re
import sqlite3
import sys

ENGINE_ID = "progress-engine/v1"
CANONICAL_SCHEMA = "project-input/v1"

# ── 输入 schema（--print-schema 打印本段 + 示例） ────────────────────────────────
SCHEMA_DOC = """\
项目关键信息的字段契约 —— 关系模型（project-db/v1）与其等价的 YAML/JSON 输入面（project-input/v1）
================================================================================
**字段类型、取值域、实体关联的可执行权威 = `schema/project.sql`（DDL，由数据库约束强制）**；
业务含义与三档必填性 R/I/O 见 `references/required-info.md`。下面描述的是同一个关系模型
的 YAML/JSON 形态（人工可写的输入面），由 `scripts/project-db.py --load` 装载进数据库，
**装载即校验**；本引擎从数据库读取（`--db`），也接受该 JSON 形态（`--input`，向后兼容）。
档位：R 必填-阻断 ｜ I 可推断（须带 inferred/inferred_from）｜ O 可选（缺失显式降级）。

顶层对象：
  schema        选填  固定 "project-input/v1"（写了则校验）
  project       必填  见下
  phases        选填  阶段数组（缺省 = 工作项不分阶段）
  work_items    条件  与 milestones 至少一组非空
  milestones    条件  与 work_items 至少一组非空
  people        选填  人员/负责人数组
  features      选填  特性数组（《需求与特性》章节）
  sources       选填  来源声明数组（管理系统导出 / 用户填写 / 上下文 / repo）
  coverage      选填  {candidate_total, excluded, granularity_truncated, source_label,
                      unattributed}；分解树覆盖闭合等式由引擎验算
  status_map    选填  {"<源状态字面量>": "<四态>"}；覆盖/扩展内置映射表（项目宪章优先）
  git_window    选填  {commit_count, first_commit, last_commit}；**仅在表单声明了
                      project.repos[] 的 opt-in 情形下才有意义**，只用于判定"排期材料是否
                      过弱"，不作任何任务级排期依据
  inferred_fields 选填 推断字段清单 [{field, inferred_value, inferred_from}]（原样透传到输出，
                      供报告 `## 元信息` 汇总"推断字段清单"）

project：
  project_name   [R] 项目对外名称
  project_desc   [O] 一句话定位
  baseline_date  [R] 基准日 D0（yyyy-mm-dd）；--baseline 未给时取此值（引擎不读系统时钟）
  project_start  [O] 项目起点（甘特时间轴起点）；缺省时引擎取全部日期中最早者并标推断起点
  repos          [O] repo 取材是**完全 opt-in** 的补充源：[{repo_id, repo_path, repo_role,
                     derive_fields[]}]；不声明 = 不做任何 repo 取材

phases[]：      phase_id [I]（被 work_items.phase_id 引用）｜ phase_name [I] ｜ phase_order [I]

work_items[]：
  item_id        [I] 全局唯一（被 depends_on / anchor_item_id 引用；缺省由校验脚本生成）
  item_name      [R] 业务语言名称
  phase_id       [I] 外键 → phases.phase_id（缺省 = 挂在分解树顶层）
  owner_id       [O] 外键 → people.owner_id
  planned_start / planned_end / actual_start / actual_end  [O] yyyy-mm-dd
                 （planned_end 缺失 ⇒ unknown-schedule：不判延期、不上红）
  status         [I] 源状态字面量（归一化由引擎执行；未映射 → unknown）
  progress_pct   [O] 材料明写的百分比（0–100），须同时给 progress_source
  checks         [O] 勾选计数 {done, open, deferred, excluded}（可计数依据）
  depends_on     [I] 外键数组 → work_items.item_id（无材料依据则不填，不虚构依赖）
  weight         [O] 材料明确给出的权重，须同时给 weight_source
  risk_note      [O] 材料明写的风险/延期信号
  source         [I] 溯源出处（缺省由 sources[] 推断）

milestones[]：
  milestone_id   [I] 全局唯一 ｜ milestone_name [R]
  planned_date   [O] 锚定日；与 anchor_item_id 二者皆缺 ⇒ unknown-schedule（不判逾期）
  actual_date    [O] 达成日 ｜ achieved_evidence [O] 达成依据（有值即视为已达成）
  status         [I] 由引擎判定（achieved / pending / at-risk / unknown-schedule）
  anchor_item_id [O] 外键 → work_items.item_id（引擎按其 planned_end 换算锚定日）
  owner_id       [O] 外键 → people.owner_id ｜ source [I]

people[]：      owner_id [O]（被 owner_id 外键引用）｜ owner_name [O] ｜ owner_role [I]
features[]：    feature_id [I] ｜ feature_name [R] ｜ status [I] ｜ owner_id [O] ｜ source [I]
sources[]：     source_id [I] ｜ source_kind [I]（management-export|user-form|context|repo）
                ｜ source_ref [I] ｜ covers[] [O]

日期字段一律接受 yyyy-mm-dd；同时容忍并**归一化** yyyy/m/d、yyyy.m.d、yyyy年m月d日、
yyyy-mm（补当月首日并标 inferred=true, precision=month）。无法判定的歧义写法（如
02/03/2026）→ 报错，不猜。所有 `*_id` 全局唯一；外键指向未声明实体 → 报错退出。

向后兼容
--------
旧形态的扁平 `items[]`（schema "progress-engine/v1"：`id`/`name`/`type`/`parent`/
`status_raw`/`planned_end`/`anchor_item`/`source` …）仍被完整接受、字段未删；两种形态
不得混写（同时出现 items[] 与 work_items[] → 报错）。
"""

EXAMPLE_INPUT = {
    "schema": CANONICAL_SCHEMA,
    "project": {
        "project_name": "示例平台 v2.0",
        "project_desc": "把三套收单链路合并为一套统一网关",
        "baseline_date": "2026-04-06",
        "project_start": "2026-03-02",
        "repos": [],
    },
    "phases": [
        {"phase_id": "P-01", "phase_name": "需求与设计", "phase_order": 1},
    ],
    "work_items": [
        {
            "item_id": "T-01", "item_name": "需求调研", "phase_id": "P-01",
            "owner_id": "U-01", "status": "[X]",
            "planned_start": "2026-03-02", "planned_end": "2026-03-09",
            "actual_end": "2026-03-09", "source": "PMO 导出#Sheet1!A12",
        },
        {
            "item_id": "T-02", "item_name": "架构设计", "phase_id": "P-01",
            "owner_id": "U-01", "status": "Implemented",
            "checks": {"done": 22, "open": 4, "deferred": 1},
            "planned_start": "2026-03-10", "planned_end": "2026-04-03",
            "depends_on": ["T-01"], "source": "PMO 导出#Sheet1!A13",
        },
    ],
    "milestones": [
        {
            "milestone_id": "M-01", "milestone_name": "需求冻结",
            "planned_date": "2026-03-09", "actual_date": "2026-03-09",
            "achieved_evidence": "评审通过记录 2026-03-09", "owner_id": "U-01",
            "source": "PMO 里程碑表#L3",
        },
        {
            "milestone_id": "M-02", "milestone_name": "联调完成",
            "anchor_item_id": "T-02", "owner_id": "U-02", "source": "路线图#Q1",
        },
        {
            "milestone_id": "M-03", "milestone_name": "正式发布",
            "source": "路线图#Q2（无计划日期）",
        },
    ],
    "people": [
        {"owner_id": "U-01", "owner_name": "张三", "owner_role": "开发负责人"},
        {"owner_id": "U-02", "owner_name": "李四", "owner_role": "未记录"},
    ],
    "features": [
        {"feature_id": "F-01", "feature_name": "统一收单", "status": "Implemented",
         "source": "需求文档#2.1"},
    ],
    "sources": [
        {"source_id": "S-01", "source_kind": "management-export",
         "source_ref": "PMO 周报导出 2026-04-06.xlsx",
         "covers": ["work_items", "milestones"]},
    ],
}

# ── 状态映射（内置默认；可被输入的 status_map 覆盖） ─────────────────────────────
# 权威语义见 references/consistency-rules.md §1（生命周期口径）；本表是其可执行形态。
DEFAULT_STATUS_MAP = {
    # 一种常见 SDD 框架的特性生命周期（**默认值，非通用事实**；目标项目定义不同时用 status_map 覆盖）
    "draft": "not-started",
    "planned": "not-started",          # 已排期 ≠ 已开工
    "implemented": "in-progress",      # 已交付代码、生命周期未闭合
    "ready for review": "in-progress",
    "completed": "completed",
    "deferred": "deferred",
    # 任务勾选标记
    "[x]": "completed",                # 大小写在归一化时统一
    "[ ]": "not-started",
    "[]": "not-started",
    "[~]": "deferred",
    # 常见外部看板字面量
    "done": "completed",
    "closed": "completed",
    "resolved": "completed",
    "已上线": "completed",
    "已完成": "completed",
    "完成": "completed",
    "已验收": "completed",
    "已交付": "completed",
    "in progress": "in-progress",
    "doing": "in-progress",
    "in review": "in-progress",
    "开发中": "in-progress",
    "进行中": "in-progress",
    "实施中": "in-progress",
    "blocked": "in-progress",
    "on hold": "in-progress",
    "挂起": "in-progress",
    "to do": "not-started",
    "todo": "not-started",
    "backlog": "not-started",
    "open": "not-started",
    "待开始": "not-started",
    "未开始": "not-started",
    "未启动": "not-started",
    "暂缓": "deferred",
    "本轮延后": "deferred",
}
TASK_STATES = ("completed", "in-progress", "not-started", "deferred", "unknown")
AGGREGATABLE = ("completed", "in-progress", "not-started")
MILESTONE_TYPES = ("milestone",)
VALID_TYPES = ("work-item", "phase", "feature", "milestone")

DATE_FIELDS = ("planned_start", "planned_end", "actual_start", "actual_end")
DATE_ALIASES = {"planned_date": "planned_end", "actual_date": "actual_end"}

# ── 可配置阈值（**唯一存放处**；文档一律只引用输出字段，不复述这些数字） ─────────────
# 可移植性纪律（references/portability.md §1.1、§2）：阈值是"在多个项目上取的折中默认值"，
# 不是任何单一项目的实测事实。需要按项目调整时改这里（或在调用方包一层），
# **不要**把数字抄进 Markdown、也不要在文档/报告里拿它做比较。
# 每次运行的实际取值随输出的 `thresholds` 块一并落盘，便于复核与复现。
#
# 排期材料"过弱"的判定下限（degradation.md 第 5 节只读 weak_git_material / reason）
WEAK_GIT_COMMITS = 10
WEAK_GIT_SPAN_DAYS = 7
# 里程碑视图独立成图的日期侧条件（milestones.md 独立成图判定 (a) 只读 standalone_condition_a）
MS_VIEW_MIN_COUNT = 4
MS_VIEW_MIN_SPAN_DAYS = 61          # "≥2 个月"的可执行化：首末跨度 ≥61 天
# 甘特图集拆分建议阈值（reporting-playbook.md 第 4 节只读 split_recommended）
GANTT_SPLIT_BARS = 20


class EngineError(Exception):
    """输入不合法：缺字段 / 非法日期 / 悬空引用 / 重号。一律报错退出，不静默降级。"""


# ── 日期归一化（唯一实现处；Markdown 不重述任何转换规则） ────────────────────────
_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_SLASH = re.compile(r"^(\d{4})[/.](\d{1,2})[/.](\d{1,2})$")
_CJK = re.compile(r"^(\d{4})年(\d{1,2})月(\d{1,2})日$")
_MONTH = re.compile(r"^(\d{4})-(\d{1,2})$|^(\d{4})年(\d{1,2})月$")
_AMBIGUOUS = re.compile(r"^\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}$")


def normalize_date(raw, where: str):
    """把材料日期归一化为 (iso, precision, inferred)。非法/歧义 → EngineError。

    `inferred=True` **只**用于"日被引擎补出来"的情形（材料仅给到月精度）；单纯的格式
    转写（`2026/7/28`、`2026年7月28日` → `2026-07-28`）不是推断，不打 `（推断）`。
    """
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        raise EngineError("%s 的日期必须是字符串，收到 %r" % (where, raw))
    text = raw.strip().replace("（推断）", "").replace("(推断)", "").strip()
    if not text:
        return None
    for pattern in (_ISO, _SLASH, _CJK):
        m = pattern.match(text)
        if m:
            y, mo, d = (int(g) for g in m.groups())
            return (_mkdate(y, mo, d, where, text).isoformat(), "day", False)
    m = _MONTH.match(text)
    if m:
        groups = [g for g in m.groups() if g is not None]
        y, mo = int(groups[0]), int(groups[1])
        return (_mkdate(y, mo, 1, where, text).isoformat(), "month", True)
    if _AMBIGUOUS.match(text):
        raise EngineError(
            "%s 的日期 %r 月/日次序有歧义 → 采集阶段须先按材料内无歧义日期确定格式后再落入"
            "进度数据文件；引擎不猜" % (where, raw)
        )
    raise EngineError("%s 的日期 %r 无法识别（期望 yyyy-mm-dd）" % (where, raw))


def _mkdate(y: int, mo: int, d: int, where: str, text: str) -> datetime.date:
    try:
        return datetime.date(y, mo, d)
    except ValueError as exc:
        raise EngineError("%s 的日期 %r 不是合法日历日：%s" % (where, text, exc))


def d(iso):
    return datetime.date.fromisoformat(iso) if iso else None


def days_between(later_iso: str, earlier_iso: str) -> int:
    """两个日期之间的整数天差（唯一实现处）。"""
    return (d(later_iso) - d(earlier_iso)).days


# ── 输入解析与校验 ──────────────────────────────────────────────────────────────
def load_input(path: str) -> dict:
    try:
        raw = sys.stdin.read() if path == "-" else pathlib.Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise EngineError("无法读取输入文件 %s：%s" % (path, exc))
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise EngineError("输入文件不是合法 JSON：%s" % exc)
    if not isinstance(data, dict):
        raise EngineError("输入文件顶层必须是对象（规范形态含 project + work_items/milestones）")
    declared = data.get("schema")
    if declared and declared not in (CANONICAL_SCHEMA, ENGINE_ID):
        raise EngineError(
            "schema 不匹配：文件声明 %r，本引擎接受 %r（规范形态）或 %r（旧形态）"
            % (declared, CANONICAL_SCHEMA, ENGINE_ID))
    canonical_groups = [g for g in ("work_items", "milestones", "phases", "features", "people")
                        if g in data]
    if "items" in data and canonical_groups:
        raise EngineError(
            "输入同时出现旧形态 items[] 与规范形态 %s → 两种形态不得混写，请统一为规范字段名"
            % "/".join(canonical_groups))
    if "items" in data:
        return normalize_legacy(data)
    return normalize_canonical(data)


def normalize_legacy(data: dict) -> dict:
    """旧形态（progress-engine/v1 扁平 items[]）—— 向后兼容，字段不删。"""
    if not isinstance(data.get("items"), list) or not data["items"]:
        raise EngineError("旧形态输入缺少非空的 items 数组")
    out = dict(data)
    out["input_schema"] = ENGINE_ID
    out.setdefault("people_roster", {})
    out.setdefault("sources", [])
    out.setdefault("inferred_fields", [])
    project = data.get("project") or {}
    out["project"] = dict(project)
    out["baseline_date"] = project.get("baseline_date")
    return out


def _text(value):
    return None if value is None or str(value).strip() == "" else str(value).strip()


def normalize_canonical(data: dict) -> dict:
    """规范形态（project-input/v1）→ 引擎内部 items[]；字段名映射集中在此一处。"""
    project = data.get("project")
    if project is None:
        project = {}
    if not isinstance(project, dict):
        raise EngineError("project 必须是对象（含 project_name / baseline_date）")
    if not _text(project.get("project_name")):
        raise EngineError("project.project_name 缺失（必填-阻断档）—— 先补齐表单再运行引擎")

    groups = {}
    for group in ("phases", "work_items", "milestones", "people", "features", "sources"):
        rows = data.get(group) or []
        if not isinstance(rows, list):
            raise EngineError("%s 必须是数组" % group)
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                raise EngineError("%s[%d] 必须是对象（键 = 规范字段名）" % (group, i))
        groups[group] = rows
    if not groups["work_items"] and not groups["milestones"]:
        raise EngineError(
            "work_items[] 与 milestones[] 皆为空（组级必填-阻断档）—— 至少一组非空才能出报告")

    roster = {}
    for i, row in enumerate(groups["people"]):
        oid = _text(row.get("owner_id")) or "U-%02d" % (i + 1)
        roster[oid] = {"owner_id": oid,
                       "owner_name": _text(row.get("owner_name")) or oid,
                       "owner_role": _text(row.get("owner_role")) or "未记录"}

    default_source = "project-input（表单填写）"
    for src in groups["sources"]:
        ref = _text(src.get("source_ref"))
        if ref and _text(src.get("source_kind")) != "repo":
            default_source = "%s（%s）" % (ref, _text(src.get("source_kind")) or "user-form")
            break

    def source_of(group: str, row: dict) -> str:
        explicit = _text(row.get("source"))
        if explicit:
            return explicit
        for src in groups["sources"]:
            if group in (src.get("covers") or []):
                return "%s（%s）" % (_text(src.get("source_ref")) or default_source,
                                    _text(src.get("source_kind")) or "user-form")
        return default_source

    items, work_ids = [], set()
    for i, row in enumerate(groups["phases"]):
        pid = _text(row.get("phase_id")) or "P-%02d" % (i + 1)
        items.append({
            "id": pid, "type": "phase",
            "name": _text(row.get("phase_name")) or pid,
            "phase_order": row.get("phase_order"),
            "source": source_of("phases", row),
        })
    for i, row in enumerate(groups["work_items"]):
        iid = _text(row.get("item_id")) or "T-%02d" % (i + 1)
        work_ids.add(iid)
        name = _text(row.get("item_name"))
        if not name:
            raise EngineError("work_items[%d].item_name 缺失（必填-阻断档）" % i)
        item = {
            "id": iid, "type": "work-item", "name": name,
            "parent": _text(row.get("phase_id")),
            "phase_id": _text(row.get("phase_id")),
            "owner_id": _text(row.get("owner_id")),
            "status_raw": row.get("status"),
            "checks": row.get("checks"),
            "progress_pct": row.get("progress_pct"),
            "progress_source": row.get("progress_source"),
            "weight": row.get("weight"),
            "weight_source": row.get("weight_source"),
            "risk_note": row.get("risk_note"),
            "depends_on": [d for d in _as_list(row.get("depends_on")) if _text(d)],
            "source": source_of("work_items", row),
        }
        for field in DATE_FIELDS:
            if row.get(field) is not None:
                item[field] = row.get(field)
        items.append(item)
    for i, row in enumerate(groups["milestones"]):
        mid = _text(row.get("milestone_id")) or "M-%02d" % (i + 1)
        name = _text(row.get("milestone_name"))
        if not name:
            raise EngineError("milestones[%d].milestone_name 缺失（必填-阻断档）" % i)
        items.append({
            "id": mid, "type": "milestone", "name": name,
            "owner_id": _text(row.get("owner_id")),
            "status_raw": row.get("status"),
            "planned_end": row.get("planned_date") or row.get("planned_end"),
            "actual_end": row.get("actual_date") or row.get("actual_end"),
            "achieved_evidence": row.get("achieved_evidence"),
            "risk_note": row.get("risk_note"),
            "anchor_item": _text(row.get("anchor_item_id")),
            "source": source_of("milestones", row),
        })
    for i, row in enumerate(groups["features"]):
        fid = _text(row.get("feature_id")) or "F-%02d" % (i + 1)
        name = _text(row.get("feature_name"))
        if not name:
            raise EngineError("features[%d].feature_name 缺失（必填-阻断档）" % i)
        items.append({
            "id": fid, "type": "feature", "name": name,
            "owner_id": _text(row.get("owner_id")),
            "status_raw": row.get("status"),
            "source": source_of("features", row),
        })

    for item in items:
        for dep in item.get("depends_on") or []:
            dep = str(dep).strip()
            if dep not in work_ids:
                raise EngineError(
                    "work_items %s 的 depends_on 指向未声明的 item_id %r（外键断裂）"
                    % (item["id"], dep))
            if dep == item["id"]:
                raise EngineError("work_items %s 的 depends_on 指向自身" % item["id"])
    for item in items:
        oid = item.get("owner_id")
        if oid and roster and oid not in roster:
            raise EngineError("条目 %s 的 owner_id=%r 不存在于 people[]（外键断裂）"
                              % (item["id"], oid))

    out = {
        "schema": CANONICAL_SCHEMA,
        "input_schema": CANONICAL_SCHEMA,
        "project": {
            "name": _text(project.get("project_name")),
            "desc": _text(project.get("project_desc")),
            "start": project.get("project_start") or project.get("start"),
            "repos": project.get("repos") or [],
        },
        "baseline_date": _text(project.get("baseline_date")),
        "items": items,
        "people_roster": roster,
        "sources": groups["sources"],
        "inferred_fields": data.get("inferred_fields") or [],
    }
    for key in ("status_map", "git_window", "coverage"):
        if data.get(key):
            out[key] = data[key]
    return out


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


DB_SCHEMA_VERSION = "project-db/v1"


def _project_db_module():
    """惰性加载同目录的 project-db.py（文件名带连字符，只能按路径加载）。

    取数（多表 JOIN、行序、依赖联结表展开）的 SQL 只有一份实现，就在 project-db.py 的
    `export_json` 里；本引擎复用它，不再复制一遍 SQL。
    """
    path = pathlib.Path(__file__).resolve().parent / "project-db.py"
    if not path.exists():
        raise EngineError("找不到 %s —— 数据库取数层缺失，无法用 --db 读取" % path)
    name = "_speckit_project_db"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)                        # type: ignore[union-attr]
    return module


def load_from_db(path: str):
    """从 SQLite 关系模型读取（取数全走 SQL），返回 (引擎内部 data, SqlFacts)。"""
    p = pathlib.Path(path)
    if not p.exists():
        raise EngineError("数据库不存在：%s（先跑 project-db.py --load <表单>）" % path)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    # SQLite 默认关闭外键强制，且是连接级设置 —— 取数连接同样显式开启，保证读到的
    # 关联是被约束过的数据
    conn.execute("PRAGMA foreign_keys = ON")
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise EngineError("无法启用 PRAGMA foreign_keys —— 外键约束会退化为注释，拒绝继续")
    try:
        version = conn.execute(
            "SELECT meta_value FROM schema_meta WHERE meta_key = 'schema_version'").fetchone()
    except sqlite3.Error as exc:
        raise EngineError("%s 不是本技能的项目库（缺 schema_meta 表）：%s" % (path, exc))
    if version and version[0] != DB_SCHEMA_VERSION:
        raise EngineError("数据库 schema 版本不匹配：库中 %r，本引擎为 %r（重新 --load 建库）"
                          % (version[0], DB_SCHEMA_VERSION))
    module = _project_db_module()
    try:
        payload = module.export_json(conn)
    except Exception as exc:                              # noqa: BLE001 - 归为输入错误
        raise EngineError("从数据库取数失败：%s" % exc)
    data = normalize_canonical(payload)
    data["db_schema_version"] = DB_SCHEMA_VERSION
    return data, SqlFacts(conn)


class SqlFacts:
    """SQL 计算层：日期天数差与一切集合级聚合都在数据库里做。

    * **天数差**：`diff()` 用 SQL `julianday` 相减 —— 引擎在 `--db` 路径下不做 Python
      日期减法（`--input` JSON 路径退回 `days_between`，两条路径结果一致，可 diff 自证）。
    * **聚合**：把逐条目算出的记录写进 `temp.item_facts` 临时表，父项/阶段聚合、项目级
      计数与分桶、里程碑达成、时间轴排序全部用 `GROUP BY` / `ORDER BY` 在 SQL 中完成。
      临时表只存在于本连接，**不改任何持久化表**。
    """

    ITEM_FACTS_DDL = """
        CREATE TEMP TABLE item_facts (
            seq             INTEGER PRIMARY KEY,
            id              TEXT NOT NULL,
            name            TEXT,
            type            TEXT,
            parent          TEXT,
            owner_id        TEXT,
            status          TEXT,
            progress_pct    REAL,
            progress_basis  TEXT,
            weight          REAL,
            planned_start   TEXT,
            planned_end     TEXT,
            actual_start    TEXT,
            actual_end      TEXT,
            schedule_status TEXT,
            delay_days      INTEGER,
            anchor_date     TEXT,
            has_children    INTEGER,
            dates_derived   INTEGER
        )
    """
    FACT_COLUMNS = ("id", "name", "type", "parent", "owner_id", "status", "progress_pct",
                    "progress_basis", "weight", "planned_start", "planned_end",
                    "actual_start", "actual_end", "schedule_status", "delay_days",
                    "anchor_date", "has_children", "dates_derived")

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.bound = False

    # ── 日期算术（唯一实现处：SQL julianday） ──────────────────────────────────
    def diff(self, later_iso: str, earlier_iso: str) -> int:
        row = self.conn.execute(
            "SELECT CAST(julianday(:later) - julianday(:earlier) AS INTEGER)",
            {"later": later_iso, "earlier": earlier_iso}).fetchone()
        if row is None or row[0] is None:
            raise EngineError("SQL 无法计算 %r 与 %r 的天数差（日期非法）"
                              % (later_iso, earlier_iso))
        return int(row[0])

    # ── 绑定逐条目记录到临时表（此后所有聚合都是 SQL） ─────────────────────────
    def bind(self, items: list, computed: dict) -> None:
        self.conn.execute("DROP TABLE IF EXISTS temp.item_facts")
        self.conn.execute(self.ITEM_FACTS_DDL)
        rows = []
        for seq, it in enumerate(items, start=1):
            rec = computed[it["id"]]
            rows.append([seq] + [self._fact_value(rec, col) for col in self.FACT_COLUMNS])
        self.conn.executemany(
            "INSERT INTO temp.item_facts (seq, %s) VALUES (%s)"
            % (", ".join(self.FACT_COLUMNS),
               ", ".join("?" for _ in range(len(self.FACT_COLUMNS) + 1))), rows)
        self.bound = True

    @staticmethod
    def _fact_value(rec: dict, col: str):
        if col == "has_children":
            return 1 if rec.get("children") else 0
        if col == "dates_derived":
            return 1 if rec.get("dates_derived") else 0
        return rec.get(col)

    def sync(self, rec: dict) -> None:
        """父项聚合后把新值写回临时表，供后续（更高层父项、项目级）SQL 聚合看到。"""
        if not self.bound:
            return
        cols = [c for c in self.FACT_COLUMNS if c != "id"]
        self.conn.execute(
            "UPDATE temp.item_facts SET %s WHERE id = ?"
            % ", ".join("%s = ?" % c for c in cols),
            [self._fact_value(rec, c) for c in cols] + [rec["id"]])

    # ── 父项 / 阶段聚合（SQL GROUP BY） ────────────────────────────────────────
    def child_stats(self, parent_id: str) -> dict:
        row = self.conn.execute("""
            SELECT count(*)                                                     AS children,
                   sum(CASE WHEN status IN ('completed','in-progress','not-started')
                            THEN 1 ELSE 0 END)                                  AS participating,
                   sum(CASE WHEN status = 'completed' THEN 1 ELSE 0 END)         AS completed,
                   sum(CASE WHEN status = 'not-started' THEN 1 ELSE 0 END)       AS not_started,
                   sum(CASE WHEN progress_pct IS NOT NULL THEN 1 ELSE 0 END)     AS counted,
                   sum(CASE WHEN progress_pct IS NULL THEN 1 ELSE 0 END)         AS excluded,
                   sum(progress_pct)                                            AS pct_sum,
                   sum(CASE WHEN progress_pct IS NOT NULL AND weight IS NOT NULL
                            THEN 1 ELSE 0 END)                                  AS weighted,
                   sum(CASE WHEN progress_pct IS NOT NULL THEN progress_pct * weight END)
                                                                                AS weighted_sum,
                   sum(CASE WHEN progress_pct IS NOT NULL THEN weight END)       AS weight_sum,
                   min(planned_start)                                           AS planned_start_min,
                   max(planned_end)                                             AS planned_end_max,
                   max(actual_end)                                              AS actual_end_max,
                   sum(CASE WHEN actual_end IS NOT NULL THEN 1 ELSE 0 END)       AS actual_end_count
              FROM temp.item_facts WHERE parent = :pid
        """, {"pid": parent_id}).fetchone()
        stats = dict(row)
        stats["excluded_ids"] = [r[0] for r in self.conn.execute(
            "SELECT id FROM temp.item_facts WHERE parent = :pid AND progress_pct IS NULL "
            "ORDER BY seq", {"pid": parent_id}).fetchall()]
        stats["weights"] = {r[0]: r[1] for r in self.conn.execute(
            "SELECT id, weight FROM temp.item_facts WHERE parent = :pid "
            "AND progress_pct IS NOT NULL ORDER BY seq", {"pid": parent_id}).fetchall()}
        return stats

    # ── 项目级聚合 ────────────────────────────────────────────────────────────
    def check_sums(self) -> dict:
        return dict(self.conn.execute("SELECT * FROM v_check_sums").fetchone())

    def leaf_progress(self) -> dict:
        return dict(self.conn.execute("""
            SELECT count(*)                                                  AS leaves,
                   sum(CASE WHEN progress_pct IS NOT NULL THEN 1 ELSE 0 END) AS counted,
                   sum(progress_pct)                                         AS pct_sum,
                   sum(CASE WHEN progress_pct IS NOT NULL
                             AND (progress_basis LIKE 'checks%'
                                  OR progress_basis = 'declared')
                            THEN 1 ELSE 0 END)                               AS countable
              FROM temp.item_facts
             WHERE type <> 'milestone' AND has_children = 0
        """).fetchone())

    def status_counts(self) -> dict:
        rows = self.conn.execute("""
            SELECT status, count(*) AS n, min(seq) AS first_seen
              FROM temp.item_facts WHERE type <> 'milestone'
             GROUP BY status ORDER BY first_seen
        """).fetchall()
        return {r["status"]: r["n"] for r in rows}

    def delayed_items(self) -> list:
        return [{"id": r["id"], "name": r["name"], "planned_end": r["planned_end"],
                 "delay_days": r["delay_days"]}
                for r in self.conn.execute("""
                    SELECT id, name, planned_end, delay_days FROM temp.item_facts
                     WHERE type <> 'milestone' AND schedule_status = 'delayed'
                     ORDER BY coalesce(delay_days, 0) DESC, seq
                """).fetchall()]

    def ids_where(self, predicate: str) -> list:
        return [r[0] for r in self.conn.execute(
            "SELECT id FROM temp.item_facts WHERE type <> 'milestone' AND %s ORDER BY seq"
            % predicate).fetchall()]

    def counts(self) -> dict:
        return dict(self.conn.execute("""
            SELECT count(*)                                                    AS items,
                   sum(CASE WHEN type <> 'milestone' THEN 1 ELSE 0 END)         AS work_items,
                   sum(CASE WHEN type <> 'milestone' AND has_children = 0
                            THEN 1 ELSE 0 END)                                  AS leaves,
                   sum(CASE WHEN type <> 'milestone'
                             AND (planned_start IS NOT NULL OR planned_end IS NOT NULL)
                            THEN 1 ELSE 0 END)                                  AS bars,
                   sum(CASE WHEN owner_id IS NOT NULL THEN 1 ELSE 0 END)         AS owned
              FROM temp.item_facts
        """).fetchone())

    def timeline(self) -> list:
        rows = self.conn.execute("""
            SELECT * FROM (
                SELECT planned_start AS date, id AS item_id, 'planned_start' AS kind,
                       name AS label, status, dates_derived AS derived
                  FROM temp.item_facts
                 WHERE type <> 'milestone' AND planned_start IS NOT NULL
                UNION ALL
                SELECT planned_end, id, 'planned_end', name, status, dates_derived
                  FROM temp.item_facts
                 WHERE type <> 'milestone' AND planned_end IS NOT NULL
                UNION ALL
                SELECT actual_end, id, 'actual_end', name, status, dates_derived
                  FROM temp.item_facts
                 WHERE type <> 'milestone' AND actual_end IS NOT NULL
                UNION ALL
                SELECT anchor_date, id, 'milestone', name, status, 0
                  FROM temp.item_facts
                 WHERE type = 'milestone' AND anchor_date IS NOT NULL
            ) ORDER BY date, item_id, kind
        """).fetchall()
        return [{"date": r["date"], "item_id": r["item_id"], "kind": r["kind"],
                 "label": r["label"], "status": r["status"], "derived": bool(r["derived"])}
                for r in rows]

    # ── 里程碑达成（计数 / 达成率分子分母 / 锚定跨度 / 逾期明细） ───────────────
    def milestone_counts(self) -> dict:
        return dict(self.conn.execute("""
            SELECT count(*)                                                    AS total,
                   sum(CASE WHEN status = 'achieved' THEN 1 ELSE 0 END)          AS achieved,
                   sum(CASE WHEN status = 'pending' THEN 1 ELSE 0 END)           AS pending,
                   sum(CASE WHEN status = 'at-risk' THEN 1 ELSE 0 END)           AS at_risk,
                   sum(CASE WHEN status = 'unknown-schedule' THEN 1 ELSE 0 END)  AS unknown_schedule,
                   min(anchor_date)                                             AS first_anchor,
                   max(anchor_date)                                             AS last_anchor,
                   count(anchor_date)                                           AS anchored
              FROM temp.item_facts WHERE type = 'milestone'
        """).fetchone())

    def milestone_rows(self, predicate: str, order: str = "seq") -> list:
        return [dict(r) for r in self.conn.execute(
            "SELECT id, name, anchor_date, delay_days FROM temp.item_facts "
            "WHERE type = 'milestone' AND %s ORDER BY %s" % (predicate, order)).fetchall()]

    def window(self) -> dict:
        row = self.conn.execute("""
            SELECT min(date) AS earliest, max(date) AS latest, count(*) AS events FROM (
                SELECT planned_start AS date FROM temp.item_facts
                 WHERE type <> 'milestone' AND planned_start IS NOT NULL
                UNION ALL
                SELECT planned_end FROM temp.item_facts
                 WHERE type <> 'milestone' AND planned_end IS NOT NULL
                UNION ALL
                SELECT actual_end FROM temp.item_facts
                 WHERE type <> 'milestone' AND actual_end IS NOT NULL
                UNION ALL
                SELECT anchor_date FROM temp.item_facts
                 WHERE type = 'milestone' AND anchor_date IS NOT NULL
            )
        """).fetchone()
        return dict(row)

    def current_phase(self) -> str:
        row = self.conn.execute("""
            SELECT name FROM temp.item_facts
             WHERE has_children = 1 AND type <> 'milestone' AND status = 'in-progress'
             ORDER BY coalesce(planned_start, '9999-99-99'), id LIMIT 1
        """).fetchone()
        return row[0] if row else None


def build_status_map(data: dict) -> dict:
    smap = dict(DEFAULT_STATUS_MAP)
    override = data.get("status_map") or {}
    if not isinstance(override, dict):
        raise EngineError("status_map 必须是对象 {源状态字面量: 三态}")
    for key, value in override.items():
        if value not in TASK_STATES:
            raise EngineError(
                "status_map[%r] = %r 不在合法状态集合 %s 内" % (key, value, list(TASK_STATES))
            )
        smap[str(key).strip().lower()] = value
    return smap


def parse_items(data: dict) -> list:
    items, seen = [], set()
    for idx, raw in enumerate(data["items"]):
        if not isinstance(raw, dict):
            raise EngineError("items[%d] 必须是对象" % idx)
        for field in ("id", "name", "type", "source"):
            if not raw.get(field):
                raise EngineError("items[%d] 缺少必填字段 %s（其余字段：%r）" % (idx, field, raw))
        iid = str(raw["id"]).strip()
        if iid in seen:
            raise EngineError("条目 ID 重复：%r —— 每个条目必须有唯一 ID" % iid)
        seen.add(iid)
        if raw["type"] not in VALID_TYPES:
            raise EngineError(
                "条目 %s 的 type=%r 非法，合法值：%s" % (iid, raw["type"], list(VALID_TYPES))
            )
        item = {
            "id": iid,
            "name": str(raw["name"]),
            "type": raw["type"],
            "parent": (str(raw["parent"]).strip() if raw.get("parent") else None),
            "source": str(raw["source"]),
            "owner_id": (str(raw["owner_id"]).strip() if raw.get("owner_id") else None),
            "phase_id": (str(raw["phase_id"]).strip() if raw.get("phase_id") else None),
            "phase_order": raw.get("phase_order"),
            "depends_on": [str(x).strip() for x in (raw.get("depends_on") or []) if str(x).strip()],
            "status_raw": raw.get("status_raw"),
            "checks": parse_checks(raw.get("checks"), iid),
            "declared_pct": parse_declared_pct(raw, iid),
            "weight": parse_weight(raw, iid),
            "achieved_evidence": raw.get("achieved_evidence"),
            "risk_note": raw.get("risk_note"),
            "anchor_item": (str(raw["anchor_item"]).strip() if raw.get("anchor_item") else None),
            "dates": {},
            "date_meta": {},
            "evidence": [],
            "children": [],
        }
        for alias, canonical in DATE_ALIASES.items():
            if raw.get(alias) and not raw.get(canonical):
                raw[canonical] = raw[alias]
        for field in DATE_FIELDS:
            parsed = normalize_date(raw.get(field), "条目 %s 的 %s" % (iid, field))
            if parsed:
                iso, precision, inferred = parsed
                item["dates"][field] = iso
                item["date_meta"][field] = {"precision": precision, "inferred": inferred}
                if str(raw[field]).strip() != iso:
                    item["evidence"].append(
                        "%s 由 %r 归一化为 %s（精度 %s%s）"
                        % (field, raw[field], iso, precision,
                           "，日由引擎补为当月首日、属推断" if inferred else "，仅格式转写")
                    )
            else:
                item["dates"][field] = None
        items.append(item)
    index = {it["id"]: it for it in items}
    for it in items:
        if it["parent"]:
            if it["parent"] not in index:
                raise EngineError("条目 %s 的 parent=%r 不存在（悬空引用）" % (it["id"], it["parent"]))
            if it["parent"] == it["id"]:
                raise EngineError("条目 %s 的 parent 指向自身" % it["id"])
            index[it["parent"]]["children"].append(it["id"])
        if it["anchor_item"] and it["anchor_item"] not in index:
            raise EngineError(
                "里程碑 %s 的 anchor_item=%r 不存在（悬空引用）" % (it["id"], it["anchor_item"])
            )
    detect_cycles(items, index)
    return items, index


def parse_checks(raw, iid: str):
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise EngineError("条目 %s 的 checks 必须是对象 {done, open, deferred, excluded}" % iid)
    out = {}
    for key in ("done", "open", "deferred", "excluded"):
        value = raw.get(key, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise EngineError("条目 %s 的 checks.%s=%r 必须是非负整数" % (iid, key, value))
        out[key] = value
    if out["done"] + out["open"] + out["deferred"] == 0:
        raise EngineError(
            "条目 %s 的 checks 全为 0 → 没有任何可计数依据时请省略 checks 字段（引擎会记 "
            "progress_pct=null），不要写 0 伪装成「0%% 完成」" % iid
        )
    return out


def parse_declared_pct(raw: dict, iid: str):
    value = raw.get("progress_pct")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EngineError("条目 %s 的 progress_pct=%r 必须是 0–100 的数字" % (iid, value))
    if not 0 <= float(value) <= 100:
        raise EngineError("条目 %s 的 progress_pct=%r 超出 0–100" % (iid, value))
    if not raw.get("progress_source"):
        raise EngineError(
            "条目 %s 给了明写百分比 progress_pct=%r 却无 progress_source 出处 → 无出处的"
            "百分比视为编造，引擎拒绝" % (iid, value)
        )
    return {"value": round(float(value), 1), "source": str(raw["progress_source"])}


def parse_weight(raw: dict, iid: str):
    """条目权重（可选）：仅当材料明确给出占比/权重时使用，必须带出处。"""
    value = raw.get("weight")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise EngineError("条目 %s 的 weight=%r 必须是正数" % (iid, value))
    if not raw.get("weight_source"):
        raise EngineError(
            "条目 %s 给了 weight=%r 却无 weight_source 出处 → 无依据的权重视为编造，"
            "引擎拒绝（无权重依据时省略该字段，引擎按等权平均聚合）" % (iid, value)
        )
    return {"value": float(value), "source": str(raw["weight_source"])}


def detect_cycles(items: list, index: dict) -> None:
    for it in items:
        seen, cur = set(), it
        while cur["parent"]:
            if cur["id"] in seen:
                raise EngineError("父项链存在环：%s" % " → ".join(sorted(seen)))
            seen.add(cur["id"])
            cur = index[cur["parent"]]


# ── 状态与进度判定（任务侧） ────────────────────────────────────────────────────
def map_status(item: dict, smap: dict, diagnostics: dict):
    raw = item.get("status_raw")
    if raw is None or str(raw).strip() == "":
        return None, None
    key = str(raw).strip().lower()
    key = re.sub(r"^\[([xX~pP ]?)\]$", lambda m: "[%s]" % m.group(1).lower(), key)
    if key in smap:
        return smap[key], "status_raw:%s" % raw
    diagnostics["unmapped_statuses"][str(raw)] = diagnostics["unmapped_statuses"].get(str(raw), 0) + 1
    return "unknown", "status_raw:%s（未映射）" % raw


def compute_progress(item: dict, status, count_deferred: bool):
    """条目进度%：只认可计数依据（勾选比 / 材料明写），否则 null。绝不由状态臆测数字。"""
    checks = item["checks"]
    if checks:
        done, open_, deferred = checks["done"], checks["open"], checks["deferred"]
        denom = done + open_ + (deferred if count_deferred else 0)
        if denom == 0:
            return None, None, None
        pct = round(done * 100.0 / denom, 1)
        formula = "%d/%d = %.1f%%" % (done, denom, pct)
        basis = "checks（%s deferred）" % ("含" if count_deferred else "不含")
        return pct, formula, basis
    if item["declared_pct"]:
        pct = item["declared_pct"]["value"]
        return pct, "材料明写 %.1f%%（%s）" % (pct, item["declared_pct"]["source"]), "declared"
    if status == "completed":
        return 100.0, "100/100 = 100.0%", "status:completed"
    if status == "not-started":
        return 0.0, "0/100 = 0.0%", "status:not-started"
    return None, None, None


def schedule_of_task(item: dict, status, baseline: str, diff=days_between):
    """任务排期判定：延期 ⇔ 有计划完成日 且 未完成 且 计划日 < 基准日。无计划日 → unknown-schedule。

    `diff(later, earlier)` 是天数差的实现：`--db` 路径注入 SQL `julianday` 版本，
    `--input` JSON 路径用内置 `days_between`。两者结果一致（同为 ISO 日期的整数日差）。
    """
    planned = item["dates"].get("planned_end")
    actual = item["dates"].get("actual_end")
    if planned is None:
        return "unknown-schedule", None, None, "无计划完成日，无法判定延期"
    days_to = diff(planned, baseline)              # >0 未到期，<0 已过期
    if status == "completed":
        if actual is None:
            return "completed-schedule-unknown", None, days_to, (
                "已完成但无实际完成日，无法判定是否按期（计划 %s）" % planned
            )
        late = diff(actual, planned)
        if late > 0:
            return "completed-late", late, days_to, (
                "逾期 %d 天完成（实际 %s − 计划 %s）" % (late, actual, planned)
            )
        return "completed-on-time", 0, days_to, (
            "按期完成（实际 %s ≤ 计划 %s）" % (actual, planned)
        )
    if days_to < 0:
        return "delayed", -days_to, days_to, (
            "逾期 %d 天（基准日 %s − 计划完成日 %s），状态 %s" % (-days_to, baseline, planned, status)
        )
    return "on-schedule", 0, days_to, (
        "计划完成日 %s 距基准日 %s 还有 %d 天" % (planned, baseline, days_to)
    )


# ── 里程碑判定 ──────────────────────────────────────────────────────────────────

def progress_bar_str(pct, cells: int = 10):
    """定宽字符进度条（█ U+2588 / ░ U+2591，默认 10 格）。呈现层照抄本串，不自行按百分比摆格子。"""
    if pct is None:
        return None
    filled = int(round(max(0.0, min(100.0, float(pct))) / 100.0 * cells))
    return "█" * filled + "░" * (cells - filled)


def resolve_milestone_anchor(item: dict, index: dict):
    """里程碑锚定日：绝对日期优先；否则由 anchor_item 的计划完成日换算（换算在引擎内做）。"""
    planned = item["dates"].get("planned_end")
    if planned:
        return planned, None
    if item["anchor_item"]:
        anchor = index[item["anchor_item"]]
        resolved = anchor["dates"].get("planned_end") or anchor["dates"].get("actual_end")
        if resolved:
            return resolved, "锚定 %s（%s）结束点，按当前排期换算为 %s" % (
                anchor["id"], anchor["name"], resolved
            )
        return None, "锚定 %s 但该工作项无计划/实际完成日，锚定日不可换算" % anchor["id"]
    return None, None


def judge_milestone(item: dict, index: dict, baseline: str, diff=days_between):
    """里程碑状态判定（顺序判定，命中即止）。返回 (status, delay_days, anchor, evidence)。"""
    anchor, note = resolve_milestone_anchor(item, index)
    ev = [note] if note else []
    actual = item["dates"].get("actual_end")
    if actual or item["achieved_evidence"]:
        parts = []
        if item["achieved_evidence"]:
            parts.append(str(item["achieved_evidence"]))
        if actual:
            parts.append("达成日 %s" % actual)
        late = None
        if actual and anchor:
            days = diff(actual, anchor)
            if days > 0:
                late = days
                parts.append("晚于锚定日 %d 天（%s − %s）" % (days, actual, anchor))
            else:
                parts.append("不晚于锚定日 %s" % anchor)
        ev.append("已达成：" + "；".join(parts))
        return "achieved", late, anchor, ev
    if anchor is None:
        ev.append("无计划日期（无绝对锚定日、无可换算的锚定工作项），无法判定延期")
        return "unknown-schedule", None, None, ev
    days_to = diff(anchor, baseline)
    if days_to < 0:
        ev.append("逾期 %d 天（基准日 %s − 锚定日 %s）" % (-days_to, baseline, anchor))
        return "at-risk", -days_to, anchor, ev
    if item["risk_note"]:
        ev.append("风险：%s（锚定日 %s 尚未到期）" % (item["risk_note"], anchor))
        return "at-risk", 0, anchor, ev
    ev.append("待达成：锚定日 %s 距基准日 %s 还有 %d 天" % (anchor, baseline, days_to))
    return "pending", 0, anchor, ev


# ── 聚合（阶段/父项 → 项目） ────────────────────────────────────────────────────
def depth_of(item: dict, index: dict) -> int:
    depth, cur = 0, item
    while cur["parent"]:
        depth += 1
        cur = index[cur["parent"]]
    return depth


def python_child_stats(kids: list) -> dict:
    """子项统计的纯 Python 实现（`--input` JSON 路径用）。

    形状与 `SqlFacts.child_stats`（SQL `GROUP BY` 版本）**逐键一致** —— 聚合的算术有两个
    实现、但决策逻辑只有一份（下方 `aggregate_tree`），两条路径的输出可 diff 自证等价。
    """
    counted = [k for k in kids if k["progress_pct"] is not None]
    excluded = [k for k in kids if k["progress_pct"] is None]
    weighted = [k for k in counted if k["weight"] is not None]
    starts = [k["planned_start"] for k in kids if k["planned_start"]]
    ends = [k["planned_end"] for k in kids if k["planned_end"]]
    actuals = [k["actual_end"] for k in kids if k["actual_end"]]
    return {
        "children": len(kids),
        "participating": len([k for k in kids if k["status"] in AGGREGATABLE]),
        "completed": len([k for k in kids if k["status"] == "completed"]),
        "not_started": len([k for k in kids if k["status"] == "not-started"]),
        "counted": len(counted),
        "excluded": len(excluded),
        "pct_sum": (sum(k["progress_pct"] for k in counted) if counted else None),
        "weighted": len(weighted),
        "weighted_sum": (sum(k["progress_pct"] * k["weight"] for k in counted)
                         if counted and len(weighted) == len(counted) else None),
        "weight_sum": (sum(k["weight"] for k in counted)
                       if counted and len(weighted) == len(counted) else None),
        "planned_start_min": (min(starts) if starts else None),
        "planned_end_max": (max(ends) if ends else None),
        "actual_end_max": (max(actuals) if actuals else None),
        "actual_end_count": len(actuals),
        "excluded_ids": [k["id"] for k in excluded],
        "weights": {k["id"]: k["weight"] for k in counted},
    }


def aggregate_status_from_stats(stats: dict):
    """完备真值表的等价判据：全完成→completed；全未开始→not-started；其余→in-progress。"""
    participating = stats["participating"] or 0
    if not participating:
        return None
    if stats["completed"] == participating:
        return "completed"
    if stats["not_started"] == participating:
        return "not-started"
    return "in-progress"


def aggregate_tree(items: list, index: dict, computed: dict, count_deferred: bool,
                   baseline: str, facts=None, diff=days_between):
    """自底向上聚合父项：状态（真值表）、进度（等权/加权平均，分母写明）、计划/实际日期（子项包络）。

    算术来源：`facts` 非空时取 SQL `GROUP BY` 的结果（`--db` 路径），否则用
    `python_child_stats`（`--input` 路径）。决策与文案只有这一份实现。
    """
    parents = [it for it in items if it["children"] and it["type"] != "milestone"]
    for it in sorted(parents, key=lambda x: depth_of(x, index), reverse=True):
        rec = computed[it["id"]]
        kids = [computed[cid] for cid in it["children"]]
        stats = facts.child_stats(it["id"]) if facts else python_child_stats(kids)
        agg = aggregate_status_from_stats(stats)
        if agg and rec["status_source"] in (None, "none"):
            rec["status"], rec["status_source"] = agg, "aggregated（%d 个子项）" % (
                stats["participating"] or 0)
            rec["evidence"].append("状态由 %d 个子项聚合得出：%s" % (stats["children"], agg))
        elif agg and rec["status"] != agg:
            rec["evidence"].append(
                "记录冲突：自身状态 %s，子项聚合为 %s（呈现按聚合值，冲突写进呈现物）"
                % (rec["status"], agg)
            )
            rec["status"], rec["status_source"] = agg, "aggregated（覆盖自身状态）"
        elif agg:
            rec["status_source"] = "aggregated"
        # 进度：等权平均（材料给了权重则加权），仅计入有 progress_pct 的子项
        counted_n, excluded_n = stats["counted"] or 0, stats["excluded"] or 0
        if rec["progress_pct"] is None or rec["progress_basis"] in (None, "status:completed",
                                                                   "status:not-started"):
            if counted_n:
                weighted_n = stats["weighted"] or 0
                if weighted_n and weighted_n != counted_n:
                    raise EngineError(
                        "条目 %s 的子项权重不完整：%d/%d 个计入进度的子项给了 weight → 要么全给"
                        "（各带 weight_source），要么全不给（引擎按等权平均）"
                        % (it["id"], weighted_n, counted_n)
                    )
                if weighted_n:
                    num, den = stats["weighted_sum"], stats["weight_sum"]
                    pct = round(num / den, 1)
                    rec["progress_formula"] = "Σ(子项进度×权重) %.1f / Σ权重 %.1f = %.1f%%" % (
                        num, den, pct
                    )
                    rec["progress_basis"] = "aggregated（加权平均）"
                else:
                    total = stats["pct_sum"]
                    pct = round(total / counted_n, 1)
                    rec["progress_formula"] = "Σ子项进度 %.1f / 子项数 %d = %.1f%%" % (
                        total, counted_n, pct
                    )
                    rec["progress_basis"] = "aggregated（等权平均）"
                rec["progress_pct"] = pct
                rec["evidence"] = [e for e in rec["evidence"] if "无可计数依据" not in e]
                rec["evidence"].append("进度由 %d 个子项聚合得出：%s"
                                       % (counted_n, rec["progress_formula"]))
            else:
                rec["progress_pct"], rec["progress_formula"], rec["progress_basis"] = None, None, None
        rec["aggregation"] = {
            "children": stats["children"],
            "denominator": counted_n,
            "excluded_unquantified": excluded_n,
            "excluded_ids": stats["excluded_ids"],
            "weights": (stats["weights"]
                        if any(v is not None for v in stats["weights"].values()) else None),
            "weight_sum": stats["weight_sum"],
        }
        if excluded_n:
            rec["evidence"].append(
                "%d 项子项进度未量化，未计入本项进度分母" % excluded_n
            )
        rollup_parent_dates(rec, stats, baseline, diff)
        if facts:
            facts.sync(rec)


def rollup_parent_dates(rec: dict, stats: dict, baseline: str, diff=days_between) -> None:
    """父项自身无日期时，用子项日期包络推出阶段起止，并重跑排期判定（计算全在引擎内）。"""
    derived = []
    if rec["planned_start"] is None and stats["planned_start_min"]:
        rec["planned_start"] = stats["planned_start_min"]
        derived.append("计划开始日取子项最早计划开始日 %s" % rec["planned_start"])
    if rec["planned_end"] is None and stats["planned_end_max"]:
        rec["planned_end"] = stats["planned_end_max"]
        derived.append("计划完成日取子项最晚计划完成日 %s" % rec["planned_end"])
    if (rec["actual_end"] is None and stats["children"]
            and stats["completed"] == stats["children"]
            and stats["actual_end_count"] == stats["children"]):
        rec["actual_end"] = stats["actual_end_max"]
        derived.append("子项全部完成，实际完成日取最晚子项实际完成日 %s" % rec["actual_end"])
    if not derived:
        return
    rec["dates_derived"] = True
    rec["evidence"].extend(derived)
    if rec["planned_start"] and rec["planned_end"]:
        rec["duration_days"] = diff(rec["planned_end"], rec["planned_start"]) + 1
    proxy = {"dates": {"planned_end": rec["planned_end"], "actual_end": rec["actual_end"]}}
    sched, delay, days_to, ev = schedule_of_task(proxy, rec["status"], baseline, diff)
    rec["schedule_status"], rec["delay_days"], rec["days_to_planned_end"] = sched, delay, days_to
    rec["evidence"] = [e for e in rec["evidence"] if "无计划完成日，无法判定延期" not in e]
    rec["evidence"].append(ev)


def project_progress(items: list, computed: dict, count_deferred: bool, facts=None):
    """项目整体进度：优先勾选口径（含/不含 deferred 两条算式都给），否则叶子等权平均。

    分子分母的加总：`facts` 非空时取 SQL（`v_check_sums` 视图 + 临时表上的叶子聚合），
    否则用 Python 加总。判定顺序与算式串只有这一份实现。
    """
    if facts:
        sums = facts.check_sums()
        done, open_ = int(sums["done"] or 0), int(sums["open_count"] or 0)
        deferred, excluded = int(sums["deferred"] or 0), int(sums["excluded_marks"] or 0)
    else:
        done = sum(it["checks"]["done"] for it in items if it["checks"])
        open_ = sum(it["checks"]["open"] for it in items if it["checks"])
        deferred = sum(it["checks"]["deferred"] for it in items if it["checks"])
        excluded = sum(it["checks"]["excluded"] for it in items if it["checks"])
    if done + open_ + deferred > 0:
        d_excl = done + open_
        d_incl = done + open_ + deferred
        pct_excl = round(done * 100.0 / d_excl, 1) if d_excl else None
        pct_incl = round(done * 100.0 / d_incl, 1) if d_incl else None
        canonical = (
            {"basis": "checks（含 deferred）", "progress_pct": pct_incl,
             "formula": "%d/%d = %.1f%%" % (done, d_incl, pct_incl)}
            if count_deferred else
            {"basis": "checks（不含 deferred）", "progress_pct": pct_excl,
             "formula": "%d/%d = %.1f%%" % (done, d_excl, pct_excl)}
        )
        alt = (
            {"basis": "checks（不含 deferred）", "progress_pct": pct_excl,
             "formula": "%d/%d = %.1f%%" % (done, d_excl, pct_excl)}
            if count_deferred else
            {"basis": "checks（含 deferred）", "progress_pct": pct_incl,
             "formula": "%d/%d = %.1f%%" % (done, d_incl, pct_incl)}
        )
        buckets = {"done": done, "open": open_, "deferred": deferred, "excluded_marks": excluded}
        closure = "%d + %d + %d = %d" % (done, open_, deferred, done + open_ + deferred)
        return dict(canonical, alternatives=[alt], buckets=buckets, bucket_closure=closure)
    if facts:
        leaf = facts.leaf_progress()
        leaf_total = int(leaf["leaves"] or 0)
        counted_n = int(leaf["counted"] or 0)
        pct_sum = leaf["pct_sum"]
        countable_n = int(leaf["countable"] or 0)
    else:
        leaves = [computed[it["id"]] for it in items
                  if not it["children"] and it["type"] != "milestone"]
        counted = [r for r in leaves if r["progress_pct"] is not None]
        # 只有"状态推出的 0/100"不足以支撑一个整体百分比：至少要有一个叶子的进度落在
        # 可计数依据（勾选比 / 材料明写百分比）上，否则整体进度走诚实空值（只报状态计数）。
        countable = [r for r in counted if r["progress_basis"]
                     and (r["progress_basis"].startswith("checks")
                          or r["progress_basis"] == "declared")]
        leaf_total, counted_n = len(leaves), len(counted)
        pct_sum = sum(r["progress_pct"] for r in counted) if counted else None
        countable_n = len(countable)
    if counted_n and countable_n:
        pct = round(pct_sum / counted_n, 1)
        return {
            "basis": "leaves（等权平均）", "progress_pct": pct,
            "formula": "Σ叶子进度 %.1f / 叶子数 %d = %.1f%%" % (pct_sum, counted_n, pct),
            "alternatives": [], "buckets": None, "bucket_closure": None,
            "unquantified_leaves": leaf_total - counted_n,
            "countable_leaves": countable_n,
        }
    return {
        "basis": None, "progress_pct": None, "formula": None,
        "reason": "无勾选比、无材料明写百分比 → 整体进度无可计数依据，只报状态计数",
        "alternatives": [], "buckets": None, "bucket_closure": None,
    }


# ── 视图/甘特/时间轴/覆盖 ────────────────────────────────────────────────────────
def collect_timeline(items: list, computed: dict, facts=None):
    """时间轴事件排序聚合：全部日期（含由子项包络推出的阶段日期）按日期升序。

    `facts` 非空时由 SQL 完成（`UNION ALL` + `ORDER BY date, item_id, kind`）。
    """
    if facts:
        return facts.timeline()
    events = []
    for it in items:
        rec = computed[it["id"]]
        if it["type"] == "milestone":
            if rec["anchor_date"]:
                events.append({"date": rec["anchor_date"], "item_id": it["id"],
                               "kind": "milestone", "label": it["name"], "status": rec["status"],
                               "derived": False})
            continue
        for field in ("planned_start", "planned_end", "actual_end"):
            if rec.get(field):
                events.append({"date": rec[field], "item_id": it["id"], "kind": field,
                               "label": it["name"], "status": rec["status"],
                               "derived": bool(rec.get("dates_derived"))})
    events.sort(key=lambda e: (e["date"], e["item_id"], e["kind"]))
    return events


def gantt_block(data: dict, items: list, computed: dict, timeline: list, baseline: str,
                facts=None, diff=days_between):
    dated = [e["date"] for e in timeline]
    declared_start = data.get("project", {}).get("start")
    start = normalize_date(declared_start, "project.start")
    if start:
        project_start, start_source = start[0], "project.start（材料给出）"
    elif dated:
        project_start, start_source = min(dated), "全部日期中的最早者（推断起点）"
    else:
        project_start, start_source = None, None
    if facts:
        bar_count = int(facts.counts()["bars"] or 0)
    else:
        bar_count = len([computed[it["id"]] for it in items
                         if it["type"] != "milestone" and (computed[it["id"]]["planned_start"]
                                                           or computed[it["id"]]["planned_end"])])
    git = data.get("git_window") or {}
    git_span, git_first, git_last = None, None, None
    if git:
        first = normalize_date(git.get("first_commit"), "git_window.first_commit")
        last = normalize_date(git.get("last_commit"), "git_window.last_commit")
        if first and last:
            git_first, git_last = first[0], last[0]
            git_span = diff(git_last, git_first)
    commit_count = git.get("commit_count")
    weak_git = bool(
        git and (
            (isinstance(commit_count, int) and commit_count < WEAK_GIT_COMMITS)
            or (git_span is not None and git_span < WEAK_GIT_SPAN_DAYS)
        )
    )
    has_dates = bool(bar_count)
    recommended = has_dates
    if has_dates:
        reason = "存在 %d 个带计划日期的工作项，可出甘特" % bar_count
    elif weak_git:
        reason = ("无任何计划日期；git 材料过弱（%s 提交 / 跨度 %s 天），不作排期依据 → 甘特不出图"
                  % (commit_count, git_span))
    else:
        reason = "无任何计划日期或工期依据 → 甘特不出图"
    block = {
        "project_start": project_start,
        "project_start_source": start_source,
        "today_offset_days": (diff(baseline, project_start) if project_start else None),
        "bar_count": bar_count,
        "split_recommended": bar_count > GANTT_SPLIT_BARS,
        "schedule_material": {
            "has_planned_dates": has_dates,
            "git_span_days": git_span,
            "git_commit_count": commit_count,
            "git_window": ([git_first, git_last] if git_first else None),
            "weak_git_material": weak_git,
            "gantt_recommended": recommended,
            "reason": reason,
        },
    }
    if project_start:
        block["today_directive"] = "today is %d days after start" % block["today_offset_days"]
        block["title_baseline"] = "基准日 today = %s，项目第 %d 天" % (
            baseline, block["today_offset_days"]
        )
    return block


def milestone_block(items: list, computed: dict, baseline: str, facts=None,
                    diff=days_between):
    """里程碑汇总：计数、达成率分子分母、锚定跨度、逾期明细、视图独立成图判据。

    `facts` 非空时计数/极值来自 SQL（`GROUP BY` + `min`/`max`），跨度用 SQL 天数差。
    """
    ms = [computed[it["id"]] for it in items if it["type"] == "milestone"]
    if facts:
        agg = facts.milestone_counts()
        counts = {"total": int(agg["total"] or 0), "achieved": int(agg["achieved"] or 0),
                  "pending": int(agg["pending"] or 0), "at_risk": int(agg["at_risk"] or 0),
                  "unknown_schedule": int(agg["unknown_schedule"] or 0)}
        first_anchor, last_anchor = agg["first_anchor"], agg["last_anchor"]
        span = (diff(last_anchor, first_anchor)
                if int(agg["anchored"] or 0) >= 2 else None)
        overdue = [{"id": r["id"], "name": r["name"], "anchor": r["anchor_date"],
                    "delay_days": r["delay_days"]}
                   for r in facts.milestone_rows(
                       "status = 'at-risk' AND delay_days IS NOT NULL AND delay_days <> 0",
                       "coalesce(delay_days, 0) DESC, seq")]
        achieved_late = [{"id": r["id"], "name": r["name"], "late_days": r["delay_days"]}
                         for r in facts.milestone_rows(
                             "status = 'achieved' AND delay_days IS NOT NULL "
                             "AND delay_days <> 0")]
        unknown_ids = [r["id"] for r in facts.milestone_rows("status = 'unknown-schedule'")]
        delay_max_row = facts.milestone_rows(
            "status = 'at-risk' AND delay_days IS NOT NULL AND delay_days <> 0",
            "delay_days DESC, seq")
        delay_max = delay_max_row[0]["delay_days"] if delay_max_row else None
    else:
        dates = sorted(r["anchor_date"] for r in ms if r["anchor_date"])
        first_anchor = dates[0] if dates else None
        last_anchor = dates[-1] if dates else None
        span = diff(dates[-1], dates[0]) if len(dates) >= 2 else None
        counts = {"total": len(ms), "achieved": 0, "pending": 0, "at_risk": 0,
                  "unknown_schedule": 0}
        for r in ms:
            key = {"achieved": "achieved", "pending": "pending",
                   "at-risk": "at_risk", "unknown-schedule": "unknown_schedule"}[r["status"]]
            counts[key] += 1
        overdue = sorted(
            [{"id": r["id"], "name": r["name"], "anchor": r["anchor_date"],
              "delay_days": r["delay_days"]}
             for r in ms if r["status"] == "at-risk" and r["delay_days"]],
            key=lambda x: -x["delay_days"])
        achieved_late = [{"id": r["id"], "name": r["name"], "late_days": r["delay_days"]}
                         for r in ms if r["status"] == "achieved" and r["delay_days"]]
        unknown_ids = [r["id"] for r in ms if r["status"] == "unknown-schedule"]
        delay_max = max([r["delay_days"] for r in ms
                         if r["status"] == "at-risk" and r["delay_days"]] or [None],
                        key=lambda x: (x is not None, x))
    # 达成率：分母 = 有计划锚定的里程碑数（unknown-schedule 不计入，避免"无计划"拉低达成率被误读）
    ach_den = counts["total"] - counts["unknown_schedule"]
    ach_num = counts["achieved"]
    if ach_den > 0:
        ach_pct = round(ach_num * 100.0 / ach_den, 1)
        ach_formula = "%d/%d = %.1f%%" % (ach_num, ach_den, ach_pct)
        ach_bar = progress_bar_str(ach_pct)
    else:
        ach_pct = None
        ach_formula = None
        ach_bar = None
    return {
        "counts": counts,
        "achieved_numerator": ach_num,
        "achieved_denominator": ach_den,
        "achieved_pct": ach_pct,
        "achieved_formula": ach_formula,
        "achieved_bar": ach_bar,
        "delay_days_max": delay_max,
        "overdue": overdue,
        "achieved_late": achieved_late,
        "unknown_schedule_ids": unknown_ids,
        "narrative": "%d 个里程碑：已达成 %d、逾期 %d、待达成 %d、无计划日期 %d" % (
            counts["total"], counts["achieved"], counts["at_risk"],
            counts["pending"], counts["unknown_schedule"]),
        "view": {
            "count": counts["total"],
            "first_anchor": first_anchor,
            "last_anchor": last_anchor,
            "span_days": span,
            "standalone_condition_a": bool(
                counts["total"] >= MS_VIEW_MIN_COUNT and span is not None
                and span >= MS_VIEW_MIN_SPAN_DAYS
            ),
            "thresholds": {"min_count": MS_VIEW_MIN_COUNT, "min_span_days": MS_VIEW_MIN_SPAN_DAYS},
        },
    }


def coverage_block(data: dict, items: list):
    cov = data.get("coverage")
    if not cov:
        return None
    if not isinstance(cov, dict):
        raise EngineError("coverage 必须是对象")
    for field in ("candidate_total",):
        if not isinstance(cov.get(field), int):
            raise EngineError("coverage.%s 必填且必须是整数" % field)
    total = cov["candidate_total"]
    excluded = int(cov.get("excluded", 0) or 0)
    truncated = int(cov.get("granularity_truncated", 0) or 0)
    unattributed = int(cov.get("unattributed", 0) or 0)
    # Phases are inferred groupings, not ledger candidates (the candidate_total
    # counts source-label-level entries only) — counting phase nodes into the
    # closure tree against an items-only total produced a permanent false
    # warning (feedback consume 2026-08-17). They are reported separately.
    phase_nodes = len([it for it in items if it.get("type") == "phase"])
    tree_items = len([it for it in items
                      if it["type"] not in ("milestone", "phase")])
    expected = total - excluded - truncated
    denom = total - excluded
    attributed = denom - unattributed
    return {
        "source_label": cov.get("source_label", "未声明候选来源层级"),
        "candidate_total": total,
        "excluded": excluded,
        "granularity_truncated": truncated,
        "unattributed": unattributed,
        "tree_items": tree_items,
        "phase_nodes": phase_nodes,
        "closure_equation": "%d − %d − %d = %d" % (total, excluded, truncated, expected),
        "closure_ok": expected == tree_items,
        "closure_note": (
            "闭合成立：候选全集减去剔除/截断项等于分解树条目数"
            if expected == tree_items else
            "闭合不成立：%d − %d − %d = %d，但分解树条目数为 %d → 差值必须有名有数"
            % (total, excluded, truncated, expected, tree_items)
        ),
        "coverage_formula": ("%d/%d = %.1f%%" % (attributed, denom, round(attributed * 100.0 / denom, 1))
                            if denom else None),
        "progress_denominator_set": "%s（%d 项，已扣除剔除项 %d）" % (
            cov.get("source_label", "候选全集"), denom, excluded),
    }


# ── 主计算 ──────────────────────────────────────────────────────────────────────
def run(data: dict, baseline: str, count_deferred: bool, strict: bool, input_label: str,
        facts=None) -> dict:
    items, index = parse_items(data)
    smap = build_status_map(data)
    roster = data.get("people_roster") or {}
    diagnostics = {"unmapped_statuses": {}, "warnings": [], "declarations": []}
    computed = {}
    # 天数差的实现：`--db` 路径走 SQL julianday；JSON 路径走内置 days_between
    diff = facts.diff if facts else days_between

    for it in items:
        status, source = map_status(it, smap, diagnostics)
        rec = {
            "id": it["id"], "name": it["name"], "type": it["type"], "parent": it["parent"],
            "phase_id": it.get("phase_id"),
            "owner_id": it.get("owner_id"),
            "owner_name": (roster.get(it["owner_id"], {}).get("owner_name")
                           if it.get("owner_id") else None) or "未记录",
            "depends_on": list(it.get("depends_on") or []),
            "is_leaf": not it["children"],
            "children": list(it["children"]),
            "status": status or ("unknown" if it["type"] != "milestone" else "pending"),
            "status_source": source or "none",
            "progress_pct": None, "progress_formula": None, "progress_basis": None,
            "planned_start": it["dates"].get("planned_start"),
            "planned_end": it["dates"].get("planned_end"),
            "actual_start": it["dates"].get("actual_start"),
            "actual_end": it["dates"].get("actual_end"),
            "date_meta": it["date_meta"],
            "weight": (it["weight"]["value"] if it["weight"] else None),
            "weight_source": (it["weight"]["source"] if it["weight"] else None),
            "duration_days": None,
            "dates_derived": False,
            "anchor_date": None,
            "schedule_status": None, "delay_days": None, "days_to_planned_end": None,
            "evidence": list(it["evidence"]),
            "source": it["source"],
        }
        if it["dates"].get("planned_start") and it["dates"].get("planned_end"):
            rec["duration_days"] = diff(
                it["dates"]["planned_end"], it["dates"]["planned_start"]) + 1
        if it["type"] == "milestone":
            status_ms, delay, anchor, ev = judge_milestone(it, index, baseline, diff)
            rec.update(status=status_ms, status_source="milestone-judgement",
                       delay_days=delay, anchor_date=anchor,
                       schedule_status=("unknown-schedule" if status_ms == "unknown-schedule"
                                        else ("delayed" if status_ms == "at-risk" and delay
                                              else "on-schedule")))
            rec["evidence"].extend(ev)
        else:
            pct, formula, basis = compute_progress(it, rec["status"], count_deferred)
            rec.update(progress_pct=pct, progress_formula=formula, progress_basis=basis)
            if basis and basis.startswith("checks"):
                rec["evidence"].append("进度依据勾选比 %s" % formula)
            elif basis is None:
                rec["evidence"].append("无勾选比/无材料明写百分比 → 进度无可计数依据（不臆造数字）")
            sched, delay, days_to, ev = schedule_of_task(it, rec["status"], baseline, diff)
            rec.update(schedule_status=sched, delay_days=delay, days_to_planned_end=days_to)
            rec["evidence"].append(ev)
        computed[it["id"]] = rec

    if facts:
        facts.bind(items, computed)              # 逐条目记录进临时表，之后的聚合全在 SQL
    aggregate_tree(items, index, computed, count_deferred, baseline, facts, diff)

    if diagnostics["unmapped_statuses"]:
        listing = "、".join("%s×%d" % (k, v) for k, v in
                            sorted(diagnostics["unmapped_statuses"].items()))
        if strict:
            raise EngineError("存在未映射状态字面量（--strict）：%s" % listing)
        diagnostics["warnings"].append(
            "未映射状态字面量 %s → 相关条目状态记为 unknown，须在报告「状态映射」中列出原文"
            % listing)

    timeline = collect_timeline(items, computed, facts)
    gantt = gantt_block(data, items, computed, timeline, baseline, facts, diff)
    ms_block = milestone_block(items, computed, baseline, facts, diff)
    prog = project_progress(items, computed, count_deferred, facts)

    tasks = [r for r in computed.values() if r["type"] != "milestone"]
    if facts:
        status_counts = facts.status_counts()
        delayed = facts.delayed_items()
        unknown_sched = facts.ids_where("schedule_status = 'unknown-schedule'")
        unquantified = facts.ids_where("progress_pct IS NULL")
        item_counts = facts.counts()
        count_items, count_tasks = int(item_counts["items"]), int(item_counts["work_items"])
        count_leaves = int(item_counts["leaves"])
        owned_count = int(item_counts["owned"])
    else:
        status_counts = {}
        for r in tasks:
            status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1
        delayed = sorted([{"id": r["id"], "name": r["name"], "planned_end": r["planned_end"],
                           "delay_days": r["delay_days"]}
                          for r in tasks if r["schedule_status"] == "delayed"],
                         key=lambda x: -(x["delay_days"] or 0))
        unknown_sched = [r["id"] for r in tasks if r["schedule_status"] == "unknown-schedule"]
        unquantified = [r["id"] for r in tasks if r["progress_pct"] is None]
        count_items, count_tasks = len(items), len(tasks)
        count_leaves = len([r for r in tasks if r["is_leaf"]])
        owned_count = len([r for r in computed.values() if r.get("owner_id")])

    if unknown_sched:
        diagnostics["declarations"].append(
            "%d 个工作项无计划完成日，无法判定延期（%s）——报告须显式声明，不上逾期色"
            % (len(unknown_sched), "、".join(unknown_sched[:8])
               + ("…" if len(unknown_sched) > 8 else "")))
    if ms_block["unknown_schedule_ids"]:
        diagnostics["declarations"].append(
            "%d 个里程碑无计划日期，无法判定延期（%s）——报告须显式声明，不上逾期色"
            % (len(ms_block["unknown_schedule_ids"]),
               "、".join(ms_block["unknown_schedule_ids"])))
    if unquantified:
        diagnostics["declarations"].append(
            "%d 个工作项进度无可计数依据，记 `-（无可计数依据）`，未计入任何百分比分母"
            % len(unquantified))
    if not gantt["schedule_material"]["gantt_recommended"]:
        diagnostics["declarations"].append("排期材料不足：%s" % gantt["schedule_material"]["reason"])

    # 排期总判断与当前阶段（呈现层"进度判断句/当前处于哪个阶段"的唯一来源，不在报告里判定）
    has_planned = any(r["planned_end"] or r["planned_start"] for r in tasks)
    if delayed:
        schedule_state = "behind"
    elif has_planned:
        schedule_state = "on-track"
    else:
        schedule_state = "unknown-schedule"
    if facts:
        current_phase = facts.current_phase()
    else:
        inprog_groups = [r for r in computed.values()
                         if r["children"] and r["type"] != "milestone"
                         and r["status"] == "in-progress"]
        inprog_groups.sort(key=lambda r: (r["planned_start"] or "9999-99-99", r["id"]))
        current_phase = inprog_groups[0]["name"] if inprog_groups else None

    coverage = coverage_block(data, items)
    if coverage and not coverage["closure_ok"]:
        diagnostics["warnings"].append(coverage["closure_note"])

    groups = [
        {
            "id": r["id"], "name": r["name"], "status": r["status"],
            "progress_pct": r["progress_pct"], "progress_formula": r["progress_formula"],
            "progress_bar": progress_bar_str(r["progress_pct"]),
            "planned_start": r["planned_start"], "planned_end": r["planned_end"],
            "schedule_status": r["schedule_status"], "delay_days": r["delay_days"],
            "aggregation": r.get("aggregation"),
        }
        for r in computed.values() if r["children"] and r["type"] != "milestone"
    ]

    if facts:
        win = facts.window()
        earliest, latest = win["earliest"], win["latest"]
        span_days = (diff(latest, earliest) if int(win["events"] or 0) >= 2 else None)
    else:
        earliest = timeline[0]["date"] if timeline else None
        latest = timeline[-1]["date"] if timeline else None
        span_days = (diff(latest, earliest) if len(timeline) >= 2 else None)

    people_block = {
        "roster": list((data.get("people_roster") or {}).values()),
        "coverage_numerator": owned_count,
        "coverage_denominator": count_items,
        "coverage_pct": (round(owned_count * 100.0 / count_items, 1) if count_items else None),
        "coverage_formula": ("%d/%d = %.1f%%" % (owned_count, count_items,
                                                round(owned_count * 100.0 / count_items, 1))
                             if count_items else None),
        "unassigned_ids": [r["id"] for r in computed.values() if not r.get("owner_id")],
    }

    return {
        "engine": ENGINE_ID,
        "input_schema": data.get("input_schema", ENGINE_ID),
        "baseline": baseline,
        "input": input_label,
        "options": {"count_deferred": count_deferred, "strict": strict},
        # 本次运行实际生效的阈值（唯一存放处见模块头常量）：随输出落盘，供 `## 元信息` 复核。
        # 文档与报告只引用判定结果字段，不复述这些数字（references/portability.md §1.1）。
        "thresholds": {
            "weak_git_commits": WEAK_GIT_COMMITS,
            "weak_git_span_days": WEAK_GIT_SPAN_DAYS,
            "milestone_view_min_count": MS_VIEW_MIN_COUNT,
            "milestone_view_min_span_days": MS_VIEW_MIN_SPAN_DAYS,
            "gantt_split_bars": GANTT_SPLIT_BARS,
        },
        "project": {
            "name": (data.get("project") or {}).get("name"),
            "status_counts": status_counts,
            "progress": prog,
            "counts": {
                "items": count_items,
                "work_items": count_tasks,
                "leaves": count_leaves,
                "milestones": ms_block["counts"]["total"],
                "delayed": len(delayed),
                "unknown_schedule": len(unknown_sched),
                "unquantified_progress": len(unquantified),
            },
            "delayed_items": delayed,
            "delay_days_max": (max(x["delay_days"] for x in delayed if x["delay_days"])
                               if any(x["delay_days"] for x in delayed) else None),
            "progress_bar": progress_bar_str(prog.get("progress_pct")),
            "schedule_state": schedule_state,
            "current_phase": current_phase,
            "unknown_schedule_items": unknown_sched,
            "unquantified_progress_items": unquantified,
            "window": {
                "earliest_date": earliest,
                "latest_date": latest,
                "span_days": span_days,
            },
        },
        "items": [dict(computed[it["id"]], progress_bar=progress_bar_str(computed[it["id"]]["progress_pct"]))
                  for it in items],
        "groups": groups,
        "milestones": ms_block,
        "gantt": gantt,
        "timeline": timeline,
        "coverage": coverage,
        "people": people_block,
        "sources": data.get("sources") or [],
        "inferred_fields": data.get("inferred_fields") or [],
        "diagnostics": diagnostics,
    }


def print_summary(out: dict) -> None:
    p, g, m = out["project"], out["gantt"], out["milestones"]
    print("== 进度引擎结论（基准日 %s，来自 %s ｜ 输入形态 %s）=="
          % (out["baseline"], out.get("baseline_source", "--baseline"),
             out.get("input_schema", ENGINE_ID)))
    print("项目：%s ｜ 条目 %d（工作项 %d / 里程碑 %d）"
          % (p["name"] or "-", p["counts"]["items"], p["counts"]["work_items"],
             p["counts"]["milestones"]))
    prog = p["progress"]
    print("整体进度：%s（口径 %s）"
          % (prog["formula"] or "-（无可计数依据）", prog["basis"] or prog.get("reason", "-")))
    for alt in prog.get("alternatives") or []:
        print("   备选口径：%s（%s）" % (alt["formula"], alt["basis"]))
    print("状态计数：%s" % p["status_counts"])
    print("延期工作项 %d ｜ 无计划日期 %d ｜ 进度未量化 %d"
          % (p["counts"]["delayed"], p["counts"]["unknown_schedule"],
             p["counts"]["unquantified_progress"]))
    for it in p["delayed_items"][:10]:
        print("   [延期] %s %s：逾期 %s 天（计划 %s）"
              % (it["id"], it["name"], it["delay_days"], it["planned_end"]))
    print("里程碑：%s" % m["narrative"])
    for it in m["overdue"]:
        print("   [逾期] %s %s：逾期 %s 天（锚定 %s）"
              % (it["id"], it["name"], it["delay_days"], it["anchor"]))
    for mid in m["unknown_schedule_ids"]:
        print("   [无计划日期] %s：无法判定延期（不上逾期色）" % mid)
    print("甘特：起点 %s（%s）｜ today 偏移 %s ｜ 条形 %d ｜ 出图建议 %s"
          % (g["project_start"], g["project_start_source"], g["today_offset_days"],
             g["bar_count"], g["schedule_material"]["gantt_recommended"]))
    if g.get("today_directive"):
        print("   甘特指令：%s ｜ 标题基准日串：%s" % (g["today_directive"], g["title_baseline"]))
    print("里程碑视图独立成图（日期侧条件 a）：%s（数量 %s，跨度 %s 天）"
          % (m["view"]["standalone_condition_a"], m["view"]["count"], m["view"]["span_days"]))
    if out["coverage"]:
        c = out["coverage"]
        print("分解树覆盖：%s ｜ 闭合 %s（%s）｜ 覆盖率 %s"
              % (c["progress_denominator_set"], c["closure_equation"],
                 "成立" if c["closure_ok"] else "不成立", c["coverage_formula"]))
    people = out.get("people") or {}
    print("人员维度覆盖率：%s（名册 %d 人）"
          % (people.get("coverage_formula") or "-", len(people.get("roster") or [])))
    print("推断字段：%d 项（报告 `## 元信息` 须汇总推断字段清单）"
          % len(out.get("inferred_fields") or []))
    for line in out["diagnostics"]["declarations"]:
        print("[声明] %s" % line)
    for line in out["diagnostics"]["warnings"]:
        print("[警告] %s" % line)


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="progress-engine.py",
        description=("日期与进度的唯一计算引擎：从 SQLite 关系模型（data/project.db）取数，"
                     "用 SQL 完成查询与聚合，输出可被报告直接引用的结构化 JSON"
                     "（状态 / 进度% / 延期天数 / 聚合 / 甘特参数）。"),
        epilog=("字段定义与约束的权威 = schema/project.sql（DDL）；业务含义与必填档位见 "
                "references/required-info.md；表单→数据库的装载与校验由 scripts/project-db.py "
                "承担；判定语义见 references/consistency-rules.md。Markdown 只引用本引擎输出，"
                "不重述算法。\n"
                "示例：\n"
                "  python3 project-db.py --load data/project-input.yaml\n"
                "  python3 progress-engine.py --db data/project.db --summary\n"
                "  python3 progress-engine.py --print-schema\n"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--db", help="项目数据库路径（关系模型，主输入；默认 data/project.db 由调用方给出）")
    ap.add_argument("--input", help="向后兼容的 JSON 输入（字段名见 --print-schema），`-` 表示 stdin")
    ap.add_argument("--baseline",
                    help=("基准日 D0（yyyy-mm-dd）；省略时取库/输入中的 project.baseline_date。"
                          "引擎不读系统时钟"))
    ap.add_argument("--out", help="输出 JSON 写入该文件（默认写 stdout）")
    ap.add_argument("--summary", action="store_true", help="额外打印人读结论摘要（stderr 之外的正文）")
    ap.add_argument("--quiet-json", action="store_true", help="只打印摘要、不打印 JSON（需配合 --summary）")
    ap.add_argument("--count-deferred", action="store_true",
                    help="把 deferred 勾选计入完成度分母（默认不计入，两种口径都会输出）")
    ap.add_argument("--strict", action="store_true",
                    help="存在未映射状态字面量时报错退出（默认记为 unknown 并在 diagnostics 列出）")
    ap.add_argument("--print-schema", action="store_true",
                    help="打印字段契约说明与最小可运行示例后退出")
    args = ap.parse_args()

    if args.print_schema:
        print(SCHEMA_DOC)
        print("最小示例（可存为 project-input.yaml 交给 project-db.py --load）：")
        print(json.dumps(EXAMPLE_INPUT, ensure_ascii=False, indent=2))
        return 0

    try:
        if args.db and args.input:
            raise EngineError("--db（关系模型，主路径）与 --input（兼容 JSON）互斥，一次只能给一个")
        if not args.db and not args.input:
            raise EngineError(
                "缺少输入：--db <项目数据库>（主路径，由 project-db.py --load 建库）"
                "或 --input <JSON>（向后兼容）；`--print-schema` 可查看字段契约")
        facts = None
        if args.db:
            data, facts = load_from_db(args.db)
            input_label = args.db
        else:
            data = load_input(args.input)
            input_label = args.input
        raw_baseline = args.baseline or data.get("baseline_date")
        baseline_source = "--baseline" if args.baseline else "project.baseline_date"
        if not raw_baseline:
            raise EngineError(
                "缺少基准日：既未传 --baseline yyyy-mm-dd，输入也没有 project.baseline_date"
                "（基准日必须显式给出，引擎不读系统时钟）")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(raw_baseline).strip()):
            raise EngineError(
                "基准日必须是零填充的 yyyy-mm-dd（与报告中写的基准日字面量逐字一致），"
                "来自 %s，收到 %r" % (baseline_source, raw_baseline))
        baseline = normalize_date(str(raw_baseline).strip(), baseline_source)[0]
        out = run(data, baseline, args.count_deferred, args.strict, input_label, facts)
        out["baseline_source"] = baseline_source
        if args.db:
            out["db"] = args.db
            out["db_schema_version"] = DB_SCHEMA_VERSION
    except EngineError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return 2

    payload = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out:
        pathlib.Path(args.out).write_text(payload + "\n", encoding="utf-8")
        print("已写出引擎结果：%s" % args.out)
    elif not args.quiet_json:
        print(payload)
    if args.summary:
        print_summary(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
