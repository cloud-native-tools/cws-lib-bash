-- ============================================================================
-- project.sql — summarize-project 的**关键信息关系模型（字段定义的唯一权威）**
-- schema 版本：project-db/v1
-- ----------------------------------------------------------------------------
-- 本文件是必要信息表七个实体的**物化形态**：字段名、类型、必填性、取值域、实体
-- 间关联全部在这里用 SQLite 的**强约束**表达（NOT NULL / PRIMARY KEY / UNIQUE /
-- FOREIGN KEY / CHECK / 触发器）。校验由数据库承担——装载即校验，违规即报错，
-- **不靠 Markdown 文档提醒、不靠脚本手写规则**。
--
-- 业务含义、必填档位（R/I/O）与缺失后果见 references/required-info.md；本文件是
-- 该文档的可执行权威：两者若有分歧，以本文件为准。
--
-- 【最常见的坑】SQLite 默认**关闭**外键强制（`PRAGMA foreign_keys` 默认 OFF），
-- 关闭时 FOREIGN KEY 只是注释、断裂引用可以静默写入。因此：
--   1. 本文件开头就 `PRAGMA foreign_keys = ON;`；
--   2. `scripts/project-db.py` **每建立一个连接**都重新执行该 PRAGMA（PRAGMA 是
--      连接级设置、不随数据库文件持久化，也在事务内无效）；
--   3. `--check` 会回读 `PRAGMA foreign_keys` 并在关闭时直接报错。
--
-- 【状态列的两列设计】`status` 存**源字面量**（材料原文，如 `已完成` / `[X]` /
-- `Implemented`），其取值集合对外部材料开放、**不能**用枚举 CHECK 约束；
-- `status_norm` 存**归一化态**，由 CHECK 枚举严格约束。两者都在库里，查询与呈现
-- 一律用 `status_norm`，溯源看 `status`。
--
-- 【日期列】统一 `TEXT`，CHECK 同时保证「零填充 yyyy-mm-dd 字面量」与「真实存在
-- 的日历日」（`date(julianday(x)) = x` 可拦下 2026-02-30、2026-04-31 之类）。
--
-- 【行序】每个实体表带 `row_order`：表单中的出现顺序是可复现输出的一部分
-- （ID 生成、`items[]` 输出次序都依赖它），一切查询按 `row_order` 排序。
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ── 元信息 ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schema_meta (
    meta_key    TEXT PRIMARY KEY,
    meta_value  TEXT NOT NULL
);

-- ── 全局 ID 命名空间（`*_id` 跨实体全局唯一，由 PK + 触发器共同保证） ──────────
-- 单表 PRIMARY KEY 只能保证「表内唯一」；必要信息表要求 `phase_id` / `item_id` /
-- `milestone_id` / `owner_id` / `feature_id` / `source_id` 在**整份输入内**互不
-- 重复（跨实体也不得撞号，否则外键有歧义）。做法：每个实体表的 AFTER INSERT
-- 触发器把新 ID 登记进本表，撞号即触发 UNIQUE 失败；AFTER DELETE 触发器注销。
-- ID 字面量规则（只允许字母/数字/`_`/`-`/`.`，且以字母或数字开头）也集中在这里
-- 一处 CHECK，所有实体共享。
CREATE TABLE IF NOT EXISTS entity_ids (
    entity_id    TEXT PRIMARY KEY
                 CHECK (entity_id GLOB '[A-Za-z0-9]*'
                        AND NOT entity_id GLOB '*[^A-Za-z0-9_.-]*'),
    entity_kind  TEXT NOT NULL
                 CHECK (entity_kind IN ('phase', 'work_item', 'milestone',
                                        'person', 'feature', 'source')),
    id_field     TEXT NOT NULL
);

-- ── project（单行） ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS project (
    id             INTEGER PRIMARY KEY CHECK (id = 1),   -- 单例：只允许一行
    project_name   TEXT NOT NULL CHECK (trim(project_name) <> ''),   -- [R]
    project_desc   TEXT,                                            -- [O]
    baseline_date  TEXT NOT NULL                                    -- [R]
                   CHECK (baseline_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                          AND date(julianday(baseline_date)) = baseline_date),
    project_start  TEXT                                             -- [O]
                   CHECK (project_start IS NULL
                          OR (project_start GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                              AND date(julianday(project_start)) = project_start))
);

-- ── people ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS people (
    owner_id    TEXT PRIMARY KEY,
    owner_name  TEXT NOT NULL CHECK (trim(owner_name) <> ''),
    owner_role  TEXT,
    row_order   INTEGER NOT NULL
);

CREATE TRIGGER IF NOT EXISTS trg_people_gid_ins AFTER INSERT ON people
BEGIN
    INSERT INTO entity_ids (entity_id, entity_kind, id_field)
    VALUES (NEW.owner_id, 'person', 'owner_id');
END;

CREATE TRIGGER IF NOT EXISTS trg_people_gid_del AFTER DELETE ON people
BEGIN
    DELETE FROM entity_ids WHERE entity_id = OLD.owner_id AND entity_kind = 'person';
END;

-- ── phases ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS phases (
    phase_id     TEXT PRIMARY KEY,
    phase_name   TEXT NOT NULL CHECK (trim(phase_name) <> ''),
    phase_order  INTEGER UNIQUE CHECK (phase_order IS NULL OR phase_order > 0),
    source       TEXT,
    inferred     INTEGER NOT NULL DEFAULT 0 CHECK (inferred IN (0, 1)),
    row_order    INTEGER NOT NULL
);

CREATE TRIGGER IF NOT EXISTS trg_phases_gid_ins AFTER INSERT ON phases
BEGIN
    INSERT INTO entity_ids (entity_id, entity_kind, id_field)
    VALUES (NEW.phase_id, 'phase', 'phase_id');
END;

CREATE TRIGGER IF NOT EXISTS trg_phases_gid_del AFTER DELETE ON phases
BEGIN
    DELETE FROM entity_ids WHERE entity_id = OLD.phase_id AND entity_kind = 'phase';
END;

-- ── work_items（任务表） ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS work_items (
    item_id          TEXT PRIMARY KEY,
    item_name        TEXT NOT NULL CHECK (trim(item_name) <> ''),          -- [R]
    phase_id         TEXT REFERENCES phases (phase_id)
                          ON UPDATE CASCADE ON DELETE RESTRICT,            -- [I] FK
    owner_id         TEXT REFERENCES people (owner_id)
                          ON UPDATE CASCADE ON DELETE RESTRICT,            -- [O] FK
    planned_start    TEXT CHECK (planned_start IS NULL
                                 OR (planned_start GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                                     AND date(julianday(planned_start)) = planned_start)),
    planned_end      TEXT CHECK (planned_end IS NULL
                                 OR (planned_end GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                                     AND date(julianday(planned_end)) = planned_end)),
    actual_start     TEXT CHECK (actual_start IS NULL
                                 OR (actual_start GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                                     AND date(julianday(actual_start)) = actual_start)),
    actual_end       TEXT CHECK (actual_end IS NULL
                                 OR (actual_end GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                                     AND date(julianday(actual_end)) = actual_end)),
    status           TEXT,                                                 -- 源字面量（开放集合）
    status_norm      TEXT CHECK (status_norm IS NULL
                                 OR status_norm IN ('completed', 'in-progress',
                                                    'not-started', 'deferred', 'unknown')),
    progress_pct     REAL CHECK (progress_pct IS NULL
                                 OR (progress_pct >= 0 AND progress_pct <= 100)),
    progress_source  TEXT,
    checks_done      INTEGER CHECK (checks_done IS NULL OR checks_done >= 0),
    checks_open      INTEGER CHECK (checks_open IS NULL OR checks_open >= 0),
    checks_deferred  INTEGER CHECK (checks_deferred IS NULL OR checks_deferred >= 0),
    checks_excluded  INTEGER CHECK (checks_excluded IS NULL OR checks_excluded >= 0),
    weight           REAL CHECK (weight IS NULL OR weight > 0),
    weight_source    TEXT,
    risk_note        TEXT,
    source           TEXT,
    inferred         INTEGER NOT NULL DEFAULT 0 CHECK (inferred IN (0, 1)),
    row_order        INTEGER NOT NULL,
    -- 无出处的数字视为编造：给了百分比/权重就必须给出处
    CHECK (progress_pct IS NULL
           OR (progress_source IS NOT NULL AND trim(progress_source) <> '')),
    CHECK (weight IS NULL
           OR (weight_source IS NOT NULL AND trim(weight_source) <> '')),
    -- 勾选计数要么整组缺省（= 无可计数依据，进度为 NULL），要么至少有一项非零：
    -- 全 0 的 checks 会把「无依据」伪装成「0% 完成」
    CHECK ((checks_done IS NULL AND checks_open IS NULL
            AND checks_deferred IS NULL AND checks_excluded IS NULL)
           OR (coalesce(checks_done, 0) + coalesce(checks_open, 0)
               + coalesce(checks_deferred, 0) > 0))
);

CREATE INDEX IF NOT EXISTS idx_work_items_phase ON work_items (phase_id);
CREATE INDEX IF NOT EXISTS idx_work_items_owner ON work_items (owner_id);
CREATE INDEX IF NOT EXISTS idx_work_items_planned_end ON work_items (planned_end);
CREATE INDEX IF NOT EXISTS idx_work_items_row_order ON work_items (row_order);

CREATE TRIGGER IF NOT EXISTS trg_work_items_gid_ins AFTER INSERT ON work_items
BEGIN
    INSERT INTO entity_ids (entity_id, entity_kind, id_field)
    VALUES (NEW.item_id, 'work_item', 'item_id');
END;

CREATE TRIGGER IF NOT EXISTS trg_work_items_gid_del AFTER DELETE ON work_items
BEGIN
    DELETE FROM entity_ids WHERE entity_id = OLD.item_id AND entity_kind = 'work_item';
END;

-- ── work_item_deps（工作项依赖，M:N 联结表） ─────────────────────────────────
CREATE TABLE IF NOT EXISTS work_item_deps (
    item_id             TEXT NOT NULL REFERENCES work_items (item_id)
                             ON UPDATE CASCADE ON DELETE CASCADE,
    depends_on_item_id  TEXT NOT NULL REFERENCES work_items (item_id)
                             ON UPDATE CASCADE ON DELETE RESTRICT,
    dep_order           INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (item_id, depends_on_item_id),
    CHECK (item_id <> depends_on_item_id)          -- 禁止自依赖
);

CREATE INDEX IF NOT EXISTS idx_deps_depends_on ON work_item_deps (depends_on_item_id);

-- ── milestones ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS milestones (
    milestone_id       TEXT PRIMARY KEY,
    milestone_name     TEXT NOT NULL CHECK (trim(milestone_name) <> ''),   -- [R]
    planned_date       TEXT CHECK (planned_date IS NULL
                                   OR (planned_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                                       AND date(julianday(planned_date)) = planned_date)),
    actual_date        TEXT CHECK (actual_date IS NULL
                                   OR (actual_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                                       AND date(julianday(actual_date)) = actual_date)),
    achieved_evidence  TEXT,
    status             TEXT,                                              -- 源字面量（开放集合）
    status_norm        TEXT CHECK (status_norm IS NULL
                                   OR status_norm IN ('achieved', 'pending',
                                                      'at-risk', 'unknown-schedule')),
    anchor_item_id     TEXT REFERENCES work_items (item_id)
                            ON UPDATE CASCADE ON DELETE RESTRICT,         -- FK
    owner_id           TEXT REFERENCES people (owner_id)
                            ON UPDATE CASCADE ON DELETE RESTRICT,         -- FK
    risk_note          TEXT,
    source             TEXT,
    inferred           INTEGER NOT NULL DEFAULT 0 CHECK (inferred IN (0, 1)),
    row_order          INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_milestones_anchor ON milestones (anchor_item_id);
CREATE INDEX IF NOT EXISTS idx_milestones_owner ON milestones (owner_id);

CREATE TRIGGER IF NOT EXISTS trg_milestones_gid_ins AFTER INSERT ON milestones
BEGIN
    INSERT INTO entity_ids (entity_id, entity_kind, id_field)
    VALUES (NEW.milestone_id, 'milestone', 'milestone_id');
END;

CREATE TRIGGER IF NOT EXISTS trg_milestones_gid_del AFTER DELETE ON milestones
BEGIN
    DELETE FROM entity_ids WHERE entity_id = OLD.milestone_id AND entity_kind = 'milestone';
END;

-- ── features ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS features (
    feature_id    TEXT PRIMARY KEY,
    feature_name  TEXT NOT NULL CHECK (trim(feature_name) <> ''),          -- [R]（该组非空时）
    status        TEXT,                                                    -- 源字面量（开放集合）
    status_norm   TEXT CHECK (status_norm IS NULL
                              OR status_norm IN ('completed', 'in-progress',
                                                 'not-started', 'deferred', 'unknown')),
    owner_id      TEXT REFERENCES people (owner_id)
                       ON UPDATE CASCADE ON DELETE RESTRICT,               -- FK
    source        TEXT,
    inferred      INTEGER NOT NULL DEFAULT 0 CHECK (inferred IN (0, 1)),
    row_order     INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_features_owner ON features (owner_id);

CREATE TRIGGER IF NOT EXISTS trg_features_gid_ins AFTER INSERT ON features
BEGIN
    INSERT INTO entity_ids (entity_id, entity_kind, id_field)
    VALUES (NEW.feature_id, 'feature', 'feature_id');
END;

CREATE TRIGGER IF NOT EXISTS trg_features_gid_del AFTER DELETE ON features
BEGIN
    DELETE FROM entity_ids WHERE entity_id = OLD.feature_id AND entity_kind = 'feature';
END;

-- ── sources（来源声明）+ source_covers（覆盖哪些实体组） ─────────────────────
CREATE TABLE IF NOT EXISTS sources (
    source_id    TEXT PRIMARY KEY,
    source_kind  TEXT NOT NULL
                 CHECK (source_kind IN ('management-export', 'user-form', 'context', 'repo')),
    source_ref   TEXT NOT NULL CHECK (trim(source_ref) <> ''),
    row_order    INTEGER NOT NULL
);

CREATE TRIGGER IF NOT EXISTS trg_sources_gid_ins AFTER INSERT ON sources
BEGIN
    INSERT INTO entity_ids (entity_id, entity_kind, id_field)
    VALUES (NEW.source_id, 'source', 'source_id');
END;

CREATE TRIGGER IF NOT EXISTS trg_sources_gid_del AFTER DELETE ON sources
BEGIN
    DELETE FROM entity_ids WHERE entity_id = OLD.source_id AND entity_kind = 'source';
END;

CREATE TABLE IF NOT EXISTS source_covers (
    source_id     TEXT NOT NULL REFERENCES sources (source_id)
                       ON UPDATE CASCADE ON DELETE CASCADE,
    entity_group  TEXT NOT NULL
                  CHECK (entity_group IN ('phases', 'work_items', 'milestones',
                                          'people', 'features')),
    PRIMARY KEY (source_id, entity_group)
);

-- ── inferred_fields（推断字段留痕：I 档推断值 + 依据） ───────────────────────
CREATE TABLE IF NOT EXISTS inferred_fields (
    seq             INTEGER PRIMARY KEY AUTOINCREMENT,
    field           TEXT NOT NULL CHECK (trim(field) <> ''),
    inferred_value  TEXT,
    inferred_from   TEXT NOT NULL CHECK (trim(inferred_from) <> '')   -- 无依据的填补即臆造
);

CREATE INDEX IF NOT EXISTS idx_inferred_field ON inferred_fields (field);

-- ── repos（opt-in repo 补充源声明）+ repo_derive_fields ─────────────────────
CREATE TABLE IF NOT EXISTS repos (
    repo_id    TEXT PRIMARY KEY,
    repo_path  TEXT NOT NULL CHECK (trim(repo_path) <> ''),   -- 声明了 repo 就必须给路径
    repo_role  TEXT,
    row_order  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS repo_derive_fields (
    repo_id  TEXT NOT NULL REFERENCES repos (repo_id)
                  ON UPDATE CASCADE ON DELETE CASCADE,
    field    TEXT NOT NULL CHECK (trim(field) <> ''),
    PRIMARY KEY (repo_id, field)
);

-- ── coverage（分解树覆盖清点，单行） ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS coverage (
    id                     INTEGER PRIMARY KEY CHECK (id = 1),
    candidate_total        INTEGER NOT NULL CHECK (candidate_total >= 0),
    excluded               INTEGER NOT NULL DEFAULT 0 CHECK (excluded >= 0),
    granularity_truncated  INTEGER NOT NULL DEFAULT 0 CHECK (granularity_truncated >= 0),
    unattributed           INTEGER NOT NULL DEFAULT 0 CHECK (unattributed >= 0),
    source_label           TEXT
);

-- ── git_window（仅 opt-in repo 情形下有意义，单行） ─────────────────────────
CREATE TABLE IF NOT EXISTS git_window (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    commit_count  INTEGER CHECK (commit_count IS NULL OR commit_count >= 0),
    first_commit  TEXT CHECK (first_commit IS NULL
                              OR (first_commit GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                                  AND date(julianday(first_commit)) = first_commit)),
    last_commit   TEXT CHECK (last_commit IS NULL
                              OR (last_commit GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                                  AND date(julianday(last_commit)) = last_commit))
);

-- ── status_map（项目自有状态字面量 → 归一化态的覆盖映射） ───────────────────
CREATE TABLE IF NOT EXISTS status_map (
    status_literal  TEXT PRIMARY KEY,          -- 小写归一后的源字面量
    status_norm     TEXT NOT NULL
                    CHECK (status_norm IN ('completed', 'in-progress', 'not-started',
                                           'deferred', 'unknown'))
);

-- ============================================================================
-- 视图（预置查询的可复用形态；一切呈现所需的读取都走 SQL，不在 Markdown 里推算）
-- 与基准日相关的查询（延期天数、逾期判定、today 偏移）需要参数，写在
-- scripts/project-db.py 与 scripts/progress-engine.py 的参数化 SQL 里，不做成视图。
-- ============================================================================

DROP VIEW IF EXISTS v_work_items;
CREATE VIEW v_work_items AS
SELECT w.item_id,
       w.item_name,
       w.phase_id,
       ph.phase_name,
       ph.phase_order,
       w.owner_id,
       pe.owner_name,
       pe.owner_role,
       w.planned_start,
       w.planned_end,
       w.actual_start,
       w.actual_end,
       w.status,
       w.status_norm,
       w.progress_pct,
       w.progress_source,
       w.checks_done,
       w.checks_open,
       w.checks_deferred,
       w.checks_excluded,
       w.weight,
       w.weight_source,
       w.risk_note,
       w.source,
       w.inferred,
       w.row_order,
       CASE WHEN w.planned_start IS NOT NULL AND w.planned_end IS NOT NULL
            THEN CAST(julianday(w.planned_end) - julianday(w.planned_start) AS INTEGER) + 1
       END AS duration_days
  FROM work_items w
  LEFT JOIN phases ph ON ph.phase_id = w.phase_id
  LEFT JOIN people pe ON pe.owner_id = w.owner_id;

DROP VIEW IF EXISTS v_milestones;
CREATE VIEW v_milestones AS
SELECT m.milestone_id,
       m.milestone_name,
       m.planned_date,
       m.actual_date,
       m.achieved_evidence,
       m.status,
       m.status_norm,
       m.anchor_item_id,
       w.item_name       AS anchor_item_name,
       w.planned_end     AS anchor_item_planned_end,
       w.actual_end      AS anchor_item_actual_end,
       -- 锚定日解析（绝对日期优先，否则由锚定工作项结束点换算）——关联在 SQL 里做
       coalesce(m.planned_date, w.planned_end, w.actual_end) AS anchor_date,
       CASE WHEN m.planned_date IS NOT NULL THEN 'planned_date'
            WHEN w.planned_end IS NOT NULL THEN 'anchor_item.planned_end'
            WHEN w.actual_end IS NOT NULL THEN 'anchor_item.actual_end'
       END AS anchor_source,
       m.owner_id,
       pe.owner_name,
       m.risk_note,
       m.source,
       m.inferred,
       m.row_order
  FROM milestones m
  LEFT JOIN work_items w ON w.item_id = m.anchor_item_id
  LEFT JOIN people pe ON pe.owner_id = m.owner_id;

DROP VIEW IF EXISTS v_features;
CREATE VIEW v_features AS
SELECT f.feature_id, f.feature_name, f.status, f.status_norm,
       f.owner_id, pe.owner_name, f.source, f.inferred, f.row_order
  FROM features f
  LEFT JOIN people pe ON pe.owner_id = f.owner_id;

-- 阶段级包络与计数聚合（阶段日期由子项包络推出，聚合在 SQL 里做）
DROP VIEW IF EXISTS v_phase_rollup;
CREATE VIEW v_phase_rollup AS
SELECT ph.phase_id,
       ph.phase_name,
       ph.phase_order,
       count(w.item_id)                                   AS item_count,
       min(w.planned_start)                               AS planned_start_min,
       max(w.planned_end)                                 AS planned_end_max,
       max(w.actual_end)                                  AS actual_end_max,
       sum(CASE WHEN w.actual_end IS NOT NULL THEN 1 ELSE 0 END) AS actual_end_count,
       sum(CASE WHEN w.progress_pct IS NOT NULL THEN 1 ELSE 0 END) AS quantified_count
  FROM phases ph
  LEFT JOIN work_items w ON w.phase_id = ph.phase_id
 GROUP BY ph.phase_id, ph.phase_name, ph.phase_order;

-- 项目级勾选计数汇总（整体完成度的可计数依据）
DROP VIEW IF EXISTS v_check_sums;
CREATE VIEW v_check_sums AS
SELECT coalesce(sum(checks_done), 0)     AS done,
       coalesce(sum(checks_open), 0)     AS open_count,
       coalesce(sum(checks_deferred), 0) AS deferred,
       coalesce(sum(checks_excluded), 0) AS excluded_marks,
       count(*)                          AS rows_with_checks
  FROM work_items
 WHERE checks_done IS NOT NULL OR checks_open IS NOT NULL
    OR checks_deferred IS NOT NULL OR checks_excluded IS NOT NULL;

-- 人员维度覆盖（分子分母由 SQL 给出，呈现层不做除法）
DROP VIEW IF EXISTS v_people_coverage;
CREATE VIEW v_people_coverage AS
SELECT (SELECT count(*) FROM work_items WHERE owner_id IS NOT NULL)
       + (SELECT count(*) FROM milestones WHERE owner_id IS NOT NULL)
       + (SELECT count(*) FROM features WHERE owner_id IS NOT NULL)   AS owned_count,
       (SELECT count(*) FROM work_items)
       + (SELECT count(*) FROM milestones)
       + (SELECT count(*) FROM features)
       + (SELECT count(*) FROM phases)                                AS entity_count,
       (SELECT count(*) FROM people)                                  AS roster_count;

-- 时间轴事件（排序聚合在 SQL 里做：日期 → 条目 ID → 事件类型）
DROP VIEW IF EXISTS v_timeline;
CREATE VIEW v_timeline AS
SELECT * FROM (
    SELECT planned_start AS event_date, item_id, 'planned_start' AS kind, item_name AS label
      FROM work_items WHERE planned_start IS NOT NULL
    UNION ALL
    SELECT planned_end, item_id, 'planned_end', item_name
      FROM work_items WHERE planned_end IS NOT NULL
    UNION ALL
    SELECT actual_end, item_id, 'actual_end', item_name
      FROM work_items WHERE actual_end IS NOT NULL
    UNION ALL
    SELECT anchor_date, milestone_id, 'milestone', milestone_name
      FROM v_milestones WHERE anchor_date IS NOT NULL
)
ORDER BY event_date, item_id, kind;

-- 实体计数（元信息与覆盖声明引用）
DROP VIEW IF EXISTS v_entity_counts;
CREATE VIEW v_entity_counts AS
SELECT (SELECT count(*) FROM phases)      AS phases,
       (SELECT count(*) FROM work_items)  AS work_items,
       (SELECT count(*) FROM milestones)  AS milestones,
       (SELECT count(*) FROM people)      AS people,
       (SELECT count(*) FROM features)    AS features,
       (SELECT count(*) FROM sources)     AS sources,
       (SELECT count(*) FROM work_item_deps) AS work_item_deps,
       (SELECT count(*) FROM repos)       AS repos;

-- 完整性体检视图（FK 由数据库强制，这些视图用于 --check 复核与孤儿排查；
-- 在 `PRAGMA foreign_keys=ON` 下装载的库里，前四个视图必须为空）
DROP VIEW IF EXISTS v_orphans;
CREATE VIEW v_orphans AS
SELECT 'work_items.phase_id' AS where_at, w.item_id AS entity_id, w.phase_id AS value
  FROM work_items w WHERE w.phase_id IS NOT NULL
   AND w.phase_id NOT IN (SELECT phase_id FROM phases)
UNION ALL
SELECT 'work_items.owner_id', w.item_id, w.owner_id
  FROM work_items w WHERE w.owner_id IS NOT NULL
   AND w.owner_id NOT IN (SELECT owner_id FROM people)
UNION ALL
SELECT 'milestones.anchor_item_id', m.milestone_id, m.anchor_item_id
  FROM milestones m WHERE m.anchor_item_id IS NOT NULL
   AND m.anchor_item_id NOT IN (SELECT item_id FROM work_items)
UNION ALL
SELECT 'milestones.owner_id', m.milestone_id, m.owner_id
  FROM milestones m WHERE m.owner_id IS NOT NULL
   AND m.owner_id NOT IN (SELECT owner_id FROM people)
UNION ALL
SELECT 'features.owner_id', f.feature_id, f.owner_id
  FROM features f WHERE f.owner_id IS NOT NULL
   AND f.owner_id NOT IN (SELECT owner_id FROM people)
UNION ALL
SELECT 'work_item_deps.depends_on_item_id', d.item_id, d.depends_on_item_id
  FROM work_item_deps d
 WHERE d.depends_on_item_id NOT IN (SELECT item_id FROM work_items);

-- 无计划完成日的工作项（`unknown-schedule` 路径的数据侧来源：不判延期、不上红）
DROP VIEW IF EXISTS v_unknown_schedule;
CREATE VIEW v_unknown_schedule AS
SELECT item_id, item_name, row_order FROM work_items WHERE planned_end IS NULL
UNION ALL
SELECT milestone_id, milestone_name, row_order FROM v_milestones WHERE anchor_date IS NULL;
