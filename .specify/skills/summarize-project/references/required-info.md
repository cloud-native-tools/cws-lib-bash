# 跨层规范：必要信息表 —— 项目关键信息的**业务含义与必填档位**

`summarize-project` 的项目关键信息用 **SQLite 关系模型**建模：**字段名、类型、取值域、实体间关联的可执行权威是 [`../schema/project.sql`](../schema/project.sql)（DDL）**，校验由**数据库约束**承担——装载即校验，违规即报错。本文档不再重复一份 schema，只讲 DDL 讲不了的那部分：**每个字段的业务含义、必填档位（R/I/O）、缺了会怎样、怎么用**。

> **核心原则**：具备强约束的数据**不用 Markdown 的模糊描述来记录**。凡"必须唯一 / 必须可解析 / 必须是 yyyy-mm-dd / 状态只能取某几个值"这类规则，都写在 DDL 里由数据库保证，本文档只指路，不复述、不靠文档提醒。

本技能不靠"挖 git repo"获取项目信息：项目管理信息本来就**不在代码仓库里**（一个项目常横跨多个 repo，且真正的排期/负责人/里程碑活在项目管理程序里）。因此输入模型是**必要信息表 + 上下文摄取 + 装载校验 + 表单补填**：

1. **上下文摄取**：先从当前对话上下文与用户提供的外部材料（管理系统导出、需求/任务/进度文档、Excel/Word/PDF、看板导出）中，按本表的**规范字段名**归集成表单；
2. **装载进数据库（约束即校验）**：`scripts/project-db.py --load` 把表单装载进 `data/project.db`；数据库拒绝任何违反约束的行，并给出可读的违规原因；
3. **表单补填**：R 档缺失（或数据库拒绝了某行）则**阻断**，只把真正需要人补的内容做成表单交给用户。

工作流三段式见 [../SKILL.md](../SKILL.md) 「Step 1」；记录层与呈现映射见 [data-model.md](data-model.md)；**repo 取材是完全 opt-in 的可选补充源**，规程见 [source-tiers.md](source-tiers.md)；字段缺失后的降级形态见 [degradation.md](degradation.md)。

**边界（四条）**：
1. **字段定义的权威在 DDL**（`../schema/project.sql`）：类型、取值域、非空、唯一、外键、条件必填组合都在那里，由数据库强制。本文档与 DDL 有分歧时**以 DDL 为准**。
2. 本文档只定义**业务语义层**：字段的含义、必填档位、缺失后果、呈现用途。**日期与进度的一切计算**在 `scripts/progress-engine.py`（从数据库读、用 SQL 算），本文档不含算式（见 [consistency-rules.md](consistency-rules.md) §0.1）。
3. 字段名是**规范命名**：snake_case ASCII 标识符，既是数据库列名、也是 YAML/JSON 表单的属性名，也是实体间关联的键。**四处一致**——DDL ⇄ 本表 ⇄ 引擎输出字段 ⇄ 各文档引用。自证命令见第 5 节。
4. 本技能**只读表单、不改表单**：表单内容由用户（或用户授权的摄取结果）维护；数据库是**派生物**（默认每次运行重建），技能读它、查它、据它出报告，绝不自作主张改写用户填写的字段值（只读呈现定位）。

---

## 1. 输入面、数据库与两种生命周期

| 事项 | 约定 |
|------|------|
| **数据库（查询与校验的唯一事实源）** | `<交付目录>/data/project.db`（SQLite；建表脚本 `${SKILL_HOME}/schema/project.sql`，schema 版本 `project-db/v1`） |
| **表单（人工可写的输入面）** | `<交付目录>/data/project-input.yaml`（SpecKit 项目默认 `.specify/project/summary/data/`，非 SpecKit 项目默认 `docs/project-summary/data/`）；也接受同结构 JSON 与按实体分文件的 CSV |
| 空白模板 / 已填样例 | `${SKILL_HOME}/templates/project-input.template.yaml`（每字段带档位注释）/ `${SKILL_HOME}/templates/project-input.example.yaml`（可直接试跑）；也可由 `python3 ${SKILL_HOME}/scripts/validate-project-input.py --blank-form` 现打印 |
| **默认生命周期：每次运行重建** | `project-db.py --load <表单>` 删旧建新、从最新输入全量装载。数据库是派生物，与"只读事实源、不管理数据"的定位一致 |
| **更新模式：基于历史库演进** | 用户希望在已有数据库上按最新信息更新时用 `project-db.py --update <表单>`：UPSERT 语义（已存在的主键行按新值更新、新行插入、本次未提及的历史行原样保留）并输出**变更摘要**；`## 元信息` 须注明本次为更新模式 |
| 只读纪律 | 技能读表单、装载表单、查询数据库；**不修改**用户填写的字段值。写入只发生在交付目录内（`data/project.db`、导出的中间产物） |
| 刷新 | 表单是交付目录的一部分，重复运行时**沿用**（用户可自行更新）；`project.db` / `engine-out.json` 是派生产物，随交付目录整体刷新 |

---

## 2. 三档必填性（尽量推断，最小阻断）

| 档位 | 含义 | 处置 |
|------|------|------|
| **R 必填-阻断** | 缺了报告根本立不住的信息 | **阻断**：不生成报告，向用户呈现待填表单（只列缺失的 R 档 + 建议补充的 O 档）。DDL 侧对应 `NOT NULL` |
| **I 可推断** | 模型可依据项目背景/阶段/里程碑等上下文，或装载器可按确定性规则推断出来 | **推断并留痕**：推断值入库时在 `inferred_fields` 表登记 `field` + `inferred_value` + `inferred_from: <依据>`（`inferred_from` 在 DDL 里是 `NOT NULL` —— 无依据的填补就是臆造，数据库不收）；引擎把全部推断项汇总到输出 `inferred_fields`，报告 `## 元信息` 固定写一份**推断字段清单** |
| **O 可选** | 缺了只影响精细度，不影响报告成立 | **显式降级**：DDL 侧允许 `NULL`，且 `NULL` 的语义是**明确的**——`progress_pct IS NULL` = 「无可计数依据」（**不是 0**）、`planned_end IS NULL` = 「无计划日期，无法判定延期」（**不是按期**）。按 [degradation.md](degradation.md) 第 3 节走合法终态（`-（无可计数依据）` / `未排期` / `未记录` / `未知`）并显式声明，**绝不臆造** |

**R 档只有三条**（刻意精简，避免把能推断的也压给用户）：

1. `project.project_name`
2. `project.baseline_date`
3. `work_items[]` 与 `milestones[]` **至少一组非空**；该组内每行的名称字段（`item_name` / `milestone_name`，以及 `features[]` 非空时的 `feature_name`）必填。

> 前两条与行内名称字段由 DDL 的 `NOT NULL` 保证；第 3 条是**跨表的业务必填组合**（表级 `CHECK` 表达不了），由 `validate-project-input.py` 的齐备性检查与 `project-db.py --check` 的 SQL 断言共同保证。
>
> **额外的条件必填**（同样已下沉为 DDL 的表级 `CHECK`）：给了 `progress_pct` 就必须给 `progress_source`；给了 `weight` 就必须给 `weight_source`——**无出处的数字视为编造**，数据库直接拒绝。

**推断 vs 臆造的边线**（与 [degradation.md](degradation.md) 第 3 节同口径）：有可指认依据的填补叫**推断**（在 `inferred_fields` 留痕），无依据地编数字/日期/人名叫**臆造**（禁止）。I 档只授权前者。

---

## 3. 必要信息表（逐字段：业务含义 × 档位 × 呈现用途 × 缺失后果）

> 每张表的列名、类型、取值域、非空/唯一/外键约束见 [`../schema/project.sql`](../schema/project.sql) 中的同名表。本节**不复述**这些约束。

### 3.1 `project`（单例；DDL 用 `CHECK (id = 1)` 保证只有一行）

| 字段 | 业务含义 | 档位 | 呈现用途 | 缺失后果 |
|------|----------|------|----------|----------|
| `project_name` | 项目对外名称 | **R** | 报告标题与元信息主体 | 阻断：报告无法命名主体 |
| `project_desc` | 一句话定位 | O | 概览背景段素材 | 概览背景缺一句定位，显式声明「材料未记录」 |
| `baseline_date` | 基准日 D0 | **R** | 全报告唯一 today；引擎 `--baseline` 缺省值 | 阻断：排期判断不可复现（引擎不读系统时钟） |
| `project_start` | 项目起点 | O | 甘特时间轴起点 | 引擎取全部日期中最早者并标为推断起点 |
| `repos` | **opt-in** repo 补充源清单（入库为 `repos` / `repo_derive_fields` 两张表） | O | `repo_id` 供字段级 `derive_fields` 引用 | 不声明 = **完全不做 repo 取材**（默认行为） |

### 3.2 `phases`（阶段）

| 字段 | 业务含义 | 档位 | 呈现用途 | 缺失后果 |
|------|----------|------|----------|----------|
| `phase_id` | 阶段标识 | I | 被 `work_items.phase_id` 引用 | 按出现顺序生成 `P-NN` 并留痕 |
| `phase_name` | 阶段名称（业务语言） | I | WBS 顶层分支名 | 取 `phase_id` 兜底并留痕 |
| `phase_order` | 阶段先后次序 | I | WBS 左右顺序、甘特分隔带顺序 | 按表单中出现顺序推断 |

> **整组缺省是合法的**：`phases` 为空表示工作项不分阶段。此时分解树的顶层分支**按 [work-breakdown.md](work-breakdown.md)「无层级材料时的深度降级」的三步顺序确定**（可推断出阶段 → `features[]` → 单层），推断出的阶段同样在 `inferred_fields` 留痕；**不由执行器在几种形态间自由取舍**。

### 3.3 `work_items`（工作项/任务表 —— 与 `milestones` 至少一组非空）

| 字段 | 业务含义 | 档位 | 呈现用途 | 缺失后果 |
|------|----------|------|----------|----------|
| `item_id` | 工作项标识 | I | 被依赖表与 `milestones.anchor_item_id` 引用 | 按出现顺序生成 `T-NN` 并留痕 |
| `item_name` | 工作项名称（业务语言动词短语） | **R** | WBS 节点 / 甘特条形 / 记录表逐字一致 | 阻断该行：无名称无法呈现 |
| `phase_id` | 所属阶段 | I | 承载分解树层级 | 该项挂在分解树顶层（无阶段分组） |
| `owner_id` | 负责人 | O | WBS `【…】`、甘特 ` ▪ 姓名` | 负责人记 `未记录`（合法终态，不静默丢弃） |
| `planned_start` | 计划开始日 | O | 甘特条形起点 | 无计划起点，甘特条形按可得日期退化 |
| `planned_end` | 计划完成日 | O | **延期判定的唯一依据** | 引擎给 `unknown-schedule`：声明「无计划日期，无法判定延期」，**不判逾期、不上红** |
| `actual_start` | 实际开始日 | O | 实际轨迹 | 少一条实际轨迹，不影响判定 |
| `actual_end` | 实际完成日 | O | 按期/逾期完成判定 | 已完成项无法判定是否按期（引擎给 `completed-schedule-unknown`） |
| `status` | 状态的**源字面量**（原文照填，如 `已完成`/`[X]`/`Implemented`） | I | 溯源；归一化态存 `status_norm`，由引擎与装载器按同一张映射表得出 | 无状态信号且无 `checks` → 状态记 `未知`（**不等于** `not-started`） |
| `progress_pct` | 材料明写的完成百分比 | O | 与 `progress_source` 成对 | 进度为 `NULL`，报告写 `-（无可计数依据）`，**不写 `0%`** |
| `progress_source` | 该百分比的出处 | 条件必填 | 溯源 | 数据库拒绝（无出处的百分比 = 编造） |
| `checks` | 勾选计数（入库为 `checks_done` / `checks_open` / `checks_deferred` / `checks_excluded` 四列） | O | 进度的可计数依据 | 无勾选依据，进度按上一行处理；**整组留空**即可，写全 0 会被数据库拒绝（那是把「无依据」伪装成「0% 完成」） |
| `depends_on` | 前置工作项（入库为 `work_item_deps` 联结表，M:N） | I | 甘特虚线依赖 | 不画依赖虚线（**不虚构依赖**）；可由阶段/日期次序推断并留痕 |
| `weight` / `weight_source` | 材料明确给出的权重与出处 | O | 阶段聚合的加权口径 | 引擎按等权平均聚合 |
| `risk_note` | 材料明写的风险信号 | O | 里程碑/工作项风险子类 | 不判风险态 |
| `source` | 溯源出处（`<文档>#<位置>` / `管理系统#<视图>` / `用户描述`） | I | 报告可溯源纪律 | 由 `sources` 声明推断；仍无则记为「表单填写（`<表单路径>`）」并留痕 |

### 3.4 `milestones`（里程碑 —— 与 `work_items` 至少一组非空）

| 字段 | 业务含义 | 档位 | 呈现用途 | 缺失后果 |
|------|----------|------|----------|----------|
| `milestone_id` | 里程碑标识 | I | 跟踪表 / 视图 / 甘特菱形 / WBS ◆Mn 四处同编号 | 按出现顺序生成 `M-NN` 并留痕 |
| `milestone_name` | 里程碑名称（业务语言，≤10 汉字） | **R** | 四处逐字一致 | 阻断该行 |
| `planned_date` | 计划锚定日 | O | 与 `anchor_item_id` 二者之一即可；**同时给出时以 `planned_date` 为准**（引擎口径） | 两者皆缺 → `unknown-schedule`：锚定列写 `未排期`，**不判逾期、不上红** |
| `actual_date` | 达成日 | O | 达成判定 | 无达成日且无 `achieved_evidence` → 视为未达成 |
| `achieved_evidence` | 达成依据（评审/发布/验收记录） | O | 有值即视为已达成 | 无依据不判 achieved |
| `status` | 状态的源字面量 | I | 归一化态**由引擎判定**（`achieved`/`pending`/`at-risk`/`unknown-schedule`） | 引擎按锚定日与基准日判定，表单不必填 |
| `anchor_item_id` | 锚定的工作项结束点 | O | 引擎按其 `planned_end` 换算锚定日（换算由 SQL 完成） | 与 `planned_date` 皆缺则无锚点 |
| `owner_id` | 负责人 | O | 里程碑标签 ` ▪姓名` | 记 `未记录` |
| `source` | 溯源出处 | I | 同 `work_items.source` | 同 `work_items.source` |

> **里程碑红线不变**：里程碑必须来自材料明确标注的**发布 / 评审 / 验收 / 阶段完成**节点。表单里没有里程碑就是没有——**不得**把普通提交、版本号、"某特性已实现"升格为里程碑（见 [degradation.md](degradation.md) 第 4 节）。这是**行为纪律**，不是数据约束：数据库拦不住"把提交写成里程碑"，只有纪律能。

### 3.5 `people`（人员）

| 字段 | 业务含义 | 档位 | 呈现用途 | 缺失后果 |
|------|----------|------|----------|----------|
| `owner_id` | 人员标识 | O | 被 `work_items.owner_id` / `milestones.owner_id` / `features.owner_id` 引用 | 整组缺省 → 全项目负责人 `未记录` + 显式声明已检索来源 |
| `owner_name` | 对外呈现规范名 | O | 报告各处逐字一致 | 装载时以 `owner_id` 兜底并留痕 |
| `owner_role` | 角色/职责 | I | `### 人员与分工` 表 | 写 `未记录`；**不得**据姓名或提交内容臆断角色 |

### 3.6 `features`（特性）与 `sources`（来源声明）

| 实体 | 字段 | 档位 | 呈现用途 | 缺失后果 |
|------|------|------|----------|----------|
| `features` | `feature_id` | I | 特性表行标识 | 按出现顺序生成 `F-NN` 并留痕 |
| `features` | `feature_name` | **R**（该组非空时） | 特性表 / 脑图节点 | 阻断该行 |
| `features` | `status` | I | 源字面量；归一化为三态 | 状态记 `未知` |
| `features` | `owner_id` | O | 脑图 ` ▪姓名` 后缀 | 记 `未记录` |
| `features` | `source` | I | 特性表来源列 | 同 `work_items.source` |
| `sources` | `source_id` | I | 元信息信息源清单 | 生成 `S-NN` |
| `sources` | `source_kind` | I | 信息源性质（取值域见 DDL 的 `CHECK`：管理系统导出 / 用户填写 / 上下文 / repo） | 记 `user-form` |
| `sources` | `source_ref` | I | 溯源与元信息（文件名 / 系统视图 / 对话位置） | 记「表单填写」 |
| `sources` | `covers` | O | 条目 `source` 的推断依据（入库为 `source_covers` 联结表） | 不参与条目 `source` 推断 |

> `features` 整组缺省是合法的：《需求与特性》章节按 [degradation.md](degradation.md) 第 2.3 节退化为「材料声明 + 已检索来源」。

### 3.7 `project.repos[]`（opt-in repo 补充源声明；入库为 `repos` + `repo_derive_fields`）

| 字段 | 业务含义 | 档位 | 缺失后果 |
|------|----------|------|----------|
| `repo_id` | 仓库标识 | I | 按顺序生成 `repo-NN` |
| `repo_path` | 仓库路径 | 条件必填 | 声明了 repo 却无路径 → 数据库拒绝（`NOT NULL`；无路径无法定向查询） |
| `repo_role` | 该仓在项目中的角色（如「网关主仓」「客户端 SDK 仓」） | O | 元信息少一句说明 |
| `derive_fields` | **声明哪些字段允许从该 repo 定向推导**（如 `people.owner_name`、`work_items.actual_end`） | O | 不声明 = 该仓只登记不查询 |

**opt-in 语义（硬约定）**：默认**不扫任何 repo**。只有 `project.repos[]` 已声明、且某字段出现在该仓的 `derive_fields` 中时，才允许对该字段做**定向小范围查询**（单条命令、限定路径），**禁止全仓扫描 / 目录遍历 / 深挖 specs+tasks**。规程与允许的查询形态见 [source-tiers.md](source-tiers.md)。

**多 repo 归集规则**：

1. **同一 `item_id` 不得在多个 repo 中重复定义**——工作项的身份由表单唯一确立（`item_id` 是主键），repo 只补字段值，不新增工作项。
2. 从 repo 推导出的值一律在 `inferred_fields` 留痕（`inferred_from: repo:<repo_id> <命令要点>`），并在元信息推断字段清单中登记。
3. 多个 repo 对同一字段给出冲突值时：**不合并、不取平均**——保留表单/管理系统的值，把冲突写进 `## 元信息`。
4. repo 只影响 I / O 档字段，**永远不能**替代 R 档：R 档缺失仍然阻断（不能靠扫 repo 凑齐必填项）。

---

## 4. 关联完整性与取值域：**由数据库约束保证**

以下规则**不在 Markdown 里重述、也不靠脚本手写**，全部由 [`../schema/project.sql`](../schema/project.sql) 的约束在装载时强制执行。本节只说明"哪条规则由哪种约束承担"，便于排错：

| 业务规则 | 承担它的数据库约束 |
|----------|--------------------|
| `*_id`（`phase_id` / `item_id` / `milestone_id` / `owner_id` / `feature_id` / `source_id`）在整份输入内**全局唯一**（跨实体也不得撞号，避免外键歧义） | `entity_ids` 表主键 + 每个实体表的 `AFTER INSERT` / `AFTER DELETE` 触发器 |
| ID 字面量只允许字母、数字、`_`、`-`、`.`，且以字母或数字开头（可安全用作 PlantUML 别名与 JSON 键） | `entity_ids.entity_id` 的 `CHECK`（一处 CHECK 管全部实体） |
| **外键必须可解析**：`work_items.phase_id` → `phases`；`work_items` / `milestones` / `features` 的 `owner_id` → `people`；`work_item_deps.depends_on_item_id` → `work_items`；`milestones.anchor_item_id` → `work_items` | 各列的 `FOREIGN KEY`（**必须** `PRAGMA foreign_keys = ON`，见下方警告） |
| 依赖不得指向自身 | `work_item_deps` 的 `CHECK (item_id <> depends_on_item_id)` |
| 日期一律零填充 `yyyy-mm-dd`，且必须是真实存在的日历日 | 各日期列的 `CHECK`（`GLOB` 形态 + `date(julianday(x)) = x`）。歧义写法（`02/03/2026`）与非法日历日（`2026-02-30`）一律被拒，**不猜** |
| 归一化状态只能取四态/里程碑三态+`unknown-schedule`；来源性质只能取四种 | `status_norm` / `source_kind` / `entity_group` 的 `CHECK ... IN (...)` |
| 名称类字段非空、`project` 单例、`phase_order` 不并列 | `NOT NULL` / `CHECK (id = 1)` / `UNIQUE` |
| 无出处的 `progress_pct` / `weight`、全 0 的 `checks` | `work_items` 的表级 `CHECK`（组合条件） |
| `inferred_from` 非空（无依据的推断即臆造） | `inferred_fields.inferred_from NOT NULL` |

> ⚠ **SQLite 默认关闭外键强制**（`PRAGMA foreign_keys` 默认 OFF），关闭时 `FOREIGN KEY` 只是注释、断裂引用可以静默写入。因此 DDL 开头声明该 PRAGMA，`project-db.py` 与 `progress-engine.py` 的**每个连接**都重新执行它，`--check` 还会回读该 PRAGMA 并在关闭时直接报错。这是本模型最容易踩的坑，别绕过。

**断裂即阻断**：数据库拒绝写入 = 与 R 档缺失同级**阻断**（关联闭合是报告"无孤儿条目"的前提）。装载器把 sqlite 的约束报错翻译成「哪一行 / 哪个字段 / 违了哪条规则 / 怎么改」的可读原因。

---

## 5. 装载、校验、查询与导出（脚本是唯一执行者）

```bash
# ① 空白表单模板（交给用户填）；已填样例见 templates/project-input.example.yaml
python3 ${SKILL_HOME}/scripts/validate-project-input.py --blank-form > <交付目录>/data/project-input.yaml

# ② R 档齐备性检查（跨表业务必填组合 + I/O 档缺口清单，人读结论）
python3 ${SKILL_HOME}/scripts/validate-project-input.py --input <交付目录>/data/project-input.yaml

# ③ 装载进数据库 —— **约束即校验**（默认每次运行重建；违规即报错并给出可读原因）
python3 ${SKILL_HOME}/scripts/project-db.py --db <交付目录>/data/project.db \
  --load <交付目录>/data/project-input.yaml

# ④ 完整性体检（FK / 枚举 / 日期 / 孤儿 / 唯一性 / 组级必填，全部用 SQL 断言）
python3 ${SKILL_HOME}/scripts/project-db.py --db <交付目录>/data/project.db --check

# ⑤ 阻断时：只列真正缺失的必填项与数据库拒绝的行，直接呈现给用户
python3 ${SKILL_HOME}/scripts/validate-project-input.py \
  --input <交付目录>/data/project-input.yaml --db <交付目录>/data/project.db --form-skeleton

# ⑥ 查询（一切读取走 SQL）：预置查询 / 任意只读 SQL / 导出引擎输入 JSON
python3 ${SKILL_HOME}/scripts/project-db.py --db <交付目录>/data/project.db --list-queries
python3 ${SKILL_HOME}/scripts/project-db.py --db <交付目录>/data/project.db --query work-item-schedule
python3 ${SKILL_HOME}/scripts/project-db.py --db <交付目录>/data/project.db \
  --export-json <交付目录>/data/progress-data.json

# ⑦ 更新模式：基于已有历史数据库按最新信息更新（UPSERT + 变更摘要）
python3 ${SKILL_HOME}/scripts/project-db.py --db <交付目录>/data/project.db --update <新表单>
```

**退出码与门禁语义**：`0` = 齐备（R 档全在、数据库未拒绝任何行、体检通过）→ 直接进入技能自身流程；`3` = **阻断**（R 档缺失 / 数据库约束违规 / 体检不通过）→ 呈现待填表单、等用户补填后重新装载；`2` = 输入错误（文件不可读 / 不是合法 YAML-JSON-CSV / 缺 DDL / 缺库）。

**结构化输出字段**（`validate-project-input.py --json` 的校验报告）：

| 字段 | 含义 |
|------|------|
| `status` | `ready` / `blocked` |
| `missing_required[]` | R 档缺失项：`field` / `why`（缺失后果）/ `how`（怎么补） |
| `inferable[]` | I 档待推断项：`field` / `inferred_value` / `inferred_from` |
| `optional_gaps[]` | O 档缺口：`field` / `count` / `consequence`（降级后果） |
| `db_constraint_errors[]` | **数据库拒绝的行**（可读原因）；同一批错误按性质归类进 `fk_errors[]` / `id_errors[]` / `date_errors[]` / `structure_errors[]` —— 字段名沿用，但**判定来自数据库约束** |
| `constraint_owner` | 一句话说明哪些校验归数据库（指向 `schema/project.sql`） |
| `db` / `db_schema_version` / `db_checked` / `db_check` | 本次装载的库路径、schema 版本、是否已装载、完整性体检结果 |
| `entity_counts` | 各实体行数（供元信息与覆盖声明引用） |
| `repo_optin` / `repos[]` / `repo_derive_fields[]` | repo 是否 opt-in、声明了哪些仓、哪些字段允许定向推导 |
| `form_skeleton` | 待填表单骨架（阻断时非空） |

**字段名四处一致自证**（改了 DDL 就要同步跑）：

```bash
python3 ${SKILL_HOME}/scripts/project-db.py --print-ddl                    # ① 权威：DDL
python3 ${SKILL_HOME}/scripts/validate-project-input.py --print-required   # ② 本表的可执行形态（含校验归属）
python3 ${SKILL_HOME}/scripts/progress-engine.py --print-schema            # ③ 引擎侧字段契约
python3 ${SKILL_HOME}/scripts/project-db.py --db <库> --query work-items    # ④ 实际列名
```

---

## 6. 与其它文档的分工（去重，避免同一规则两处写）

| 文档 | 管什么 | 与本文档的关系 |
|------|--------|----------------|
| [`../schema/project.sql`](../schema/project.sql) | **字段定义与约束的唯一权威**（类型、取值域、非空、唯一、外键、条件必填组合） | 本文档引用它，不复述 |
| 本文档 | **业务语义层**：字段含义、三档必填性、呈现用途、缺失后果、多 repo 归集 | 语义唯一权威 |
| [data-model.md](data-model.md) | **记录层 → 呈现物**的派生映射（四结构与图表/表格的对应） | 字段定义引用 DDL，不再各写一份 schema |
| [degradation.md](degradation.md) | 字段缺失后**章节与图怎么退化、怎么声明** | 缺失分级按本文档的 R/I/O 三档 |
| [source-tiers.md](source-tiers.md) | **opt-in** repo 补充源的定向取材规程 | 仅服务于 `derive_fields` 声明过的字段 |
| [consistency-rules.md](consistency-rules.md) | 判定语义（状态映射、聚合、覆盖门禁）与落盘门禁 | 输入侧的**语义**门禁以本文档为准，**机械**门禁在数据库约束里 |
| `scripts/project-db.py` | 表单装载、约束校验、SQL 查询、导出、更新模式 | 本文档第 5 节的执行者 |
| `scripts/progress-engine.py` | 一切日期与进度计算（从数据库读、用 SQL 算） | 字段名 **等于** DDL 列名 |

---

## 7. 落笔检查（输入模型维度）

- [ ] 已先做**上下文摄取**（对话内已有信息 + 用户提供的外部文档），按规范字段名归集，**未默认扫 repo**
- [ ] 已跑 `validate-project-input.py`（R 档齐备）与 `project-db.py --load`（装载即校验），退出码 0 才进入后续步骤；阻断时向用户呈现的是**只含缺失必填项与数据库拒绝行**的表单骨架
- [ ] R 档三项齐备：`project_name`、`baseline_date`、`work_items[]`/`milestones[]` 至少一组非空且行内名称齐全
- [ ] I 档推断项**逐条**在 `inferred_fields` 留痕（`field` + `inferred_from`），并已汇总进 `## 元信息` 的推断字段清单
- [ ] O 档缺口按 [degradation.md](degradation.md) 走合法终态并显式声明，无占位数字/日期/人名
- [ ] `project-db.py --check` 通过：`PRAGMA foreign_keys=ON`、无孤儿引用、无撞号、组级必填成立（这些**不靠人工核对**）
- [ ] `progress_pct` / `weight` 均带出处（数据库已代为把关，无出处的行进不了库）
- [ ] repo 取材：未声明 `project.repos[]` 时**全程未查询任何仓库**；声明了也只对 `derive_fields` 列出的字段做定向查询，推导值均在 `inferred_fields` 留痕
- [ ] 多 repo 情形：同一 `item_id` 未在多仓重复定义；冲突值未合并、已写入元信息
- [ ] 引擎读的是**数据库**（`--db`），字段名与 DDL 列名逐字一致（未在中间换名）
- [ ] 本次是 `--load`（重建）还是 `--update`（基于历史库更新）已在 `## 元信息` 注明
- [ ] 技能未修改表单内容（只读呈现定位）
