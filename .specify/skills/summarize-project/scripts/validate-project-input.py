#!/usr/bin/env python3
"""validate-project-input.py — 必要信息表的**R 档齐备性检查器 + 待填表单生成器**。

角色（本轮收缩：约束校验已下沉到数据库）
----------------------------------------
项目关键信息用 **SQLite 关系模型**建模（DDL：`${SKILL_HOME}/schema/project.sql`），
因此**一切能被关系约束表达的校验都由数据库承担**，本脚本不再手写一遍：

| 校验 | 归属 | 落点 |
|------|------|------|
| 外键可解析（`phase_id` / `owner_id` / `anchor_item_id` / `depends_on`） | **数据库** | `FOREIGN KEY` + `PRAGMA foreign_keys=ON` |
| `*_id` 跨实体全局唯一 + ID 字面量合法 | **数据库** | `entity_ids` 主键 + 各表 `AFTER INSERT` 触发器 + `CHECK` |
| 日期是零填充 `yyyy-mm-dd` 且是真实日历日 | **数据库** | 日期列 `CHECK`（`GLOB` + `date(julianday(x)) = x`） |
| 状态/来源性质等枚举取值 | **数据库** | `CHECK ... IN (...)` |
| 名称类字段非空、单例 project、`phase_order` 唯一 | **数据库** | `NOT NULL` / `CHECK (id = 1)` / `UNIQUE` |
| 无出处的 `progress_pct` / `weight`、全 0 的 `checks` | **数据库** | 表级 `CHECK`（组合条件） |
| **R 档齐备性**（`project_name`、`baseline_date`、`work_items[]`/`milestones[]` 至少一组非空） | **本脚本** | 跨表的"业务必填组合"，表级 `CHECK` 无法表达；组级那一条同时由 `project-db.py --check` 的 SQL 断言兜底 |
| **待填表单骨架**（只列真正缺失的必填项 + 建议补充的可选项） | **本脚本** | 这是"给人看的产物"，不是数据约束 |
| **I / O 档缺口登记**（可推断项与可选缺口清单，供元信息与降级声明引用） | **本脚本** | 同上，属报告素材 |

所以本脚本只做三件事：① 读表单 → ② 检 R 档齐备性、登记 I/O 档缺口 → ③ 缺就出待填表单。
`--db` / `--emit-json` 会把表单**装载进数据库**，让**数据库来校验**，并把违规按可读原因
归类到 `fk_errors[]` / `id_errors[]` / `date_errors[]` / `structure_errors[]`（字段名不变，
但**来源已是数据库约束**）。

**本脚本不读 git repo、不扫描目标项目目录**：repo 取材是完全 opt-in 的补充源
（`project.repos[]` + 字段级 `derive_fields` 声明，见 `references/source-tiers.md`）。

用法
----
    python3 validate-project-input.py --input data/project-input.yaml
    python3 validate-project-input.py --input data/project-input.yaml --json
    python3 validate-project-input.py --input data/project-input.yaml --form-skeleton
    python3 validate-project-input.py --input data/project-input.yaml --db data/project.db
    python3 validate-project-input.py --input data/project-input.yaml \
        --db data/project.db --emit-json data/progress-data.json
    python3 validate-project-input.py --print-required     # 必要信息表字段清单（含档位与校验归属）
    python3 validate-project-input.py --blank-form         # 空白表单模板

退出码：0 齐备（R 档全在、数据库未拒绝任何行）；3 阻断（R 档缺失 / 数据库约束违规）；
2 输入错误（文件不可读 / 不是合法 YAML-JSON / 顶层结构非法 / 缺 DDL）。
本脚本除 `--db`（数据库）与 `--emit-json` 指定的文件外不写任何文件，也不修改表单本身
（只读呈现定位）。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys
import tempfile

TOOL_ID = "validate-project-input/v2"
INPUT_SCHEMA = "project-input/v1"
DB_SCHEMA = "project-db/v1"
DDL_REF = "schema/project.sql"

# ── 必要信息表（字段 × 必填档位 × 关联 × 校验归属）───────────────────────────────
# 档位：R = 必填-阻断；I = 可推断（缺失由模型/装载器推断并标 inferred）；O = 可选
# owner 列：db = 该字段的类型/取值域/关联由 schema/project.sql 的约束保证；
#           script = 由本脚本检查（跨表的业务必填组合 / 报告素材）
REQUIRED_INFO = [
    # entity, field, tier, kind, relation, consequence, owner
    ("project", "project_name", "R", "str", "-", "无项目名，报告无法命名主体 → 阻断", "script+db"),
    ("project", "project_desc", "O", "str", "-", "概览背景段落缺一句定位，显式声明「材料未记录」", "db"),
    ("project", "baseline_date", "R", "date", "全报告唯一基准日 D0", "无基准日则一切排期判断不可复现 → 阻断", "script+db"),
    ("project", "project_start", "O", "date", "甘特时间轴起点", "缺失时引擎取全部日期最早者并标推断起点", "db"),
    ("project", "repos", "O", "list", "repo_id 供 derive_fields 引用", "不声明 = 不做任何 repo 取材（默认）", "db"),
    ("phases", "phase_id", "I", "id", "被 work_items.phase_id 引用", "缺失时按工作项分组生成 P-NN 并标推断", "db"),
    ("phases", "phase_name", "I", "str", "-", "缺失时取生成的阶段编号作名称并标推断", "db"),
    ("phases", "phase_order", "I", "int", "阶段左右/先后次序（UNIQUE）", "缺失时按首次出现顺序推断", "db"),
    ("work_items", "item_id", "I", "id", "全局唯一，被 work_item_deps / anchor_item_id 引用", "缺失时按出现顺序生成 T-NN 并标推断", "db"),
    ("work_items", "item_name", "R", "str", "-", "工作项无名称无法呈现 → 阻断（该组非空时）", "db"),
    ("work_items", "phase_id", "I", "fk:phases.phase_id", "工作项 → 阶段", "缺失时该项挂在分解树顶层（无阶段分组）", "db"),
    ("work_items", "owner_id", "O", "fk:people.owner_id", "工作项 → 人员", "缺失时负责人记 `未记录`（合法终态）", "db"),
    ("work_items", "planned_start", "O", "date", "-", "缺失则该项无计划起点，甘特条形按可得日期退化", "db"),
    ("work_items", "planned_end", "O", "date", "延期判定的唯一依据", "缺失 → 引擎给 `unknown-schedule`，不判延期、不上红", "db"),
    ("work_items", "actual_start", "O", "date", "-", "缺失不影响判定，仅少一条实际轨迹", "db"),
    ("work_items", "actual_end", "O", "date", "按期/逾期完成的判定依据", "缺失 → 已完成项无法判定是否按期", "db"),
    ("work_items", "status", "I", "str", "源字面量；归一化态存 status_norm（枚举 CHECK）", "缺失且无勾选计数 → 状态记 `未知`（非 not-started）", "db"),
    ("work_items", "progress_pct", "O", "num", "0–100；须同时给 progress_source", "缺失则进度为 null，报告写 `-（无可计数依据）`", "db"),
    ("work_items", "depends_on", "I", "fk:work_item_deps → work_items.item_id", "工作项 → 前置工作项（M:N 联结表）", "缺失则不画依赖虚线（不虚构依赖）", "db"),
    ("work_items", "source", "I", "str", "溯源出处", "缺失时由 sources[] 推断，仍无则记为表单填写", "db"),
    ("milestones", "milestone_id", "I", "id", "全局唯一", "缺失时按出现顺序生成 M-NN 并标推断", "db"),
    ("milestones", "milestone_name", "R", "str", "-", "里程碑无名称无法呈现 → 阻断（该组非空时）", "db"),
    ("milestones", "planned_date", "O", "date", "锚定日（或由 anchor_item_id 换算）", "两者皆缺 → `unknown-schedule`，不判逾期", "db"),
    ("milestones", "actual_date", "O", "date", "达成日", "缺失且无达成依据 → 视为未达成", "db"),
    ("milestones", "status", "I", "str", "由引擎判定；归一化态枚举 CHECK", "缺失由引擎按锚定日与基准日判定", "db"),
    ("milestones", "anchor_item_id", "O", "fk:work_items.item_id", "里程碑 → 工作项结束点", "缺失且无 planned_date → 无锚点", "db"),
    ("milestones", "owner_id", "O", "fk:people.owner_id", "里程碑 → 人员", "缺失时负责人记 `未记录`", "db"),
    ("milestones", "source", "I", "str", "溯源出处", "同 work_items.source", "db"),
    ("people", "owner_id", "O", "id", "被 owner_id 外键引用", "无人员表则全项目负责人 `未记录` 并显式声明", "db"),
    ("people", "owner_name", "O", "str", "对外呈现规范名（NOT NULL，装载器以 owner_id 兜底）", "缺失时以 owner_id 兜底呈现", "db"),
    ("people", "owner_role", "I", "str", "-", "缺失时写 `未记录`，不得据姓名臆断角色", "db"),
    ("features", "feature_id", "I", "id", "全局唯一", "缺失时按出现顺序生成 F-NN 并标推断", "db"),
    ("features", "feature_name", "R", "str", "-", "特性无名称无法呈现 → 阻断（该组非空时）", "db"),
    ("features", "status", "I", "str", "源字面量；归一化态枚举 CHECK", "缺失 → 状态记 `未知`", "db"),
    ("features", "source", "I", "str", "溯源出处", "同 work_items.source", "db"),
    ("sources", "source_id", "I", "id", "全局唯一", "缺失时生成 S-NN", "db"),
    ("sources", "source_kind", "I", "enum", "management-export/user-form/context/repo", "缺失时记 user-form", "db"),
    ("sources", "source_ref", "I", "str", "文件/系统/对话位置", "缺失时记「表单填写」", "db"),
    ("sources", "covers", "O", "list", "该来源覆盖的实体组（source_covers 联结表）", "缺失则不参与条目 source 推断", "db"),
]

GROUPS = ("phases", "work_items", "milestones", "people", "features", "sources")
NAME_FIELD = {
    "phases": "phase_name",
    "work_items": "item_name",
    "milestones": "milestone_name",
    "people": "owner_name",
    "features": "feature_name",
    "sources": "source_ref",
}

BLANK_FORM = """\
# 项目输入表单（project-input/v1）—— summarize-project 的必要信息表
# 落位：<交付目录>/data/project-input.yaml
# 字段业务含义与必填档位见 references/required-info.md；
# 字段类型/取值域/关联约束的权威是 schema/project.sql（DDL，由数据库强制）。
# 档位：[R] 必填-阻断  [I] 可推断（留空即可，模型/装载器会推断并留痕）  [O] 可选
# 日期一律 yyyy-mm-dd。留空 = 「本表未提供」，按档位处置，绝不臆造。
# 本表由 scripts/project-db.py --load 装载进 SQLite；装载即校验（约束违规会报可读原因）。

schema: project-input/v1

project:
  project_name: ""          # [R] 项目对外名称
  project_desc: ""          # [O] 一句话定位（用于概览背景）
  baseline_date: ""         # [R] 基准日 D0（yyyy-mm-dd），一切排期判断以此为参照
  project_start: ""         # [O] 项目起点（甘特时间轴起点）
  repos: []                 # [O] 仅在需要 repo 补充取材时声明（默认留空 = 不扫任何 repo）
  #  - repo_id: main
  #    repo_path: /abs/path/to/repo
  #    repo_role: "代码主仓"
  #    derive_fields: ["people.owner_name"]   # 声明「从 repo 定向推导」的字段，未声明的字段不查 repo

phases: []                  # [I] 阶段；留空则由工作项分组推断
#  - phase_id: P-01
#    phase_name: "需求与设计"
#    phase_order: 1

work_items: []              # 与 milestones 至少一组非空（[R] 组级要求）
#  - item_id: T-01          # [I] 留空自动生成
#    item_name: "需求调研"   # [R]
#    phase_id: P-01         # [I] 外键 → phases.phase_id
#    owner_id: U-01         # [O] 外键 → people.owner_id
#    planned_start: 2026-03-02   # [O]
#    planned_end: 2026-03-09     # [O] 缺失 → 无法判定延期（不上红）
#    actual_start: ""            # [O]
#    actual_end: 2026-03-09      # [O]
#    status: "已完成"             # [I] 源字面量即可，归一化交给装载器与引擎
#    progress_pct:               # [O] 只在材料明写百分比时填，并给 progress_source
#    progress_source: ""
#    checks: {done: 22, open: 4, deferred: 1}   # [O] 可计数依据（勾选比）
#    depends_on: [T-00]          # [I] 外键 → work_items.item_id
#    source: "PMO 导出#Sheet1!A12" # [I] 缺失时由 sources[] 推断

milestones: []              # 与 work_items 至少一组非空（[R] 组级要求）
#  - milestone_id: M-01     # [I]
#    milestone_name: "需求冻结"  # [R]
#    planned_date: 2026-03-09    # [O] 与 anchor_item_id 二选一，皆缺 → 无锚点
#    actual_date: ""             # [O]
#    status: ""                  # [I] 由引擎判定
#    anchor_item_id: ""          # [O] 外键 → work_items.item_id
#    owner_id: ""                # [O] 外键 → people.owner_id
#    achieved_evidence: ""       # [O] 达成依据（评审记录/发布记录）
#    source: ""                  # [I]

people: []                  # [O] 人员；缺失则全项目负责人记「未记录」并显式声明
#  - owner_id: U-01
#    owner_name: "张三"
#    owner_role: "开发负责人"    # [I] 未知写 未记录，不得臆断

features: []                # [O] 特性清单（《需求与特性》章节）
#  - feature_id: F-01
#    feature_name: "统一登录"   # [R]（该组非空时）
#    status: "已完成"           # [I]
#    source: ""                 # [I]

sources: []                 # [I] 每组信息的来源声明
#  - source_id: S-01
#    source_kind: management-export   # management-export | user-form | context | repo
#    source_ref: "PMO 周报导出 2026-04-06.xlsx"
#    covers: [work_items, milestones]

# coverage: {candidate_total: 0, excluded: 0, granularity_truncated: 0, unattributed: 0, source_label: ""}
# status_map: {}            # [O] 项目自有状态字面量 → 归一化态的覆盖映射
"""


class InputError(Exception):
    """表单不可读 / 不是合法 YAML-JSON / 顶层结构非法 → 退出码 2。"""


# ── 数据库层（表单读取、装载、约束校验、导出）都在 project-db.py 里，此处复用 ──────
def project_db():
    """惰性加载同目录的 project-db.py（文件名带连字符，只能按路径加载）。"""
    path = pathlib.Path(__file__).resolve().parent / "project-db.py"
    if not path.exists():
        raise InputError("找不到 %s —— 关系模型读写层缺失，无法读表单/校验约束" % path)
    name = "_speckit_project_db"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)                        # type: ignore[union-attr]
    return module


def read_form(path: str) -> dict:
    db = project_db()
    try:
        return db.read_input(path)
    except db.InputError as exc:                          # type: ignore[attr-defined]
        raise InputError(str(exc))


def blank(value) -> bool:
    """空值判定：None / 空串 / 只含空白 / 空列表 / 空字典 一律视为「本表未提供」。"""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def as_rows(data: dict, group: str, errors: list) -> list:
    rows = data.get(group)
    if blank(rows):
        return []
    if not isinstance(rows, list):
        errors.append({"where": group, "problem": "必须是数组（每行一条记录）"})
        return []
    out = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append({"where": "%s[%d]" % (group, i), "problem": "必须是对象（键 = 规范字段名）"})
            continue
        out.append(row)
    return out


def tier_for(entity: str, field: str) -> str:
    for e, f, tier, _k, _r, _c, _o in REQUIRED_INFO:
        if e == entity and f == field:
            return tier
    return "O"


def consequence_for(entity: str, field: str) -> str:
    for e, f, _t, _k, _r, consequence, _o in REQUIRED_INFO:
        if e == entity and f == field:
            return consequence
    return "-"


# ── R 档齐备性 + I/O 档缺口登记（数据库约束表达不了的那部分） ────────────────────
def validate(data: dict, input_label: str) -> dict:
    struct_errors: list = []
    project = data.get("project") if isinstance(data.get("project"), dict) else {}
    if not isinstance(data.get("project"), dict) and not blank(data.get("project")):
        struct_errors.append({"where": "project", "problem": "必须是对象"})
    entities = {g: as_rows(data, g, struct_errors) for g in GROUPS}

    missing_required: list = []
    inferable: list = []
    optional_gaps: dict = {}

    def note_optional(field: str, consequence: str) -> None:
        entry = optional_gaps.setdefault(field, {"field": field, "count": 0,
                                                 "consequence": consequence})
        entry["count"] += 1

    # -- project 级 R 档 --------------------------------------------------------
    for entity, field, tier, _kind, _rel, consequence, _owner in REQUIRED_INFO:
        if entity != "project" or tier != "R":
            continue
        if blank(project.get(field)):
            missing_required.append({
                "field": "project.%s" % field,
                "why": consequence,
                "how": "在表单 project 段填写 %s" % field,
            })

    # -- 组级 R 档：work_items 与 milestones 至少一组非空（跨表条件，表级 CHECK 表达不了）
    if not entities["work_items"] and not entities["milestones"]:
        missing_required.append({
            "field": "work_items[] / milestones[]",
            "why": "两组皆空 → 报告既无任务分解也无里程碑，五章节骨架无法成立 → 阻断",
            "how": "至少填写一组：work_items[]（每行 item_name）或 milestones[]（每行 milestone_name）",
        })

    # -- 行级：R 档名称齐备性 + I/O 档缺口登记（其余约束由数据库负责） -------------
    for group in GROUPS:
        name_field = NAME_FIELD[group]
        for i, row in enumerate(entities[group]):
            where = "%s[%d]" % (group, i)
            if tier_for(group, name_field) == "R" and blank(row.get(name_field)):
                missing_required.append({
                    "field": "%s.%s" % (where, name_field),
                    "why": consequence_for(group, name_field),
                    "how": "补齐该行的 %s（业务语言名称）" % name_field,
                })
            for entity, field, tier, _kind, _rel, consequence, _owner in REQUIRED_INFO:
                if entity != group or field == name_field:
                    continue
                if not blank(row.get(field)):
                    continue
                if tier == "I":
                    inferable.append({"field": "%s.%s" % (where, field),
                                      "inferred_value": None,
                                      "inferred_from": consequence})
                elif tier == "O":
                    note_optional("%s.%s" % (group, field), consequence)

    # -- project 级 O 档缺口 ----------------------------------------------------
    for entity, field, tier, _kind, _rel, consequence, _owner in REQUIRED_INFO:
        if entity == "project" and tier == "O" and blank(project.get(field)):
            note_optional("project.%s" % field, consequence)

    repos = project.get("repos") if isinstance(project.get("repos"), list) else []
    repo_ids, derive_fields = [], []
    for i, repo in enumerate(repos):
        if not isinstance(repo, dict):
            struct_errors.append({"where": "project.repos[%d]" % i, "problem": "必须是对象"})
            continue
        rid = str(repo.get("repo_id") or "").strip() or "repo-%02d" % (i + 1)
        repo_ids.append(rid)
        for field in (repo.get("derive_fields") or []):
            derive_fields.append({"repo_id": rid, "field": str(field)})

    sources = [{"source_id": str(row.get("source_id") or "").strip() or "S-%02d" % (i + 1),
                "source_kind": str(row.get("source_kind") or "user-form").strip(),
                "source_ref": row.get("source_ref") or "表单填写",
                "covers": row.get("covers") or []}
               for i, row in enumerate(entities["sources"])]
    if not sources:
        inferable.append({
            "field": "sources[]",
            "inferred_value": "user-form",
            "inferred_from": "表单未声明来源 → 全部条目来源记为「表单填写（%s）」" % input_label,
        })

    blocking = bool(missing_required or struct_errors)
    report = {
        "tool": TOOL_ID,
        "input": input_label,
        "status": "blocked" if blocking else "ready",
        "entity_counts": {g: len(entities[g]) for g in GROUPS},
        "baseline_date": project.get("baseline_date"),
        "missing_required": missing_required,
        "inferable": inferable,
        "optional_gaps": sorted(optional_gaps.values(), key=lambda x: x["field"]),
        # 以下四类**由数据库约束判定**（本脚本不再手写规则）：未做数据库装载时为空并附说明
        "fk_errors": [],
        "id_errors": [],
        "date_errors": [],
        "structure_errors": struct_errors,
        "db_constraint_errors": [],
        "constraint_owner": (
            "外键 / `*_id` 全局唯一 / 日期字面量与日历日 / 枚举 / 非空 / 条件必填组合"
            "一律由数据库约束保证（见 %s）；用 --db 装载即校验，或跑 "
            "project-db.py --load 与 --check" % DDL_REF),
        "db": None,
        "db_schema_version": DB_SCHEMA,
        "db_checked": False,
        "sources": sources,
        "repos": sorted(set(repo_ids)),
        "repo_derive_fields": derive_fields,
        "repo_optin": bool(repo_ids),
        "next_action": (
            "R 档齐备 → 装载进数据库（约束即校验）后进入技能自身流程"
            if not blocking else
            "阻断 → 向用户呈现待填表单（只列下方 missing_required），补填后重新校验"
        ),
    }
    report["form_skeleton"] = form_skeleton(report) if blocking else None
    return report


# ── 数据库装载：让约束来校验，并把违规按可读原因归类回报告字段 ────────────────────
def classify(message: str) -> str:
    if "FOREIGN KEY" in message or "关联断裂" in message:
        return "fk_errors"
    if ("全局唯一" in message or "PRIMARY KEY" in message or "不是合法标识" in message
            or "UNIQUE" in message or "重复" in message):
        return "id_errors"
    if "合法日期" in message:
        return "date_errors"
    return "structure_errors"


def load_into_db(report: dict, data: dict, input_label: str, db_path: str) -> None:
    """把表单装载进 SQLite：**校验由数据库约束完成**，违规回填进报告。"""
    db = project_db()
    report["db"] = db_path
    try:
        tables = db.form_to_tables(data, input_label)
        conn = db.init_db(db_path, fresh=True)
        db.load_tables(conn, tables)
    except db.ConstraintError as exc:                     # type: ignore[attr-defined]
        message = str(exc)
        report["db_constraint_errors"].append({"where": "database", "problem": message})
        report[classify(message)].append({"where": "database", "value": None,
                                          "expected": message, "problem": message})
        report["status"] = "blocked"
        report["next_action"] = ("阻断 → 数据库拒绝了该行（约束违规），按上方可读原因修正表单后"
                                "重新装载")
        report["form_skeleton"] = form_skeleton(report)
        return
    except db.InputError as exc:                          # type: ignore[attr-defined]
        raise InputError(str(exc))
    check = db.run_check(conn)
    report["db_checked"] = True
    report["db_check"] = check
    if check["status"] != "ok":
        for finding in check["findings"]:
            report["db_constraint_errors"].append({"where": finding["check"],
                                                   "problem": finding["why"],
                                                   "rows": finding["rows"]})
        report["status"] = "blocked"
        report["next_action"] = "阻断 → 数据库完整性体检不通过，见 db_check.findings"
        report["form_skeleton"] = form_skeleton(report)
    report["_conn"] = conn


def form_skeleton(report: dict) -> str:
    """只列真正缺失的必填字段 + 数据库拒绝的行；能推断的一律不塞给用户填。"""
    lines = ["# 待填表单（只列缺失的必填项与数据库拒绝的行，能推断的字段已省略）",
             "# 填好后重新运行：python3 validate-project-input.py --input <本文件> --db <库路径>"]
    if report["missing_required"]:
        lines.append("")
        lines.append("## 必填缺失（缺这些就无法出报告）")
        for item in report["missing_required"]:
            lines.append("- %s：%s" % (item["field"], item["how"]))
            lines.append("  # 缺失后果：%s" % item["why"])
    if report.get("db_constraint_errors"):
        lines.append("")
        lines.append("## 数据库约束违规（由 %s 的约束判定，不是文档提醒）" % DDL_REF)
        for item in report["db_constraint_errors"]:
            lines.append("- %s：%s" % (item.get("where"), item.get("problem")))
    if report["structure_errors"]:
        lines.append("")
        lines.append("## 结构问题")
        for item in report["structure_errors"]:
            lines.append("- %s：%s" % (item.get("where"), item.get("problem")))
    if report["optional_gaps"]:
        lines.append("")
        lines.append("## 建议补充（可选，缺失只降级、不阻断）")
        for item in report["optional_gaps"]:
            lines.append("- %s（%d 处）：%s" % (item["field"], item["count"], item["consequence"]))
    return "\n".join(lines)


def print_required_table() -> None:
    print("必要信息表（字段 × 必填档位 × 关联 × 校验归属）")
    print("业务含义与缺失后果见 references/required-info.md；字段类型/取值域/关联约束的权威是 "
          "%s（由数据库强制）" % DDL_REF)
    print("档位：R 必填-阻断 ｜ I 可推断（标 inferred + inferred_from）｜ O 可选（缺失显式降级）")
    print("校验归属：db = 数据库约束 ｜ script = 本脚本（跨表业务必填组合 / 报告素材）")
    print("%-11s %-16s %-4s %-10s %-34s %s" % ("实体", "字段", "档位", "校验归属", "类型/关联", "缺失后果"))
    for entity, field, tier, kind, relation, consequence, owner in REQUIRED_INFO:
        rel = kind if relation == "-" else "%s → %s" % (kind, relation)
        print("%-11s %-16s %-4s %-10s %-34s %s" % (entity, field, tier, owner, rel, consequence))


def print_human(report: dict) -> None:
    print("== 项目输入表单校验（%s）==" % report["input"])
    print("状态：%s ｜ 基准日：%s" % (report["status"], report["baseline_date"] or "-"))
    counts = report["entity_counts"]
    print("实体计数：" + " ".join("%s=%d" % (k, v) for k, v in counts.items()))
    print("repo 取材：%s" % ("opt-in（%s）" % "、".join(report["repos"]) if report["repo_optin"]
                            else "未声明 repos[] → 不做任何 repo 取材（默认）"))
    if report["repo_derive_fields"]:
        print("  定向推导字段：" + "、".join("%s@%s" % (d["field"], d["repo_id"])
                                            for d in report["repo_derive_fields"]))
    print("必填缺失 %d ｜ 可推断 %d ｜ 可选缺口 %d"
          % (len(report["missing_required"]), len(report["inferable"]),
             len(report["optional_gaps"])))
    print("约束校验归属：%s" % report["constraint_owner"])
    if report["db_checked"]:
        print("数据库装载：%s（schema %s）｜ 完整性体检 %s"
              % (report["db"], report["db_schema_version"], report["db_check"]["status"]))
    else:
        print("数据库装载：未执行（加 --db <库路径> 让约束来校验）")
    for item in report["missing_required"]:
        print("  [必填缺失] %s —— %s" % (item["field"], item["why"]))
    for item in report["db_constraint_errors"]:
        print("  [约束违规] %s：%s" % (item.get("where"), item.get("problem")))
    for item in report["structure_errors"]:
        print("  [结构问题] %s：%s" % (item["where"], item["problem"]))
    for item in report["inferable"][:12]:
        print("  [可推断] %s ← %s" % (item["field"], item["inferred_from"]))
    if len(report["inferable"]) > 12:
        print("  [可推断] …另有 %d 项" % (len(report["inferable"]) - 12))
    for item in report["optional_gaps"]:
        print("  [可选缺口] %s（%d 处）：%s" % (item["field"], item["count"], item["consequence"]))
    print("下一步：%s" % report["next_action"])


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="validate-project-input.py",
        description=("项目输入表单的 R 档齐备性检查器与待填表单生成器：检查跨表的业务必填组合、"
                     "登记 I/O 档缺口；一切能被关系约束表达的校验已下沉到数据库"
                     "（schema/project.sql），用 --db 装载即校验。"),
        epilog=("字段业务含义与档位见 references/required-info.md；字段类型/取值域/关联约束的"
                "权威是 schema/project.sql。\n退出码：0 齐备 ｜ 3 阻断 ｜ 2 输入错误。\n"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--input", help="项目输入表单路径（.yaml / .json / CSV 目录），`-` 表示 stdin")
    ap.add_argument("--db", help="把表单装载进该 SQLite 库，由数据库约束完成校验（建议 data/project.db）")
    ap.add_argument("--json", action="store_true", help="输出结构化 JSON 校验报告")
    ap.add_argument("--form-skeleton", action="store_true",
                    help="阻断时只打印待填表单骨架（可直接交给用户）")
    ap.add_argument("--emit-json", help="校验通过时**从数据库**导出引擎输入 JSON（不换字段名）")
    ap.add_argument("--print-required", action="store_true",
                    help="打印必要信息表字段清单（含档位与校验归属）后退出")
    ap.add_argument("--blank-form", action="store_true", help="打印空白表单模板后退出")
    args = ap.parse_args()

    if args.print_required:
        print_required_table()
        return 0
    if args.blank_form:
        print(BLANK_FORM)
        return 0

    tmp_dir = None
    try:
        if not args.input:
            raise InputError("缺少 --input <表单文件>（`--blank-form` 可打印空白模板）")
        data = read_form(args.input)
        report = validate(data, args.input)
        db_path = args.db
        if args.emit_json and not db_path:
            # `--emit-json` 必须经数据库（DB 是查询与校验的唯一事实源）；未给 --db 时用临时库
            tmp_dir = tempfile.TemporaryDirectory(prefix="speckit-project-db-")
            db_path = str(pathlib.Path(tmp_dir.name) / "project.db")
        if db_path and report["status"] != "blocked":
            load_into_db(report, data, args.input, db_path)
    except InputError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return 2

    blocked = report["status"] == "blocked"
    conn = report.pop("_conn", None)
    if args.emit_json and not blocked and conn is not None:
        db = project_db()
        payload = db.export_json(conn)
        pathlib.Path(args.emit_json).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.emit_json).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["engine_input"] = args.emit_json
        report["inferred_fields"] = payload["inferred_fields"]

    public = {k: v for k, v in report.items() if not k.startswith("_")}
    if args.form_skeleton:
        print(public["form_skeleton"] or "# 表单齐备，无需补填。")
    elif args.json:
        print(json.dumps(public, ensure_ascii=False, indent=2))
    else:
        print_human(public)
        if blocked:
            print("")
            print(public["form_skeleton"])
    if args.emit_json and not blocked:
        print("已从数据库导出引擎输入：%s" % args.emit_json)
    if tmp_dir is not None:
        tmp_dir.cleanup()
    return 3 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
