#!/usr/bin/env python3
"""project-db.py — 项目关键信息的**关系模型读写与查询引擎**（summarize-project）。

定位
----
本技能的项目关键信息以 **SQLite 关系模型**建模：字段定义、取值域与实体关联的权威是
`${SKILL_HOME}/schema/project.sql`（DDL），**校验由数据库约束承担**——装载即校验，
违规即报错。YAML 表单仍然是人工可写的**输入面**，本脚本把它装载进 SQLite；装载之后
**数据库是查询与校验的唯一事实源**（呈现层与引擎都从库里读，不再回读表单）。

核心原则：**具备强约束的数据不用 Markdown 的模糊描述来记录。**

生命周期（两种模式）
--------------------
* `--load`（默认）：**每次运行重建**。数据库是派生物，删旧建新、从最新输入全量装载，
  与技能"只读事实源、不管理数据"的定位一致。
* `--update`：**基于已有历史数据库按最新信息更新**（UPSERT 语义）。用于用户希望在
  历史库上增量演进的场合：已存在的主键行按新值更新、新行插入、本次输入未提及的历史行
  原样保留，并输出**变更摘要**（插入/更新/保留，逐字段列出变化）。

用法
----
    python3 project-db.py --init                       # 建库建表（DDL 落地）
    python3 project-db.py --load data/project-input.yaml
    python3 project-db.py --update data/project-input-delta.yaml
    python3 project-db.py --check
    python3 project-db.py --list-queries
    python3 project-db.py --query work-item-schedule --baseline 2026-04-06
    python3 project-db.py --sql "SELECT item_id, planned_end FROM work_items"
    python3 project-db.py --export-json data/progress-data.json
    python3 project-db.py --print-ddl

默认数据库落位 `data/project.db`（交付目录内，随交付目录一起交付、一起刷新），可用
`--db` 覆盖。

退出码：0 成功；3 **约束违规 / 完整性体检不通过**（与 R 档缺失同级阻断）；
2 输入错误（文件不可读 / 不是合法 YAML-JSON-CSV / 缺 DDL / 缺库）。

零第三方依赖：`sqlite3` 与 `csv` 都是标准库；YAML 读取优先用 PyYAML，缺失时回退到
内置的受限 YAML 子集解析器。
"""
from __future__ import annotations

import argparse
import csv
import datetime
import importlib.util
import json
import pathlib
import re
import sqlite3
import sys

TOOL_ID = "project-db/v1"
SCHEMA_VERSION = "project-db/v1"
INPUT_SCHEMA = "project-input/v1"
DEFAULT_DB = "data/project.db"
DDL_PATH = pathlib.Path(__file__).resolve().parent.parent / "schema" / "project.sql"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")

GROUPS = ("phases", "work_items", "milestones", "people", "features", "sources")
ID_FIELD = {
    "phases": "phase_id",
    "work_items": "item_id",
    "milestones": "milestone_id",
    "people": "owner_id",
    "features": "feature_id",
    "sources": "source_id",
}
ID_PREFIX = {"phases": "P", "work_items": "T", "milestones": "M",
             "people": "U", "features": "F", "sources": "S"}
SOURCE_KINDS = ("management-export", "user-form", "context", "repo")
COVER_GROUPS = ("phases", "work_items", "milestones", "people", "features")
TASK_STATES = ("completed", "in-progress", "not-started", "deferred", "unknown")

# 装载顺序 = 外键依赖顺序（父表先行），删除时倒序
LOAD_ORDER = ("people", "phases", "work_items", "work_item_deps", "milestones",
              "features", "sources", "source_covers", "repos", "repo_derive_fields",
              "coverage", "git_window", "status_map", "project", "inferred_fields")
PK_COLUMNS = {
    "people": ("owner_id",),
    "phases": ("phase_id",),
    "work_items": ("item_id",),
    "work_item_deps": ("item_id", "depends_on_item_id"),
    "milestones": ("milestone_id",),
    "features": ("feature_id",),
    "sources": ("source_id",),
    "source_covers": ("source_id", "entity_group"),
    "repos": ("repo_id",),
    "repo_derive_fields": ("repo_id", "field"),
    "coverage": ("id",),
    "git_window": ("id",),
    "status_map": ("status_literal",),
    "project": ("id",),
    "inferred_fields": (),        # 追加型：每次装载重建，不做 UPSERT
}


class InputError(Exception):
    """表单/CSV 不可读、非法，或缺 DDL / 缺库 → 退出码 2。"""


class ConstraintError(Exception):
    """数据库约束违规（可读原因已写入 message）→ 退出码 3。"""


# ── 表单读取（YAML / JSON / CSV）—— 本脚本是输入面的唯一读取者 ────────────────
def load_form(path: str) -> dict:
    """读项目输入表单（.yaml / .json，`-` 表示 stdin）→ dict。"""
    try:
        raw = sys.stdin.read() if path == "-" else pathlib.Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError("无法读取表单文件 %s：%s" % (path, exc))
    text = raw.lstrip()
    if text.startswith("{"):
        try:
            data = json.loads(raw)
        except ValueError as exc:
            raise InputError("表单不是合法 JSON：%s" % exc)
    else:
        data = load_yaml(raw)
    if not isinstance(data, dict):
        raise InputError("表单顶层必须是对象（含 project / work_items / milestones 等键）")
    declared = data.get("schema")
    if declared and declared != INPUT_SCHEMA:
        raise InputError("schema 不匹配：表单声明 %r，本装载器为 %r" % (declared, INPUT_SCHEMA))
    return normalize_dates(data)


def load_csv_dir(path: pathlib.Path) -> dict:
    """CSV 输入面：一个目录下 `<实体组>.csv`（表头 = 规范字段名），或单个 `<实体组>.csv`。"""
    data: dict = {}
    files = []
    if path.is_dir():
        files = sorted(p for p in path.iterdir() if p.suffix.lower() == ".csv")
        if not files:
            raise InputError("目录 %s 下没有任何 .csv（期望 <实体组>.csv）" % path)
    else:
        files = [path]
    for csv_path in files:
        group = csv_path.stem
        if group not in GROUPS and group != "project":
            raise InputError("CSV 文件名 %s 不是已知实体组（%s / project）"
                             % (csv_path.name, "、".join(GROUPS)))
        try:
            with csv_path.open(encoding="utf-8-sig", newline="") as fh:
                rows = [{k: (v if v != "" else None) for k, v in row.items() if k}
                        for row in csv.DictReader(fh)]
        except OSError as exc:
            raise InputError("无法读取 CSV %s：%s" % (csv_path, exc))
        if group == "project":
            if len(rows) != 1:
                raise InputError("project.csv 必须恰好一行（project 是单例实体）")
            data["project"] = rows[0]
        else:
            data[group] = rows
    return normalize_dates(data)


def read_input(path: str) -> dict:
    p = pathlib.Path(path) if path != "-" else None
    if p is not None and (p.is_dir() or p.suffix.lower() == ".csv"):
        return load_csv_dir(p)
    return load_form(path)


def normalize_dates(node):
    """YAML 解析出的 date/datetime 统一转写为 yyyy-mm-dd 字符串。"""
    if isinstance(node, dict):
        return {k: normalize_dates(v) for k, v in node.items()}
    if isinstance(node, list):
        return [normalize_dates(v) for v in node]
    if isinstance(node, datetime.datetime):
        return node.date().isoformat()
    if isinstance(node, datetime.date):
        return node.isoformat()
    return node


def load_yaml(raw: str) -> dict:
    try:
        import yaml  # type: ignore
    except ImportError:
        return mini_yaml(raw)
    try:
        return yaml.safe_load(raw) or {}
    except Exception as exc:                       # noqa: BLE001 - 解析异常归为输入错误
        raise InputError("表单不是合法 YAML：%s" % exc)


def mini_yaml(raw: str):
    """受限 YAML 子集解析器（无 PyYAML 时的兜底）。

    支持：块映射、块序列（标量项与映射项）、行内空集合 `[]`/`{}`、行内简单列表
    `[a, b]` 与行内简单映射 `{k: v}`、`#` 注释、单/双引号标量、int/float/bool/null。
    不支持锚点、多行标量、复杂嵌套流式结构 —— 本技能的表单模板不使用这些。
    """
    lines = []
    for lineno, line in enumerate(raw.splitlines(), start=1):
        stripped = strip_comment(line)
        if stripped.strip() == "":
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        lines.append((lineno, indent, stripped.strip()))
    value, idx = _parse_block(lines, 0, lines[0][1] if lines else 0)
    if idx != len(lines):
        raise InputError("YAML 第 %d 行缩进结构无法解析（受限解析器）" % lines[idx][0])
    return value or {}


def strip_comment(line: str) -> str:
    out, quote = [], None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            out.append(ch)
            continue
        if ch == "#":
            break
        out.append(ch)
    return "".join(out).rstrip()


def _parse_block(lines, idx: int, indent: int):
    if idx >= len(lines):
        return None, idx
    if lines[idx][2].startswith("- "):
        return _parse_seq(lines, idx, indent)
    return _parse_map(lines, idx, indent)


def _parse_map(lines, idx: int, indent: int):
    out = {}
    while idx < len(lines):
        lineno, ind, text = lines[idx]
        if ind < indent:
            break
        if ind > indent:
            raise InputError("YAML 第 %d 行缩进异常（受限解析器）" % lineno)
        if ":" not in text:
            raise InputError("YAML 第 %d 行缺少 `key:`（受限解析器）：%s" % (lineno, text))
        key, _, rest = text.partition(":")
        key, rest = key.strip().strip("\"'"), rest.strip()
        idx += 1
        if rest:
            out[key] = scalar(rest)
            continue
        if idx < len(lines) and lines[idx][1] > indent:
            out[key], idx = _parse_block(lines, idx, lines[idx][1])
        elif idx < len(lines) and lines[idx][1] == indent and lines[idx][2].startswith("- "):
            out[key], idx = _parse_seq(lines, idx, indent)
        else:
            out[key] = None
    return out, idx


def _parse_seq(lines, idx: int, indent: int):
    out = []
    while idx < len(lines):
        lineno, ind, text = lines[idx]
        if ind < indent or not text.startswith("- "):
            break
        if ind > indent:
            raise InputError("YAML 第 %d 行序列缩进异常（受限解析器）" % lineno)
        body = text[2:].strip()
        idx += 1
        if ":" in body and not body.startswith(("[", "{", '"', "'")):
            item, idx = _parse_seq_map(lines, idx, ind, body)
            out.append(item)
        elif body:
            out.append(scalar(body))
        elif idx < len(lines) and lines[idx][1] > ind:
            child, idx = _parse_block(lines, idx, lines[idx][1])
            out.append(child)
        else:
            out.append(None)
    return out, idx


def _parse_seq_map(lines, idx: int, ind: int, body: str):
    """序列项是映射：首个 `key: value` 在 `- ` 之后，后续同缩进行继续该映射。"""
    item = {}
    key, _, rest = body.partition(":")
    key, rest = key.strip().strip("\"'"), rest.strip()
    if rest:
        item[key] = scalar(rest)
        pending_key = None
    else:
        pending_key = key
    child_indent = None
    while idx < len(lines):
        _, ind2, text2 = lines[idx]
        if ind2 <= ind:
            break
        if child_indent is None:
            child_indent = ind2
        if ind2 != child_indent:
            if pending_key is not None:
                nested, idx = _parse_block(lines, idx, ind2)
                item[pending_key] = nested
                pending_key = None
                continue
            break
        if pending_key is not None and text2.startswith("- "):
            item[pending_key], idx = _parse_seq(lines, idx, ind2)
            pending_key = None
            continue
        rest_map, idx = _parse_map(lines, idx, child_indent)
        item.update(rest_map)
        pending_key = None
    if pending_key is not None:
        item[pending_key] = None
    return item, idx


def scalar(text: str):
    text = text.strip()
    if text in ("[]", "{}"):
        return [] if text == "[]" else {}
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [scalar(p) for p in split_flow(inner)] if inner else []
    if text.startswith("{") and text.endswith("}"):
        inner, out = text[1:-1].strip(), {}
        for part in split_flow(inner):
            if ":" in part:
                k, _, v = part.partition(":")
                out[k.strip().strip("\"'")] = scalar(v)
        return out
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    low = text.lower()
    if low in ("null", "~", ""):
        return None
    if low == "true":
        return True
    if low == "false":
        return False
    if re.match(r"^-?\d+$", text):
        return int(text)
    if re.match(r"^-?\d+\.\d+$", text):
        return float(text)
    return text


def split_flow(inner: str):
    parts, depth, buf, quote = [], 0, [], None
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
            continue
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if "".join(buf).strip():
        parts.append("".join(buf).strip())
    return parts


# ── 工具 ────────────────────────────────────────────────────────────────────────
def blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def text(value):
    return None if blank(value) else str(value).strip()


def as_rows(data: dict, group: str) -> list:
    rows = data.get(group)
    if blank(rows):
        return []
    if not isinstance(rows, list):
        raise InputError("%s 必须是数组（每行一条记录）" % group)
    out = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise InputError("%s[%d] 必须是对象（键 = 规范字段名）" % (group, i))
        out.append(row)
    return out


def as_list(value):
    if blank(value):
        return []
    return value if isinstance(value, list) else [value]


def engine_status_map() -> dict:
    """归一化映射表的唯一权威在 progress-engine.py（DEFAULT_STATUS_MAP），此处复用、不复制。"""
    engine = pathlib.Path(__file__).resolve().parent / "progress-engine.py"
    if not engine.exists():
        return {}
    try:
        spec = importlib.util.spec_from_file_location("_speckit_progress_engine", engine)
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("_speckit_progress_engine", module)
        spec.loader.exec_module(module)                     # type: ignore[union-attr]
        return dict(getattr(module, "DEFAULT_STATUS_MAP", {}) or {})
    except Exception:                                       # noqa: BLE001 - 缺失时留 NULL
        return {}


def normalize_status(raw, smap: dict):
    """源字面量 → 归一化态；未映射返回 None（列留 NULL，引擎侧仍会记 unknown 并告警）。"""
    if blank(raw):
        return None
    key = str(raw).strip().lower()
    key = re.sub(r"^\[([xX~pP ]?)\]$", lambda m: "[%s]" % m.group(1).lower(), key)
    return smap.get(key)


# ── 表单 → 关系行（含 I 档推断留痕） ────────────────────────────────────────────
def form_to_tables(data: dict, input_label: str) -> dict:
    """把表单对象展开成各表的行集合；I 档推断值逐条登记到 inferred_fields。"""
    project = data.get("project")
    if project is None:
        project = {}
    if not isinstance(project, dict):
        raise InputError("project 必须是对象（含 project_name / baseline_date）")
    entities = {g: as_rows(data, g) for g in GROUPS}
    smap = engine_status_map()
    inferred: list = []

    def mark(field: str, value, why: str):
        inferred.append({"field": field, "inferred_value": value, "inferred_from": why})

    # ID 解析（缺失按出现顺序生成，并留痕）
    resolved: dict = {}
    for group in GROUPS:
        id_field = ID_FIELD[group]
        for i, row in enumerate(entities[group]):
            raw_id = row.get(id_field)
            if blank(raw_id):
                gen = "%s-%02d" % (ID_PREFIX[group], i + 1)
                mark("%s[%d].%s" % (group, i, id_field), gen,
                     "按 %s 中的出现顺序生成（第 %d 行）" % (group, i + 1))
                resolved[id(row)] = gen
                row["__generated_id"] = True
            else:
                resolved[id(row)] = str(raw_id).strip()

    # sources[] 与条目 source 推断
    src_rows = []
    for i, row in enumerate(entities["sources"]):
        sid = resolved[id(row)]
        kind = text(row.get("source_kind"))
        if kind is None:
            kind = "user-form"
            mark("sources[%s].source_kind" % sid, kind, "表单未声明来源性质，取 user-form")
        ref = text(row.get("source_ref"))
        if ref is None:
            ref = "表单填写"
            mark("sources[%s].source_ref" % sid, ref, "表单未声明来源位置，记「表单填写」")
        covers = [str(c).strip() for c in as_list(row.get("covers")) if not blank(c)]
        src_rows.append({"source_id": sid, "source_kind": kind, "source_ref": ref,
                         "covers": covers, "row_order": i + 1})
    default_source = next(("%s（%s）" % (s["source_ref"], s["source_kind"])
                           for s in src_rows if s["source_kind"] != "repo"), None)
    if default_source is None:
        default_source = "表单填写（%s）" % input_label
        if not src_rows:
            mark("sources[]", "user-form",
                 "表单未声明来源 → 全部条目来源记为「表单填写（%s）」" % input_label)

    def source_of(group: str, row: dict, ident: str) -> str:
        explicit = text(row.get("source"))
        if explicit:
            return explicit
        covering = [s for s in src_rows if group in s["covers"]]
        value = ("%s（%s）" % (covering[0]["source_ref"], covering[0]["source_kind"])
                 if covering else default_source)
        mark("%s[%s].source" % (group, ident), value, "条目未写来源，按 sources[] 声明推断")
        return value

    # people
    people_rows = []
    for i, row in enumerate(entities["people"]):
        uid = resolved[id(row)]
        name = text(row.get("owner_name"))
        if name is None:
            name = uid
            mark("people[%s].owner_name" % uid, uid, "人员名缺失，取人员标识兜底呈现")
        role = text(row.get("owner_role"))
        if role is None:
            role = "未记录"
            mark("people[%s].owner_role" % uid, role, "材料未记录角色，取合法终态（不臆断）")
        people_rows.append({"owner_id": uid, "owner_name": name, "owner_role": role,
                            "row_order": i + 1})

    # phases
    phase_rows = []
    for i, row in enumerate(entities["phases"]):
        pid = resolved[id(row)]
        name = text(row.get("phase_name"))
        if name is None:
            name = pid
            mark("phases[%s].phase_name" % pid, pid, "阶段名缺失，取阶段标识兜底")
        order = row.get("phase_order")
        if blank(order):
            order = i + 1
            mark("phases[%s].phase_order" % pid, order, "按表单中阶段出现顺序推断")
        phase_rows.append({"phase_id": pid, "phase_name": name, "phase_order": int(order),
                           "source": source_of("phases", row, pid),
                           "inferred": 1 if row.get("__generated_id") else 0,
                           "row_order": i + 1})

    # work_items + deps
    item_rows, dep_rows = [], []
    for i, row in enumerate(entities["work_items"]):
        iid = resolved[id(row)]
        checks = row.get("checks") if isinstance(row.get("checks"), dict) else {}
        raw_status = row.get("status")
        item_rows.append({
            "item_id": iid,
            "item_name": text(row.get("item_name")),
            "phase_id": text(row.get("phase_id")),
            "owner_id": text(row.get("owner_id")),
            "planned_start": text(row.get("planned_start")),
            "planned_end": text(row.get("planned_end")),
            "actual_start": text(row.get("actual_start")),
            "actual_end": text(row.get("actual_end")),
            "status": raw_status if not blank(raw_status) else None,
            "status_norm": normalize_status(raw_status, smap),
            "progress_pct": row.get("progress_pct") if not blank(row.get("progress_pct")) else None,
            "progress_source": text(row.get("progress_source")),
            "checks_done": checks.get("done") if not blank(checks) else None,
            "checks_open": checks.get("open") if not blank(checks) else None,
            "checks_deferred": checks.get("deferred") if not blank(checks) else None,
            "checks_excluded": checks.get("excluded") if not blank(checks) else None,
            "weight": row.get("weight") if not blank(row.get("weight")) else None,
            "weight_source": text(row.get("weight_source")),
            "risk_note": text(row.get("risk_note")),
            "source": source_of("work_items", row, iid),
            "inferred": 1 if row.get("__generated_id") else 0,
            "row_order": i + 1,
        })
        for j, dep in enumerate(as_list(row.get("depends_on"))):
            if blank(dep):
                continue
            dep_rows.append({"item_id": iid, "depends_on_item_id": str(dep).strip(),
                             "dep_order": j + 1})

    # milestones
    ms_rows = []
    for i, row in enumerate(entities["milestones"]):
        mid = resolved[id(row)]
        raw_status = row.get("status")
        ms_rows.append({
            "milestone_id": mid,
            "milestone_name": text(row.get("milestone_name")),
            "planned_date": text(row.get("planned_date")),
            "actual_date": text(row.get("actual_date")),
            "achieved_evidence": text(row.get("achieved_evidence")),
            "status": raw_status if not blank(raw_status) else None,
            "status_norm": None,          # 里程碑归一化态由引擎按锚定日与基准日判定
            "anchor_item_id": text(row.get("anchor_item_id")),
            "owner_id": text(row.get("owner_id")),
            "risk_note": text(row.get("risk_note")),
            "source": source_of("milestones", row, mid),
            "inferred": 1 if row.get("__generated_id") else 0,
            "row_order": i + 1,
        })

    # features
    feat_rows = []
    for i, row in enumerate(entities["features"]):
        fid = resolved[id(row)]
        raw_status = row.get("status")
        feat_rows.append({
            "feature_id": fid,
            "feature_name": text(row.get("feature_name")),
            "status": raw_status if not blank(raw_status) else None,
            "status_norm": normalize_status(raw_status, smap),
            "owner_id": text(row.get("owner_id")),
            "source": source_of("features", row, fid),
            "inferred": 1 if row.get("__generated_id") else 0,
            "row_order": i + 1,
        })

    # repos（opt-in）
    repo_rows, derive_rows = [], []
    for i, repo in enumerate(as_list(project.get("repos"))):
        if not isinstance(repo, dict):
            raise InputError("project.repos[%d] 必须是对象" % i)
        rid = text(repo.get("repo_id")) or "repo-%02d" % (i + 1)
        repo_rows.append({"repo_id": rid, "repo_path": text(repo.get("repo_path")),
                          "repo_role": text(repo.get("repo_role")), "row_order": i + 1})
        for field in as_list(repo.get("derive_fields")):
            if not blank(field):
                derive_rows.append({"repo_id": rid, "field": str(field).strip()})

    cov = data.get("coverage") if isinstance(data.get("coverage"), dict) else None
    cov_rows = []
    if cov:
        cov_rows = [{"id": 1,
                     "candidate_total": cov.get("candidate_total"),
                     "excluded": int(cov.get("excluded") or 0),
                     "granularity_truncated": int(cov.get("granularity_truncated") or 0),
                     "unattributed": int(cov.get("unattributed") or 0),
                     "source_label": text(cov.get("source_label"))}]
    gw = data.get("git_window") if isinstance(data.get("git_window"), dict) else None
    gw_rows = []
    if gw:
        gw_rows = [{"id": 1, "commit_count": gw.get("commit_count"),
                    "first_commit": text(gw.get("first_commit")),
                    "last_commit": text(gw.get("last_commit"))}]
    smap_rows = []
    override = data.get("status_map") if isinstance(data.get("status_map"), dict) else {}
    for key, value in (override or {}).items():
        smap_rows.append({"status_literal": str(key).strip().lower(), "status_norm": value})

    tables = {
        "project": [{"id": 1,
                     "project_name": text(project.get("project_name")),
                     "project_desc": text(project.get("project_desc")),
                     "baseline_date": text(project.get("baseline_date")),
                     "project_start": text(project.get("project_start"))}],
        "people": people_rows,
        "phases": phase_rows,
        "work_items": item_rows,
        "work_item_deps": dep_rows,
        "milestones": ms_rows,
        "features": feat_rows,
        "sources": [{k: v for k, v in s.items() if k != "covers"} for s in src_rows],
        "source_covers": [{"source_id": s["source_id"], "entity_group": g}
                          for s in src_rows for g in s["covers"]],
        "repos": repo_rows,
        "repo_derive_fields": derive_rows,
        "coverage": cov_rows,
        "git_window": gw_rows,
        "status_map": smap_rows,
        "inferred_fields": [{"field": x["field"],
                             "inferred_value": (None if x["inferred_value"] is None
                                                else str(x["inferred_value"])),
                             "inferred_from": x["inferred_from"]}
                            for x in inferred],
    }
    # 表单里已带的推断留痕（例如上游摄取阶段登记的）一并入库，不丢
    for x in (data.get("inferred_fields") or []):
        if isinstance(x, dict) and x.get("field") and x.get("inferred_from"):
            tables["inferred_fields"].insert(0, {
                "field": str(x["field"]),
                "inferred_value": (None if x.get("inferred_value") is None
                                   else str(x.get("inferred_value"))),
                "inferred_from": str(x["inferred_from"]),
            })
    return tables


# ── 约束违规的可读化（SQLite 的 CHECK 报错不带列名，此处按 DDL 规则逐条指认） ──
def date_ok(value) -> bool:
    if value is None:
        return True
    s = str(value)
    if not DATE_RE.match(s):
        return False
    try:
        datetime.date.fromisoformat(s)
    except ValueError:
        return False
    return True


DATE_COLUMNS = {
    "project": ("baseline_date", "project_start"),
    "work_items": ("planned_start", "planned_end", "actual_start", "actual_end"),
    "milestones": ("planned_date", "actual_date"),
    "git_window": ("first_commit", "last_commit"),
}
NOT_NULL_COLUMNS = {
    "project": ("project_name", "baseline_date"),
    "people": ("owner_name",),
    "phases": ("phase_name",),
    "work_items": ("item_name",),
    "milestones": ("milestone_name",),
    "features": ("feature_name",),
    "sources": ("source_kind", "source_ref"),
    "repos": ("repo_path",),
    "inferred_fields": ("field", "inferred_from"),
}
ENUM_COLUMNS = {
    "work_items": {"status_norm": TASK_STATES},
    "features": {"status_norm": TASK_STATES},
    "milestones": {"status_norm": ("achieved", "pending", "at-risk", "unknown-schedule")},
    "sources": {"source_kind": SOURCE_KINDS},
    "source_covers": {"entity_group": COVER_GROUPS},
    "status_map": {"status_norm": TASK_STATES},
}
FK_COLUMNS = {
    "work_items": {"phase_id": ("phases", "phase_id"), "owner_id": ("people", "owner_id")},
    "milestones": {"anchor_item_id": ("work_items", "item_id"),
                   "owner_id": ("people", "owner_id")},
    "features": {"owner_id": ("people", "owner_id")},
    "work_item_deps": {"item_id": ("work_items", "item_id"),
                       "depends_on_item_id": ("work_items", "item_id")},
    "source_covers": {"source_id": ("sources", "source_id")},
    "repo_derive_fields": {"repo_id": ("repos", "repo_id")},
}
GLOBAL_ID_COLUMN = {
    "phases": "phase_id", "work_items": "item_id", "milestones": "milestone_id",
    "people": "owner_id", "features": "feature_id", "sources": "source_id",
}
# entity_ids.entity_kind 的取值（与 DDL 的 CHECK 逐字一致）
ENTITY_KIND = {
    "phases": "phase", "work_items": "work_item", "milestones": "milestone",
    "people": "person", "features": "feature", "sources": "source",
}


def explain_violation(conn: sqlite3.Connection, table: str, row: dict, exc: Exception) -> str:
    """把 sqlite3 的约束报错翻译成「哪一行 / 哪个字段 / 违了哪条规则 / 怎么改」。"""
    where = "%s(%s)" % (table, ", ".join("%s=%r" % (k, row.get(k)) for k in PK_COLUMNS[table]))
    # 1) 非空
    for col in NOT_NULL_COLUMNS.get(table, ()):
        if blank(row.get(col)):
            return ("%s：%s 为空 —— DDL 约束 NOT NULL（必填-阻断档）。补齐该字段后重新装载。"
                    % (where, col))
    # 2) 全局 ID 唯一 + ID 字面量
    id_col = GLOBAL_ID_COLUMN.get(table)
    if id_col:
        value = row.get(id_col)
        if value is not None and not ID_RE.match(str(value)):
            return ("%s：%s=%r 不是合法标识 —— DDL 约束 entity_ids.entity_id 只允许字母/数字/"
                    "`_`/`-`/`.`，且以字母或数字开头。" % (where, id_col, value))
        hit = conn.execute(
            "SELECT entity_kind, id_field FROM entity_ids WHERE entity_id = ?",
            (value,)).fetchone()
        if hit:
            if hit[0] == ENTITY_KIND.get(table):
                return ("%s：%s=%r 在本实体内重复 —— DDL 约束 PRIMARY KEY（同一实体不得两行同号）。"
                        % (where, id_col, value))
            return ("%s：%s=%r 与已登记的 %s.%s 撞号 —— DDL 约束 `*_id` 跨实体**全局唯一**"
                    "（entity_ids 主键 + 各表 AFTER INSERT 触发器）。换一个唯一标识后重新装载。"
                    % (where, id_col, value, hit[0], hit[1]))
    # 3) 外键
    for col, (target_table, target_col) in FK_COLUMNS.get(table, {}).items():
        value = row.get(col)
        if blank(value):
            continue
        exists = conn.execute("SELECT 1 FROM %s WHERE %s = ?" % (target_table, target_col),
                              (str(value),)).fetchone()
        if not exists:
            return ("%s：%s=%r 指向未声明的实体 —— DDL 约束 FOREIGN KEY → %s.%s（关联断裂）。"
                    "先声明该 %s，或改成已声明的标识。"
                    % (where, col, value, target_table, target_col, target_table))
    # 4) 日期字面量与日历日
    for col in DATE_COLUMNS.get(table, ()):
        if not date_ok(row.get(col)):
            return ("%s：%s=%r 不是合法日期 —— DDL 约束要求零填充 `yyyy-mm-dd` 且必须是真实存在"
                    "的日历日（歧义写法一律不采信、不猜）。" % (where, col, row.get(col)))
    # 5) 枚举
    for col, allowed in ENUM_COLUMNS.get(table, {}).items():
        value = row.get(col)
        if value is not None and value not in allowed:
            return ("%s：%s=%r 不在允许取值内 —— DDL 约束 CHECK IN (%s)。"
                    % (where, col, value, "、".join(allowed)))
    # 6) 表级组合约束
    if table == "work_items":
        if row.get("progress_pct") is not None and blank(row.get("progress_source")):
            return ("%s：给了 progress_pct=%r 却无 progress_source —— DDL 约束「无出处的百分比"
                    "视为编造」。补出处，或删掉该百分比。" % (where, row.get("progress_pct")))
        if row.get("weight") is not None and blank(row.get("weight_source")):
            return ("%s：给了 weight=%r 却无 weight_source —— DDL 约束「无依据的权重视为编造」。"
                    % (where, row.get("weight")))
        pct = row.get("progress_pct")
        if pct is not None and not (0 <= float(pct) <= 100):
            return "%s：progress_pct=%r 超出 0–100 —— DDL 约束 CHECK。" % (where, pct)
        chk = [row.get(k) for k in ("checks_done", "checks_open", "checks_deferred",
                                    "checks_excluded")]
        if any(v is not None for v in chk):
            if any(v is not None and int(v) < 0 for v in chk):
                return "%s：checks 计数出现负数 —— DDL 约束 CHECK >= 0。" % where
            if sum(int(v or 0) for v in chk[:3]) == 0:
                return ("%s：checks 全为 0 —— DDL 约束禁止把「无可计数依据」伪装成「0%% 完成」；"
                        "没有勾选依据时整组留空即可（进度会记 NULL）。" % where)
    if table == "work_item_deps" and row.get("item_id") == row.get("depends_on_item_id"):
        return "%s：depends_on 指向自身 —— DDL 约束 CHECK 禁止自依赖。" % where
    if table == "phases" and row.get("phase_order") is not None:
        dup = conn.execute("SELECT phase_id FROM phases WHERE phase_order = ?",
                           (row.get("phase_order"),)).fetchone()
        if dup:
            return ("%s：phase_order=%r 与阶段 %s 重复 —— DDL 约束 UNIQUE（阶段次序不可并列）。"
                    % (where, row.get("phase_order"), dup[0]))
    if table == "project" and row.get("id") != 1:
        return "%s：project 是单例实体 —— DDL 约束 CHECK (id = 1)，只允许一行。" % where
    return "%s：数据库拒绝写入 —— %s（规则见 schema/project.sql）" % (where, exc)


# ── 建库 / 装载 / 更新 ──────────────────────────────────────────────────────────
def read_ddl() -> str:
    if not DDL_PATH.exists():
        raise InputError("找不到 DDL 文件 %s —— 字段定义的权威就是它，缺失无法建库" % DDL_PATH)
    return DDL_PATH.read_text(encoding="utf-8")


def connect(path: str, must_exist: bool) -> sqlite3.Connection:
    p = pathlib.Path(path)
    if must_exist and not p.exists():
        raise InputError("数据库不存在：%s（先跑 --init 或 --load）" % path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    # SQLite 默认关闭外键强制，且该设置是**连接级**的、不随文件持久化 —— 每个连接都要开
    conn.execute("PRAGMA foreign_keys = ON")
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise InputError("无法启用 PRAGMA foreign_keys —— 外键约束会退化为注释，拒绝继续")
    return conn


def init_db(path: str, fresh: bool) -> sqlite3.Connection:
    p = pathlib.Path(path)
    if fresh and p.exists():
        p.unlink()
    conn = connect(path, must_exist=False)
    conn.executescript(read_ddl())
    conn.execute("PRAGMA foreign_keys = ON")
    now = datetime.datetime.now().isoformat(timespec="seconds")
    conn.executemany(
        "INSERT INTO schema_meta (meta_key, meta_value) VALUES (?, ?) "
        "ON CONFLICT(meta_key) DO UPDATE SET meta_value = excluded.meta_value",
        [("schema_version", SCHEMA_VERSION), ("input_schema", INPUT_SCHEMA),
         ("ddl_path", str(DDL_PATH)), ("initialized_at", now)])
    conn.commit()
    return conn


def insert_rows(conn: sqlite3.Connection, table: str, rows: list) -> None:
    for row in rows:
        cols = [k for k in row]
        sql = "INSERT INTO %s (%s) VALUES (%s)" % (
            table, ", ".join(cols), ", ".join("?" for _ in cols))
        try:
            conn.execute(sql, [row[c] for c in cols])
        except sqlite3.IntegrityError as exc:
            raise ConstraintError(explain_violation(conn, table, row, exc))
        except sqlite3.Error as exc:
            raise ConstraintError("%s 写入失败：%s" % (table, exc))


def load_tables(conn: sqlite3.Connection, tables: dict) -> dict:
    """全量装载（重建语义）。约束违规立即抛 ConstraintError（含可读原因）。"""
    for table in reversed(LOAD_ORDER):
        conn.execute("DELETE FROM %s" % table)
    conn.execute("DELETE FROM entity_ids")
    for table in LOAD_ORDER:
        insert_rows(conn, table, tables.get(table) or [])
    conn.commit()
    return {t: len(tables.get(t) or []) for t in LOAD_ORDER}


def upsert_tables(conn: sqlite3.Connection, tables: dict) -> dict:
    """基于已有历史库按最新信息更新（UPSERT），并给出逐表变更摘要。"""
    summary = {}
    # inferred_fields 是追加型留痕表：本次装载的推断记录整表重建，避免历史重复堆积
    conn.execute("DELETE FROM inferred_fields")
    for table in LOAD_ORDER:
        rows = tables.get(table) or []
        pk = PK_COLUMNS[table]
        inserted, updated, unchanged, changes = 0, 0, 0, []
        before = conn.execute("SELECT count(*) FROM %s" % table).fetchone()[0]
        for row in rows:
            if not pk:
                insert_rows(conn, table, [row])
                inserted += 1
                continue
            where = " AND ".join("%s = ?" % c for c in pk)
            old = conn.execute("SELECT * FROM %s WHERE %s" % (table, where),
                               [row[c] for c in pk]).fetchone()
            cols = [k for k in row]
            if old is None:
                insert_rows(conn, table, [row])
                inserted += 1
                continue
            diff = {c: (old[c], row[c]) for c in cols
                    if c not in pk and c != "row_order" and old[c] != row[c]}
            assigns = [c for c in cols if c not in pk]
            sql = ("INSERT INTO %s (%s) VALUES (%s) ON CONFLICT(%s) DO UPDATE SET %s"
                   % (table, ", ".join(cols), ", ".join("?" for _ in cols),
                      ", ".join(pk), ", ".join("%s = excluded.%s" % (c, c) for c in assigns)))
            try:
                conn.execute(sql, [row[c] for c in cols])
            except sqlite3.IntegrityError as exc:
                raise ConstraintError(explain_violation(conn, table, row, exc))
            if diff:
                updated += 1
                changes.append({"key": {c: row[c] for c in pk},
                                "fields": {c: {"old": v[0], "new": v[1]}
                                           for c, v in diff.items()}})
            else:
                unchanged += 1
        after = conn.execute("SELECT count(*) FROM %s" % table).fetchone()[0]
        summary[table] = {"input_rows": len(rows), "inserted": inserted, "updated": updated,
                          "unchanged": unchanged,
                          # 本次输入未提及、但历史库里保留下来的行
                          "retained_from_history": max(0, before - (updated + unchanged)),
                          "rows_before": before, "rows_after": after,
                          "changes": changes}
    conn.commit()
    return summary


# ── 完整性体检（--check）：FK / 枚举 / 日期 / 孤儿 / 唯一性 / 组级必填 ──────────
CHECK_QUERIES = [
    ("foreign_key_check", "PRAGMA foreign_key_check", "外键断裂（数据库级复核）"),
    ("orphans", "SELECT * FROM v_orphans", "孤儿引用（外键目标不存在）"),
    ("bad_date", """
        SELECT 'work_items' AS tbl, item_id AS entity_id, 'planned_end' AS col, planned_end AS value
          FROM work_items
         WHERE planned_end IS NOT NULL
           AND NOT (planned_end GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                    AND date(julianday(planned_end)) = planned_end)
        UNION ALL
        SELECT 'milestones', milestone_id, 'planned_date', planned_date
          FROM milestones
         WHERE planned_date IS NOT NULL
           AND NOT (planned_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                    AND date(julianday(planned_date)) = planned_date)
     """, "日期字面量或日历日非法"),
    ("bad_enum", """
        SELECT 'work_items' AS tbl, item_id AS entity_id, status_norm AS value
          FROM work_items
         WHERE status_norm IS NOT NULL
           AND status_norm NOT IN ('completed','in-progress','not-started','deferred','unknown')
        UNION ALL
        SELECT 'milestones', milestone_id, status_norm
          FROM milestones
         WHERE status_norm IS NOT NULL
           AND status_norm NOT IN ('achieved','pending','at-risk','unknown-schedule')
     """, "归一化状态取值越界"),
    ("dup_global_id", """
        SELECT entity_id, count(*) AS n FROM entity_ids GROUP BY entity_id HAVING n > 1
     """, "`*_id` 跨实体撞号"),
    ("unregistered_id", """
        SELECT 'work_items' AS tbl, item_id AS entity_id FROM work_items
         WHERE item_id NOT IN (SELECT entity_id FROM entity_ids)
        UNION ALL
        SELECT 'milestones', milestone_id FROM milestones
         WHERE milestone_id NOT IN (SELECT entity_id FROM entity_ids)
        UNION ALL
        SELECT 'phases', phase_id FROM phases
         WHERE phase_id NOT IN (SELECT entity_id FROM entity_ids)
        UNION ALL
        SELECT 'people', owner_id FROM people
         WHERE owner_id NOT IN (SELECT entity_id FROM entity_ids)
     """, "ID 未登记进全局命名空间（触发器被绕过）"),
    ("self_dep", """
        SELECT item_id, depends_on_item_id FROM work_item_deps
         WHERE item_id = depends_on_item_id
     """, "自依赖"),
    ("pct_without_source", """
        SELECT item_id, progress_pct FROM work_items
         WHERE progress_pct IS NOT NULL
           AND (progress_source IS NULL OR trim(progress_source) = '')
     """, "明写百分比无出处"),
]


def run_check(conn: sqlite3.Connection) -> dict:
    report = {"tool": TOOL_ID, "schema_version": SCHEMA_VERSION,
              "foreign_keys_pragma": conn.execute("PRAGMA foreign_keys").fetchone()[0],
              "entity_counts": dict(conn.execute("SELECT * FROM v_entity_counts").fetchone()),
              "findings": [], "status": "ok"}
    for name, sql, why in CHECK_QUERIES:
        rows = [dict(r) for r in conn.execute(sql).fetchall()]
        if rows:
            report["findings"].append({"check": name, "why": why, "rows": rows})
    # 组级必填（跨表条件，表级 CHECK 无法表达 → 在此以 SQL 断言承担）
    counts = report["entity_counts"]
    if counts["work_items"] == 0 and counts["milestones"] == 0:
        report["findings"].append({
            "check": "group_required",
            "why": "work_items 与 milestones 两组皆空 → 五章节骨架无法成立（组级必填-阻断）",
            "rows": [{"work_items": 0, "milestones": 0}]})
    if conn.execute("SELECT count(*) FROM project").fetchone()[0] != 1:
        report["findings"].append({
            "check": "project_singleton",
            "why": "project 表必须恰好一行（项目名与基准日是 R 档必填）",
            "rows": [{"rows": conn.execute("SELECT count(*) FROM project").fetchone()[0]}]})
    if report["foreign_keys_pragma"] != 1:
        report["findings"].append({
            "check": "foreign_keys_off",
            "why": "PRAGMA foreign_keys 未开启 → 外键约束退化为注释",
            "rows": [{"pragma": report["foreign_keys_pragma"]}]})
    report["status"] = "ok" if not report["findings"] else "failed"
    report["unknown_schedule"] = [dict(r) for r in
                                  conn.execute("SELECT * FROM v_unknown_schedule").fetchall()]
    return report


# ── 导出引擎输入（DB → project-input/v1 JSON；字段名不换） ─────────────────────
def export_json(conn: sqlite3.Connection) -> dict:
    prj = conn.execute("SELECT * FROM project WHERE id = 1").fetchone()
    if prj is None:
        raise ConstraintError("project 表为空 —— 先装载（--load）再导出")
    repos = []
    for r in conn.execute("SELECT * FROM repos ORDER BY row_order").fetchall():
        derive = [x[0] for x in conn.execute(
            "SELECT field FROM repo_derive_fields WHERE repo_id = ? ORDER BY field",
            (r["repo_id"],)).fetchall()]
        entry = {"repo_id": r["repo_id"], "repo_path": r["repo_path"]}
        if r["repo_role"]:
            entry["repo_role"] = r["repo_role"]
        if derive:
            entry["derive_fields"] = derive
        repos.append(entry)

    phases = [{"phase_id": r["phase_id"], "phase_name": r["phase_name"],
               "phase_order": r["phase_order"]}
              for r in conn.execute("SELECT * FROM phases ORDER BY row_order").fetchall()]

    work_items = []
    for r in conn.execute("SELECT * FROM work_items ORDER BY row_order").fetchall():
        item = {"item_id": r["item_id"], "item_name": r["item_name"],
                "phase_id": r["phase_id"], "owner_id": r["owner_id"],
                "status": r["status"], "source": r["source"]}
        for col in ("planned_start", "planned_end", "actual_start", "actual_end"):
            if r[col] is not None:
                item[col] = r[col]
        if r["progress_pct"] is not None:
            item["progress_pct"] = r["progress_pct"]
            item["progress_source"] = r["progress_source"]
        checks = {k: r["checks_%s" % k] for k in ("done", "open", "deferred", "excluded")
                  if r["checks_%s" % k] is not None}
        if checks:
            item["checks"] = checks
        if r["weight"] is not None:
            item["weight"] = r["weight"]
            item["weight_source"] = r["weight_source"]
        if r["risk_note"] is not None:
            item["risk_note"] = r["risk_note"]
        deps = [x[0] for x in conn.execute(
            "SELECT depends_on_item_id FROM work_item_deps WHERE item_id = ? "
            "ORDER BY dep_order, depends_on_item_id", (r["item_id"],)).fetchall()]
        if deps:
            item["depends_on"] = deps
        if r["inferred"]:
            item["inferred"] = True
        work_items.append(item)

    milestones = []
    for r in conn.execute("SELECT * FROM milestones ORDER BY row_order").fetchall():
        ms = {"milestone_id": r["milestone_id"], "milestone_name": r["milestone_name"],
              "owner_id": r["owner_id"], "status": r["status"], "source": r["source"]}
        for col in ("planned_date", "actual_date", "anchor_item_id", "achieved_evidence",
                    "risk_note"):
            if r[col] is not None:
                ms[col] = r[col]
        if r["inferred"]:
            ms["inferred"] = True
        milestones.append(ms)

    features = [{"feature_id": r["feature_id"], "feature_name": r["feature_name"],
                 "status": r["status"], "owner_id": r["owner_id"], "source": r["source"]}
                for r in conn.execute("SELECT * FROM features ORDER BY row_order").fetchall()]
    people = [{"owner_id": r["owner_id"], "owner_name": r["owner_name"],
               "owner_role": r["owner_role"]}
              for r in conn.execute("SELECT * FROM people ORDER BY row_order").fetchall()]
    sources = []
    for r in conn.execute("SELECT * FROM sources ORDER BY row_order").fetchall():
        covers = [x[0] for x in conn.execute(
            "SELECT entity_group FROM source_covers WHERE source_id = ? ORDER BY entity_group",
            (r["source_id"],)).fetchall()]
        sources.append({"source_id": r["source_id"], "source_kind": r["source_kind"],
                        "source_ref": r["source_ref"], "covers": covers})
    inferred = [{"field": r["field"], "inferred_value": r["inferred_value"],
                 "inferred_from": r["inferred_from"]}
                for r in conn.execute(
                    "SELECT * FROM inferred_fields ORDER BY seq").fetchall()]

    out = {
        "schema": INPUT_SCHEMA,
        "db_schema_version": SCHEMA_VERSION,
        "project": {"project_name": prj["project_name"], "project_desc": prj["project_desc"],
                    "baseline_date": prj["baseline_date"], "project_start": prj["project_start"],
                    "repos": repos},
        "phases": phases,
        "work_items": work_items,
        "milestones": milestones,
        "people": people,
        "features": features,
        "sources": sources,
        "inferred_fields": inferred,
    }
    cov = conn.execute("SELECT * FROM coverage WHERE id = 1").fetchone()
    if cov is not None:
        out["coverage"] = {"candidate_total": cov["candidate_total"],
                           "excluded": cov["excluded"],
                           "granularity_truncated": cov["granularity_truncated"],
                           "unattributed": cov["unattributed"],
                           "source_label": cov["source_label"]}
    gw = conn.execute("SELECT * FROM git_window WHERE id = 1").fetchone()
    if gw is not None:
        out["git_window"] = {"commit_count": gw["commit_count"],
                             "first_commit": gw["first_commit"],
                             "last_commit": gw["last_commit"]}
    smap = {r["status_literal"]: r["status_norm"]
            for r in conn.execute("SELECT * FROM status_map").fetchall()}
    if smap:
        out["status_map"] = smap
    return out


# ── 预置查询（一切读取走 SQL） ──────────────────────────────────────────────────
PRESET_QUERIES = {
    "entity-counts": ("SELECT * FROM v_entity_counts", False, "各实体行数"),
    "project": ("SELECT * FROM project WHERE id = 1", False, "项目单行"),
    "phases": ("SELECT * FROM phases ORDER BY coalesce(phase_order, row_order)", False,
               "阶段（按次序）"),
    "work-items": ("SELECT * FROM v_work_items ORDER BY row_order", False,
                   "工作项（含负责人与阶段名、工期）"),
    "milestones": ("SELECT * FROM v_milestones ORDER BY row_order", False,
                   "里程碑（含 SQL 解析出的锚定日）"),
    "features": ("SELECT * FROM v_features ORDER BY row_order", False, "特性"),
    "people": ("SELECT * FROM people ORDER BY row_order", False, "人员名册"),
    "deps": ("SELECT * FROM work_item_deps ORDER BY item_id, dep_order", False, "工作项依赖"),
    "sources": ("SELECT s.*, group_concat(c.entity_group, '|') AS covers FROM sources s "
                "LEFT JOIN source_covers c ON c.source_id = s.source_id "
                "GROUP BY s.source_id ORDER BY s.row_order", False, "来源声明"),
    "inferred": ("SELECT * FROM inferred_fields ORDER BY seq", False, "推断字段清单"),
    "phase-rollup": ("SELECT * FROM v_phase_rollup ORDER BY coalesce(phase_order, phase_id)",
                     False, "阶段级包络与计数聚合"),
    "check-sums": ("SELECT * FROM v_check_sums", False, "项目级勾选计数汇总"),
    "people-coverage": ("SELECT * FROM v_people_coverage", False, "人员维度覆盖分子分母"),
    "timeline": ("SELECT * FROM v_timeline", False, "时间轴事件（已排序）"),
    "unknown-schedule": ("SELECT * FROM v_unknown_schedule ORDER BY row_order", False,
                         "无计划完成日 / 无锚定日的条目（不判延期、不上红）"),
    "orphans": ("SELECT * FROM v_orphans", False, "孤儿引用（应为空）"),
    "work-item-schedule": ("""
        SELECT item_id, item_name, status_norm, planned_start, planned_end, actual_end,
               duration_days,
               CASE WHEN planned_end IS NULL THEN NULL
                    ELSE CAST(julianday(planned_end) - julianday(:baseline) AS INTEGER)
               END AS days_to_planned_end,
               CASE WHEN planned_end IS NULL OR actual_end IS NULL THEN NULL
                    ELSE CAST(julianday(actual_end) - julianday(planned_end) AS INTEGER)
               END AS late_days
          FROM v_work_items ORDER BY row_order
     """, True, "工作项排期（天数差由 SQL 的 julianday 算出）"),
    "overdue": ("""
        SELECT item_id, item_name, planned_end,
               CAST(julianday(:baseline) - julianday(planned_end) AS INTEGER) AS delay_days
          FROM v_work_items
         WHERE planned_end IS NOT NULL
           AND julianday(planned_end) < julianday(:baseline)
           AND coalesce(status_norm, 'unknown') <> 'completed'
         ORDER BY delay_days DESC
     """, True, "已逾期未完成的工作项"),
    "milestone-schedule": ("""
        SELECT milestone_id, milestone_name, anchor_date, anchor_source, actual_date,
               achieved_evidence,
               CASE WHEN anchor_date IS NULL THEN NULL
                    ELSE CAST(julianday(anchor_date) - julianday(:baseline) AS INTEGER)
               END AS days_to_anchor
          FROM v_milestones ORDER BY row_order
     """, True, "里程碑锚定与达成（锚定解析 + 天数差都在 SQL）"),
}


def run_query(conn: sqlite3.Connection, name: str, baseline) -> list:
    if name not in PRESET_QUERIES:
        raise InputError("未知预置查询 %r（用 --list-queries 查看全部）" % name)
    sql, needs_baseline, _ = PRESET_QUERIES[name]
    if needs_baseline:
        if not baseline:
            baseline = conn.execute("SELECT baseline_date FROM project WHERE id = 1").fetchone()
            baseline = baseline[0] if baseline else None
        if not baseline:
            raise InputError("查询 %s 需要基准日：传 --baseline yyyy-mm-dd 或先装载 project 行"
                             % name)
        return [dict(r) for r in conn.execute(sql, {"baseline": baseline}).fetchall()]
    return [dict(r) for r in conn.execute(sql).fetchall()]


def print_rows(rows: list) -> None:
    if not rows:
        print("（无记录）")
        return
    cols = list(rows[0].keys())
    widths = {c: max(len(c), *(len(str(r.get(c))) for r in rows)) for c in cols}
    print(" | ".join(c.ljust(widths[c]) for c in cols))
    print("-+-".join("-" * widths[c] for c in cols))
    for r in rows:
        print(" | ".join(str(r.get(c)).ljust(widths[c]) for c in cols))


def print_change_summary(summary: dict) -> None:
    print("== --update 变更摘要（基于已有历史数据库按最新信息更新）==")
    for table, s in summary.items():
        if not (s["inserted"] or s["updated"] or s["input_rows"] or s["rows_before"]):
            continue
        print("%-20s 输入 %d ｜ 新增 %d ｜ 更新 %d ｜ 未变 %d ｜ 历史保留 %d ｜ 行数 %d → %d"
              % (table, s["input_rows"], s["inserted"], s["updated"], s["unchanged"],
                 s["retained_from_history"], s["rows_before"], s["rows_after"]))
        for ch in s["changes"]:
            for col, v in ch["fields"].items():
                print("   [变更] %s %s：%r → %r" % (ch["key"], col, v["old"], v["new"]))


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="project-db.py",
        description=("项目关键信息的 SQLite 关系模型引擎：建库、装载（约束即校验）、"
                     "基于历史库更新、SQL 查询、完整性体检、导出引擎输入。"),
        epilog=("字段定义与约束的权威 = schema/project.sql（DDL）；业务含义与必填档位见 "
                "references/required-info.md。\n退出码：0 成功 ｜ 3 约束违规/体检不通过 ｜ "
                "2 输入错误。\n"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--db", default=DEFAULT_DB, help="数据库路径（默认 %s）" % DEFAULT_DB)
    ap.add_argument("--init", action="store_true", help="建库建表（按 DDL），已存在则重建")
    ap.add_argument("--load", metavar="INPUT",
                    help="装载表单/CSV（默认语义：**每次运行重建**）")
    ap.add_argument("--update", metavar="INPUT",
                    help="基于已有历史数据库按最新信息更新（UPSERT + 变更摘要）")
    ap.add_argument("--check", action="store_true",
                    help="完整性体检：FK / 枚举 / 日期 / 孤儿 / 唯一性 / 组级必填")
    ap.add_argument("--query", metavar="NAME", help="运行预置查询")
    ap.add_argument("--sql", metavar="SELECT", help="运行只读 SQL（只允许 SELECT/PRAGMA/WITH）")
    ap.add_argument("--baseline", help="基准日 yyyy-mm-dd（部分查询需要；缺省取库中 project 行）")
    ap.add_argument("--export-json", metavar="OUT",
                    help="从数据库导出引擎输入 JSON（`-` 表示 stdout）")
    ap.add_argument("--list-queries", action="store_true", help="列出全部预置查询后退出")
    ap.add_argument("--print-ddl", action="store_true", help="打印 DDL（字段定义权威）后退出")
    ap.add_argument("--json", action="store_true", help="结果以 JSON 输出")
    args = ap.parse_args()

    try:
        if args.print_ddl:
            print(read_ddl())
            return 0
        if args.list_queries:
            print("预置查询（--query <名称>）：")
            for name, (_sql, needs, desc) in PRESET_QUERIES.items():
                print("  %-22s %s%s" % (name, desc, "（需基准日）" if needs else ""))
            return 0
        if args.load and args.update:
            raise InputError("--load（重建）与 --update（基于历史库更新）互斥，一次只能选一种")

        if args.load:
            data = read_input(args.load)
            tables = form_to_tables(data, args.load)
            conn = init_db(args.db, fresh=True)
            counts = load_tables(conn, tables)
            report = run_check(conn)
            if args.json:
                print(json.dumps({"mode": "load", "db": args.db, "rows": counts,
                                  "check": report}, ensure_ascii=False, indent=2))
            else:
                print("已按 DDL 重建数据库并装载：%s（schema %s）" % (args.db, SCHEMA_VERSION))
                print("装载行数：" + " ".join("%s=%d" % (k, v) for k, v in counts.items() if v))
                print("完整性体检：%s" % report["status"])
            if report["status"] != "ok":
                for f in report["findings"]:
                    print("  [体检不通过] %s：%s" % (f["check"], f["why"]), file=sys.stderr)
                return 3
            return 0

        if args.update:
            data = read_input(args.update)
            tables = form_to_tables(data, args.update)
            conn = connect(args.db, must_exist=True)
            summary = upsert_tables(conn, tables)
            report = run_check(conn)
            if args.json:
                print(json.dumps({"mode": "update", "db": args.db, "summary": summary,
                                  "check": report}, ensure_ascii=False, indent=2))
            else:
                print_change_summary(summary)
                print("完整性体检：%s" % report["status"])
            if report["status"] != "ok":
                for f in report["findings"]:
                    print("  [体检不通过] %s：%s" % (f["check"], f["why"]), file=sys.stderr)
                return 3
            return 0

        if args.init:
            init_db(args.db, fresh=True)
            print("已建库建表：%s（schema %s，DDL %s）" % (args.db, SCHEMA_VERSION, DDL_PATH))
            return 0

        conn = connect(args.db, must_exist=True)
        rc = 0
        if args.check:
            report = run_check(conn)
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                print("== 完整性体检（%s）==" % args.db)
                print("schema %s ｜ PRAGMA foreign_keys=%s ｜ 状态 %s"
                      % (report["schema_version"], report["foreign_keys_pragma"],
                         report["status"]))
                print("实体计数：" + " ".join("%s=%s" % (k, v)
                                             for k, v in report["entity_counts"].items()))
                for f in report["findings"]:
                    print("  [不通过] %s：%s" % (f["check"], f["why"]))
                    for row in f["rows"][:10]:
                        print("      %s" % row)
                if report["unknown_schedule"]:
                    print("无计划日期条目 %d 个（合法终态：不判延期、不上红）"
                          % len(report["unknown_schedule"]))
            rc = 0 if report["status"] == "ok" else 3
        if args.query:
            rows = run_query(conn, args.query, args.baseline)
            print(json.dumps(rows, ensure_ascii=False, indent=2)) if args.json else print_rows(rows)
        if args.sql:
            head = args.sql.lstrip().split(None, 1)[0].upper() if args.sql.strip() else ""
            if head not in ("SELECT", "WITH", "PRAGMA"):
                raise InputError("--sql 只接受只读查询（SELECT / WITH / PRAGMA），收到 %r" % head)
            rows = [dict(r) for r in conn.execute(args.sql).fetchall()]
            print(json.dumps(rows, ensure_ascii=False, indent=2)) if args.json else print_rows(rows)
        if args.export_json:
            payload = export_json(conn)
            body = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            if args.export_json == "-":
                sys.stdout.write(body)
            else:
                pathlib.Path(args.export_json).parent.mkdir(parents=True, exist_ok=True)
                pathlib.Path(args.export_json).write_text(body, encoding="utf-8")
                print("已从数据库导出引擎输入：%s" % args.export_json)
        if not (args.check or args.query or args.sql or args.export_json):
            raise InputError("没有指定动作：--init / --load / --update / --check / --query / "
                             "--sql / --export-json（-h 看全部）")
        return rc
    except ConstraintError as exc:
        print("约束违规（数据库拒绝写入）：%s" % exc, file=sys.stderr)
        return 3
    except InputError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return 2
    except sqlite3.Error as exc:
        print("SQLite 错误：%s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
