---
name: git-utils
description: |
  Unified git workspace governance skill — one reconcile family across FOUR scopes: (A) single-repo branch workflow governance (the project's declared branch model — single-branch / dual-branch / temp-branch (trunk + short-lived feature branches) / MAIN-PRE-DEV three-tier — recorded in `docs/git-workflow.md`; sync/merge discipline, selective merge, `.gitexcludes`); (B) multi-environment coordination of one developer's many checkouts plus the inter-repo dependency graph and dependency-first sequencing; (C) disciplined submodule editing (project-named branches + ledgered gitlink bumps); (D) plain-SSH server provisioning into a git server (git user, bare repos, authorized keys, ssh config Host entry). Formerly four separate skills (git-workflow, git-fleet, git-server-init, git-submodule-edit), merged with content preserved. Host-platform-agnostic and free of personal/environment-specific data — host names, absolute paths, and inventories all come from caller-provided parameters; code-hosting-platform automation (GitHub/Gitee/Aone Code) is deliberately out of scope. Runs as a single **reconcile engine** (see `.specify/shared/patterns/reconcile-pattern.md`): the desired state is the declared branch model + sync relations + per-branch `.gitexcludes` rules; every invocation observes the current repo state, diffs, and converges — bootstrap (model selection + interactive branch naming + creation + .gitexcludes init when the block is absent or unfilled), health-check (structure/sync/.gitexcludes observation + residual report), and directed convergence (rebase sync, merge, and safe push with automatic .gitexcludes enforcement) are the same engine under different inputs. Covers pre-checks, rebase synchronization, conflict resolution, force-with-lease push strategies, and per-branch file exclusion via `.gitexcludes`. Use this when the user mentions ["git workflow", "branch sync", "rebase sync", "分支同步", "git rebase", "force-with-lease", "发布流程", "分支策略", "主干分支", "预发分支", "开发分支", "three-tier git", "git workflow setup", "创建git工作流", "工作流维护", "workflow health check", "工作流检查", "selective merge", "选择性合并", "排除文件", "忽略配置文件", "分支排除", "branch-exclusive", ".gitexcludes", "开发专属文件", "merge filter", "工作流模型", "分支模型", "trunk-based", "单分支开发", "双分支开发", "临时分支", "短命特性分支", "调谐工作流", "git 调谐", "git workspace", "git-utils", "工作区治理", "multi-machine git", "跨机器 git", "多环境 git", "环境 × 仓库", "git fleet", "依赖图", "dependency graph", "受影响消费方", "affected consumers", "依赖优先顺序", "topological order", "checkout inventory", "git server", "git 服务器", "搭建git服务", "bare repository", "裸仓库", "创建git用户", "配置git远程", "edit submodule", "子模块修改", "submodule branch", "gitlink bump"]
skill_id: "<SKILL:.specify/skills/git-utils/SKILL.md>"
classification: external
---

# git-utils

## Overview

统一的 **git 工作区治理**技能——一个调谐（Reconcile）家族覆盖四个作用域（由原 git-workflow / git-fleet / git-server-init / git-submodule-edit 四技能合并而来，内容无损、形式按本技能惯例重表达）：

| 作用域 | 覆盖 | 细节入口 |
|--------|------|----------|
| **A — 单仓分支工作流** | 单仓分支工作流治理，模型可选（见下方工作流模型菜单：单分支 / 双分支 / 临时分支 / MAIN/PRE/DEV 三层）、同步与合并纪律、选择性合并、`.gitexcludes`、强推纪律；状态面 `docs/git-workflow.md` 托管块 | 本文件下方 Workflow + `references/` 的 `bootstrap-commands` / `health-check-commands` / `execute-commands` / `gitexcludes-subroutine` / `instructions-lookup` / `troubleshooting` |
| **B — 多环境协调** | 同一批仓库跨多台机器的巡检、危险分级、仓库间依赖图与依赖优先排序 | `references/fleet-workflow.md` + `fleet-inventory-schema` / `fleet-hazard-taxonomy` / `fleet-coordination-playbook` / `fleet-dependency-model`；引擎 `.specify/scripts/git_fleet.py` |
| **C — 子模块编辑** | 子模块内改代码纪律（`project-<PARENT_SLUG>/*` 分支）+ gitlink 抬升台账 | `references/submodule-workflow.md` + `submodule-command-recipes`；`.specify/scripts/record-bump.sh`；`assets/ledger-template.md` |
| **D — 服务器置备** | 纯 SSH 服务器 → Git 服务器（D1–D4 四期望态） | `references/server-workflow.md` + `server-ssh-config-entry` / `server-reference-architecture` / `server-troubleshooting`；`.specify/scripts/provision-git-server.sh` / `.specify/scripts/ssh_config_insert.py` |

跨作用域硬约束：① 环境无关——主机名/绝对路径一律由调用方 inventory 或参数提供；② 高影响动作（写远端、强推等）的分级确认口径以本文件下方分级确认表与各作用域自身规则为准；③ 数据源唯一——分支信息只在 `docs/git-workflow.md` 托管块，子模块台账只在 `${SKILL_WORKDIR}/submodule-edits.md`。

> **边界：本技能不承载代码托管平台（GitHub/Gitee/Aone Code）自动化。** 本技能只管本地 git 状态与自建 git 服务器，与具体托管平台无关、不含任何个人/环境私有数据；托管平台侧的对象操作（建库/PR·MR/issue/release/成员/webhook 等）属另一独立本地技能，不在此处。

### 作用域 A — 单仓分支工作流（模型可选）

单仓 Git 开发工作流管理。**Git 工作流是项目级建议项（为更好地管理代码库服务），不是普适强制**；不同项目采用不同模型，本技能维护托管块**所声明的那个模型**，不把任何单一模型强加给项目。

**工作流模型菜单**（Bootstrap 时按项目形态推荐并确认；声明后写入托管块 `Workflow model` 行）：

| 模型 | 形态 | 典型场景 |
|------|------|----------|
| **单分支** | 仅一条主干分支，直接开发（连临时分支都不创建） | 个人小项目、一次性脚本仓 |
| **双分支** | 两条长期分支：一条日常开发，另一条归档或跟踪上游 | 维护型项目、需跟踪上游的 fork |
| **临时分支**（trunk-based） | 单主干；每次开发切临时分支，完成即合入主干并删除 | 大部分 SDD 模式开发的项目（与单分支的分界：单分支连临时分支都不创建） |
| **MAIN/PRE/DEV 三层** | 主干/预发/开发三层长期分支 + 固定 rebase 链（角色定义见下方「三层模型的分支角色」） | 需版本集成与环境验证的发布型项目 |

**只有一个运行模式——调谐（Reconcile）**，遵循 [`.specify/shared/patterns/reconcile-pattern.md`](../../shared/patterns/reconcile-pattern.md)：

- **期望态（spec）** = `docs/git-workflow.md` 的 Git Workflow 托管块（`<!-- GIT_WORKFLOW_START -->` … `<!-- GIT_WORKFLOW_END -->`）声明的**工作流模型 + 该模型的分支结构**（如三层模型要求 MAIN/PRE/DEV 存在且 tracking 正确）+ 该模型声明的同步/合并关系（无积压分叉）+ 各分支 `.gitexcludes` 规则就位且被排除路径未被跟踪 + 本次用户操作指令。
- **当前态（status）** = 仓库实际分支结构、同步状态、`.gitexcludes` 分布。
- **调谐** = 观测 → diff（过容忍带）→ 收敛（分级确认）→ 校验。

同一调谐引擎在不同输入下表现为三种作用域：

| 输入 | 作用域 | 行为 |
|------|--------|------|
| `docs/git-workflow.md` 缺失，或其托管块仍是 `None yet.` 占位行 | **Bootstrap** | 交互选择工作流模型与分支名、创建分支、初始化 `.gitexcludes`、写入 Git Workflow 块 |
| 块已填写 且 无操作参数 | **全维度体检** | R1 观测 + R3 diff + 残差汇报，不自动收敛 |
| 块已填写 且 有操作参数 | **定向收敛** | 用户指令并入期望态，执行具体 git 操作（自动尊重 `.gitexcludes`） |

**容忍带**：同步状态 `0 0`、`.gitexcludes` 内容语义等价、Git Workflow 块与实际分支名一致——均标记「已一致（容忍）」不触发收敛；仅 ahead/behind 分叉、分支缺失、排除路径仍被跟踪等实质偏离进入收敛建议。

**分级确认门禁**（与模式文档对齐）：
> Gate probe: gate-git-workflow-tiered-mode — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).

| 动作类 | 门禁 |
|--------|------|
| 只读观测、体检报告、本地分支创建 | 自动执行 |
| 写远端（push / 建远端分支）、直接 merge 入 PRE/MAIN | **停下确认**（外部权威源） |
| 共享分支 force-with-lease 强推 | **停下确认** + 团队同步窗口 + 回滚预案 |

**强制产物**：体检的「工作流维护报告」同时充当观测快照与残差汇报；定向收敛的审计由 git 提交历史天然承担。

### 分支角色（三层模型的角色定义）

以下三角色是**三层模型**（菜单选项之一）的角色定义；其余模型的分支约定由托管块自行声明。

| 角色 | 含义 | 说明 |
|------|------|------|
| **`MAIN`** | 主干分支 | 上游主干，只接收已通过版本验证的代码 |
| **`PRE`** | 预发分支 | 预发发布分支，用于版本集成与环境验证 |
| **`DEV`** | 开发分支 | 本地开发分支，所有新改动先在此开发与自测 |

> **重要**：分支名称因项目而异（如 `master` / `xuanji/prepub`，或 `main` / `staging` / `dev`）。本技能在执行时**动态确认**实际分支名，将其记录到`docs/git-workflow.md` 的 Git Workflow 托管块（`${SKILL_WORKDIR}/docs/git-workflow.md`），后续操作以该块为准。

三层模型核心链路（角色代号）：

```
代码同步：MAIN -> PRE -> DEV
代码合入：MAIN <- PRE <- DEV
```

三层模型固定 rebase 关系：`PRE` 基于 `MAIN` rebase；`DEV` 基于 `PRE` rebase。其余模型的同步/合并关系由托管块声明（如临时分支模型：特性分支自主干切出、合回主干、随即删除；双分支：日常分支与归档/上游跟踪分支之间的同步节奏）。

---

## Workflow

### Phase 0: 调谐作用域判定

1. **版本漂移探测**：本技能随分支版本化——若会话开始时在旧分支加载了旧版技能文本、或会话中途切换过分支，加载文本可能与当前检出的 `${SKILL_HOME}/SKILL.md` 不一致（判据：状态文件位置约定不同——本技能约定 `docs/git-workflow.md`，`.specify/git-workflow.md` / `.specify/memory/git-workflow.md` 均为更早世代的旧约定）。命中漂移时：以当前检出为准，重新读取本技能与 references 后再继续判定；漂移未排除前不得写入任何状态文件，避免按旧约定重复建文档。无论加载文本约定哪个位置，均无条件探测最新位置 `docs/git-workflow.md` 的托管块，命中即直接以该块为数据源。
2. 若存在任一遗留数据源（前代位置 `.specify/git-workflow.md`、更早位置 `.specify/memory/git-workflow.md`，或更早版本写在 `.specify/instructions.md` `## Git Workflow` 章节内的托管块），先把其分支映射提取到 `docs/git-workflow.md` 的 Git Workflow 托管块，并把该遗留文件/旧块报告为「已冗余，待用户确认处理」——**不自动删除**（命令见 [bootstrap-commands.md](./references/bootstrap-commands.md#遗留配置迁移)；instructions 内旧块按 [instructions-lookup.md](./references/instructions-lookup.md) 的迁移规则替换为指针）。
3. 检查`docs/git-workflow.md` 的 Git Workflow 托管块是否已填写（存在 MAIN/PRE/DEV 行，且不是 `None yet.` 占位行）。
4. 检查用户是否传入了操作参数（具体的 git 操作指令）。

| 块已填写 | 有操作参数 | 进入作用域 |
|----------|------------|------------|
| 否 | — | Bootstrap 调谐（Setup） |
| 是 | 否 | 全维度体检（Maintain） |
| 是 | 是 | 定向收敛（Execute） |

---

### Bootstrap 调谐（Setup）— 建立工作流

当`docs/git-workflow.md` 的 Git Workflow 托管块缺失或仍是占位行时进入：期望态 = 用户选定模型的工作流骨架（不预设任何一个模型，尤其不得默认三层），通过最少必要问题（逐一确认，不臆造模型与分支名）+ 自动探测补齐信息。命令序列见 [bootstrap-commands.md](./references/bootstrap-commands.md)。

#### 1.0 选择工作流模型

先于一切分支问题，按上方菜单向用户推荐并确认**工作流模型**（每次只问一个问题；结合项目形态给推荐与理由，如 SDD 项目通常推荐「临时分支」）。选三层则继续 1.1–1.5 的三层实例化；选其他模型则按该模型形态确认其分支约定（单分支：仅确认主干名；双分支：确认两条长期分支的名字与角色分工；临时分支：确认主干名与特性分支命名惯例），随后同样走 1.4（写入托管块，含 `Workflow model` 声明行）；`.gitexcludes` 仅在模型存在长期并行层（如三层）时初始化（1.5）。

#### 1.1 检测现有分支

命令见 [bootstrap-commands.md#分支检测](./references/bootstrap-commands.md#分支检测)。

#### 1.2 交互式确认分支名（三层模型）

逐一向用户确认（每次只问一个问题），不臆造分支名：

1. **主干分支 `MAIN`**：推荐远端常见候选（`main`/`master`），询问选择或自定义。
2. **预发分支 `PRE`**：询问是否存在；不存在则建议命名（`staging`/`release`/`prepub`）。
3. **开发分支 `DEV`**：同上逻辑，推荐命名（`dev`/`develop`）。

#### 1.3 创建缺失分支

命令见 [bootstrap-commands.md#创建缺失分支](./references/bootstrap-commands.md#创建缺失分支)。

#### 1.4 写入 Git Workflow 块

读取模板 `${SKILL_HOME}/assets/git-workflow-block.md`，按选定模型渲染后写入`docs/git-workflow.md` 的 Git Workflow 托管块：先填 `Workflow model` 声明行（模型名）；三层模型再替换 `<MAIN>` / `<PRE>` / `<DEV>`（分支名）、`<MAIN_TRACKING>` / `<PRE_TRACKING>` / `<DEV_TRACKING>`（各分支 upstream，无则 `-`）、`<DATE>`（运行日期）；其他模型按其形态填写主干/特性分支约定等声明行（模板注释给出各模型最小行集）。

- 目标文件固定为 `${SKILL_WORKDIR}/docs/git-workflow.md`；定位与写入规则见 [instructions-lookup.md](./references/instructions-lookup.md)。
- 文件已存在且含 `<!-- GIT_WORKFLOW_START -->` … `<!-- GIT_WORKFLOW_END -->` 标记：**只替换标记之间的内容**，标记与块外内容字节保持。
- 文件不存在：用 `${SKILL_HOME}/assets/git-workflow-block.md` 渲染整文件后写入。
- 该文件由本技能独占维护，`/speckit.instructions` 不读写它——不要在别处另存分支信息，避免出现第二个数据源。

#### 1.5 初始化 `.gitexcludes`（分支排除规则）

`.gitexcludes` 定义本分支专属文件（语法同 `.gitignore`），目标分支的规则在同步时保护其专属文件不被覆盖。机制详见 [gitexcludes-subroutine.md](./references/gitexcludes-subroutine.md) 的设计原则，初始化命令见 [bootstrap-commands.md#初始化-gitexcludes](./references/bootstrap-commands.md#初始化-gitexcludes)。

---

### 全维度体检（Maintain）— 观测 + diff + 残差汇报

当`docs/git-workflow.md` 的 Git Workflow 托管块已填写且用户未传入操作参数时进入。只观测与 diff，不自动收敛；收敛建议列入报告尾部待用户确认。命令序列见 [health-check-commands.md](./references/health-check-commands.md)。

#### 2.1 加载配置

从`docs/git-workflow.md` 的 Git Workflow 托管块读取分支映射：三层模型取表格中 `MAIN` / `PRE` / `DEV` 行的 `Branch` 列（反引号内）；其他模型取 `Workflow model` 声明行与该模型的分支约定行（主干名、特性分支惯例等）。

#### 2.2 分支结构检查

命令见 [health-check-commands.md#分支结构检查](./references/health-check-commands.md#分支结构检查)。检查项随声明模型而定：三层模型查 MAIN/PRE/DEV 是否存在于本地和远端、tracking 是否正确；其他模型查其声明行对应的分支是否与实际一致。

#### 2.3 同步状态检查

命令见 [health-check-commands.md#同步状态检查](./references/health-check-commands.md#同步状态检查)。

#### 2.4 `.gitexcludes` 一致性检查

命令见 [health-check-commands.md#gitexcludes-一致性检查](./references/health-check-commands.md#gitexcludes-一致性检查)。检查项：各分支是否都有 `.gitexcludes`、排除路径是否仍被跟踪、规则是否符合预期。

#### 2.5 Git Workflow 块一致性检查

- 块中记录的分支名与实际分支是否一致（不一致属实质偏离，进入收敛建议）
- `Workflow model` 声明行存在且块结构与声明模型一致（三层模型须 MAIN/PRE/DEV 三行齐备、`Tracking` 与实际 upstream 相符；其他模型须其约定行齐备）、`Last updated` 存在
- 标记 `<!-- GIT_WORKFLOW_START -->` / `<!-- GIT_WORKFLOW_END -->` 成对存在（缺失会破坏"只替换标记之间内容"的写入规则）
- 不存在第二个数据源：`.specify/instructions.md` 内旧版 `## Git Workflow` 托管块、遗留 `.specify/git-workflow.md` 或 `.specify/memory/git-workflow.md` 若仍在，报告为冗余并按迁移规则处理

#### 2.6 输出维护报告

容忍带内的项标记「✅ 已一致」；仅实质偏离进入「建议操作」。报告模板见 [health-check-commands.md#维护报告模板](./references/health-check-commands.md#维护报告模板)。

---

### 定向收敛（Execute）— 执行工作流

当`docs/git-workflow.md` 的 Git Workflow 托管块已填写且用户传入了具体操作参数时进入：用户指令并入期望态，按下列预定义操作收敛，写远端/直接合入类动作遵循 Overview 的分级确认门禁。命令序列见 [execute-commands.md](./references/execute-commands.md)。
> Gate probe: gate-git-workflow-remote-ops — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).

#### 3.1 加载配置

同全维度体检 Step 2.1，从 `## Git Workflow` 块读取 `Workflow model` 声明行与分支映射（三层模型取 `MAIN` / `PRE` / `DEV` 表行；其他模型取其声明行）。

#### 3.2 前置校验

命令见 [execute-commands.md#前置校验](./references/execute-commands.md#前置校验)。

> **Gate**：`git status --short` 必须为空，才能继续执行。

#### 3.3 通用排除处理子程序（.gitexcludes Subroutine）

所有同步/合并操作均自动调用此子程序。详细实现见 [gitexcludes-subroutine.md](./references/gitexcludes-subroutine.md)。

**核心逻辑**：前置（保存状态 + 打印保护清单）→ 执行 rebase/merge → 后置（恢复排除文件 + 移除新引入文件 + 打印结果 + 提交 + 清理标签）。

> **设计原则**：谁接收代码（目标分支），谁的 `.gitexcludes` 说了算（方向无关）；`.gitexcludes` 本身是固定排除项，各分支内容可不同，永不被其他分支覆盖。

#### 3.4 解析并执行操作

根据用户指令匹配预定义操作。**操作 A–C 是三层模型的预定义操作**（触发词命中且声明模型为三层时使用）；其他模型（临时分支 / 双分支 / 单分支）按托管块声明的同步/合并关系理解指令，走操作 E 的通用拆解路径。

##### 操作 A: 代码同步（MAIN → PRE → DEV）

触发词：同步、sync、拉取上游更新。命令见 [execute-commands.md#操作-a-代码同步](./references/execute-commands.md#操作-a-代码同步)。
推送策略：仅 ahead → 正常推送；ahead + behind → 确认团队同步窗口后 `--force-with-lease` 推送（Security 规则 3-4）。

##### 操作 B: 提交到预发（DEV → PRE）

触发词：提交到预发、合入预发、merge to pre、提测。建议通过 PR 流程；或直接合入（需用户确认）。命令见 [execute-commands.md#操作-b-提交到预发](./references/execute-commands.md#操作-b-提交到预发)。

##### 操作 C: 提交到主干（PRE → MAIN）

触发词：提交到主干、合入主干、merge to main、发布。建议通过 PR 流程；或直接合入（需用户确认）。命令见 [execute-commands.md#操作-c-提交到主干](./references/execute-commands.md#操作-c-提交到主干)。

> **安全检查**：禁止跳过 `<PRE>` 直接把 `<DEV>` 合入 `<MAIN>`。

##### 操作 D: 基于指定分支 rebase

触发词：rebase、变基。命令见 [execute-commands.md#操作-d-rebase](./references/execute-commands.md#操作-d-rebase)。

##### 操作 E: 自定义操作

对于无法匹配预定义操作的用户指令，根据本技能的 Security 底线与 `docs/git-workflow.md` 托管块声明的分支关系理解用户意图，拆解为安全的 git 操作序列。

##### 操作 F: 管理 `.gitexcludes`

触发词：排除规则、gitexcludes、配置排除、分支专属文件、添加排除、移除排除。命令见 [execute-commands.md#操作-f-管理-gitexcludes](./references/execute-commands.md#操作-f-管理-gitexcludes)。

##### 操作 G: 验证排除效果

触发词：验证排除、检查排除状态、确认排除生效。命令见 [execute-commands.md#操作-g-验证排除效果](./references/execute-commands.md#操作-g-验证排除效果)。

---

### 作用域 B — 多环境协调（原 git-fleet）

**期望态**：同一逻辑仓库在各环境的可见状态一致（无跨环境未提交并发、无只存在于单机的提交、同分支 HEAD 一致），且仓库间依赖图与工作区实况一致。环境集合、transport、roots 全部来自调用方 inventory（环境无关硬约束）；逻辑仓库键 = 规范化 origin URL。引擎：

```bash
python3 "${SKILL_HOME}/scripts/git_fleet.py" --inventory <inventory.yaml> --state-dir <state> <scan|report|plan|sync>
```

只读巡检（`scan` / `report`，退出码 `10` = 有待协调项）→ 处置编排（`plan` 有序步骤标 SAFE/GATED；`sync` 默认干跑、`--apply` 收敛）。危险分级（`MULTI_DIRTY` / `HEAD_DIVERGED` / `STALE_REFS` / `SAME_ENV_CLONES` 等）与处置、依赖图证据分级与依赖优先排序：见 `references/fleet-workflow.md` 与其子页。

### 作用域 C — 子模块编辑（原 git-submodule-edit）

两条纪律：① 子模块内每次编辑都在 `project-<PARENT_SLUG>/<topic>` 分支上（自当前 gitlink 检出，绝不 detached HEAD / main）；② 父仓 gitlink 每次抬升追加一行到 `${SKILL_WORKDIR}/submodule-edits.md` 台账（旧→新 SHA、子模块分支、验证父仓分支/提交、验证状态）。全流程（进入 → 编辑 → 抬升 → 验证 → 上游回收）见 `references/submodule-workflow.md`，即用命令见 `references/submodule-command-recipes.md`；台账助手 `.specify/scripts/record-bump.sh`，模板 `assets/ledger-template.md`。

### 作用域 D — 服务器置备（原 git-server-init）

把只有 SSH 的服务器置备成 Git 服务器——四期望态：D1 git 用户、D2 裸仓库、D3 授权公钥、D4 本机 ssh config Host 条目（first-match-wins 陷阱见 `references/server-ssh-config-entry.md`）。可移植契约：MUST NOT 内嵌主机清单/IP/内部主机名/绝对用户目录；服务器身份一律由调用方参数传入。流程见 `references/server-workflow.md`；脚本 `.specify/scripts/provision-git-server.sh`（远端 D1–D3 观察/收敛）与 `.specify/scripts/ssh_config_insert.py`（本机 D4）；架构与排查见 `references/server-reference-architecture.md` / `references/server-troubleshooting.md`。

---

## Security / 安全底线

1. `<MAIN>` 禁止直接 push 未审查代码。
2. 禁止跳过 `<PRE>` 直接把 `<DEV>` 合入 `<MAIN>`。
3. 禁止 `git push -f`，仅允许 `git push --force-with-lease`。
4. 对共享分支执行强推前，必须完成"通知 + 同步窗口 + 回滚预案"。
5. 同步/合并后必须验证 `.gitexcludes` 匹配的路径未被意外修改。
6. `.gitexcludes` 文件本身是**固定排除项**，各分支独立维护，永不被其他分支版本覆盖。
7. 排除子程序的前置和后置必须打印明确的文件清单，供用户确认哪些文件被保护/移除。

## Known Issues & Mitigations

常见异常现象与应对策略见 [troubleshooting.md](./references/troubleshooting.md)。

## Git Workflow 块维护

- **创建**：Bootstrap 调谐（Setup）Step 1.4 用 `${SKILL_HOME}/assets/git-workflow-block.md` 渲染 `${SKILL_WORKDIR}/docs/git-workflow.md`（文件级模板）。
- **更新**：分支改名或 tracking 变化时改对应表格单元并刷新 `Last updated`；新增异常经验追加到 [troubleshooting.md](./references/troubleshooting.md)。
- **数据源**：`docs/git-workflow.md` 的 Git Workflow 托管块是后续所有操作的**唯一**分支名数据源；各分支的 `.gitexcludes` 是排除规则的数据源。`.specify/instructions.md` 只保留指向本文件的指针——操作规程留在本技能与其 references 中，避免第二个数据源。
- **边界**：该文件由本技能独占写入，`/speckit.instructions` 不读写它；instructions 文件内容不属本技能职责（旧版块迁移除外）。

## Resource ID

- Canonical ID: `<SKILL:.specify/skills/git-utils/SKILL.md>`
- Canonical Path: `.specify/skills/git-utils/SKILL.md`

## Path Conventions

- `${SKILL_HOME}/<relative-path>` — Skill-owned resources (scripts, references, assets).
- `${SKILL_WORKDIR}/<relative-path>` — runtime/user-facing paths.

## Resources

### References (`${SKILL_HOME}/references/`)
- `instructions-lookup.md` — 状态文件 `docs/git-workflow.md` 定位/创建规则与 Git Workflow 托管块写入规则。
- `gitexcludes-subroutine.md` — `.gitexcludes` 通用排除子程序详细实现。
- `bootstrap-commands.md` — Bootstrap 调谐（Phase 0-1）命令序列：迁移、分支检测/创建、`.gitexcludes` 初始化。
- `health-check-commands.md` — 全维度体检（Phase 2）命令序列：结构/同步/排除检查、维护报告模板。
- `execute-commands.md` — 定向收敛（Phase 3）命令序列：前置校验、操作 A-G 命令。
- `troubleshooting.md` — 异常现象与应对策略（Known Issues）。

- `fleet-workflow.md` / `fleet-inventory-schema.md` / `fleet-hazard-taxonomy.md` / `fleet-coordination-playbook.md` / `fleet-dependency-model.md` — 作用域 B（多环境协调）。
- `submodule-workflow.md` / `submodule-command-recipes.md` — 作用域 C（子模块编辑）。
- `server-workflow.md` / `server-ssh-config-entry.md` / `server-reference-architecture.md` / `server-troubleshooting.md` — 作用域 D（服务器置备）。

### Assets (`${SKILL_HOME}/assets/`)
- `git-workflow-block.md` — `docs/git-workflow.md` 整文件模板：文件头说明 + Git Workflow 托管块（含 `<MAIN>` / `<PRE>` / `<DEV>` / `<*_TRACKING>` / `<DATE>` 占位符与 START/END 标记）。
- `ledger-template.md` — 子模块编辑台账模板（作用域 C）。

### Scripts (`${SKILL_HOME}/scripts/`)
- `git_fleet.py` — 多环境巡检/报告/编排引擎（作用域 B；子命令与退出码见 `references/fleet-workflow.md`）。
- `provision-git-server.sh` — 远端 D1–D3 观察/收敛（作用域 D）。
- `ssh_config_insert.py` — 本机 ssh config D4 收敛（作用域 D）。
- `record-bump.sh` — 子模块 gitlink 抬升记账（作用域 C）。

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:git-utils" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:git-utils" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:git-utils" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
