---
name: git-fleet
description: |
  Multi-environment git coordination skill: keeps ONE developer's many git checkouts consistent across MANY machines, and models the dependency relations between the repos themselves. Collects a read-only, normalized state record per (repo, environment) — branch, HEAD, dirty counts, ahead/behind, stash, gitlink drift, fetch staleness — groups checkouts of the same logical repo by normalized origin URL, and raises a graded hazard taxonomy (uncommitted work in two environments, commits stranded on one machine, HEAD divergence, stale refs). Also derives the inter-repo dependency graph from first-hand workspace evidence (`.gitmodules` + gitlink SHAs + package manifests) and stores BOTH directions — depends-on and depended-on-by — so a change can be sequenced dependency-first and every submodule bump can name its affected consumers. Environment-agnostic by construction: every machine, transport and directory root comes from a caller-supplied inventory, so the skill contains no host list and no absolute paths of its own. Use this when the user mentions ["multi-machine git", "跨机器 git", "多环境 git", "git fleet", "环境 × 仓库", "哪台机器有没提交的改动", "改动散落在多台机器", "unpushed on another host", "仓库依赖关系", "被哪些项目依赖", "依赖图", "dependency graph", "submodule 依赖", "受影响的消费方", "affected consumers", "依赖优先顺序", "topological order", "checkout inventory", "stale clone"]
skill_id: "<SKILL:.specify/skills/git-fleet/SKILL.md>"
---

# git-fleet

## Overview

跨**环境**协调同一批 git 仓库，并维护这批仓库**彼此之间**的依赖关系。

两个既有技能各自只看一个仓库、一台机器：`git-workflow` 管单仓三层分支的调谐，
`git-submodule-edit` 管单个子模块的编辑与 gitlink 抬升。**都没有「同一个仓库同时
存在于多台机器」这个维度，也都没有仓库间依赖图**——本技能补的正是这两块，并把
落到单仓内部的 git 操作**原样委托**给它们。

本技能遵循 [`../../shared/patterns/reconcile-pattern.md`](../../shared/patterns/reconcile-pattern.md)：

- **期望态**：同一逻辑仓库在各环境的可见状态一致（无跨环境未提交并发、无只存在于
  单机的提交、同分支 HEAD 一致），且依赖图与工作区实况一致。
- **当前态**：一次只读巡检得到的 `环境 × 检出` 快照。
- **调谐**：观测 → diff（过容忍带）→ 分级收敛 → 校验。

**容忍带**（标「已一致」，不进收敛建议）：同一环境内的多份同源检出（并行克隆、
worktree）；子模块 HEAD 与其独立克隆不同（本就由父仓 gitlink 锁定）；`ahead/behind`
均为 0；仅 `untracked` 且被 `.gitignore` 之外的临时产物。

### 环境无关（硬约束）

本技能**不持有任何主机名、任何绝对路径**。环境集合、访问方式（transport）、
被管目录根（roots）全部来自调用方提供的 inventory 文件。这使同一份实现既能服务
「一台笔记本 + 二十台远端」，也能服务「只有本机」。机器专属事实属于调用方的
前门技能（本机入口层），不得写回本技能。

## When to Use / Not Use

| 场景 | 归属 |
|------|------|
| 同一仓库散落在多台机器，想知道改动都在哪 | **本技能** |
| 某个仓库改动前想知道会影响哪些下游项目 | **本技能**（`deps`） |
| 一批仓库要按依赖顺序依次升级 | **本技能**（`deps` 拓扑序） |
| 单仓三层分支同步 / rebase / merge / force-with-lease 决策 | `git-workflow` |
| 进子模块改代码、开分支、抬 gitlink、记账 | `git-submodule-edit` |
| 单仓 `.gitexcludes` 分支排除 | `git-workflow` |
| 代码评审 | `code-review` |

## Key Concepts

**逻辑仓库（logical repo）**：跨环境的连接键 = **规范化 origin URL**，而非路径——
同一仓库在不同机器上的路径通常不同（`/storage/project/<org>/<repo>` 与
`/cws_work/<repo>`），只有 origin 稳定。规范化会剥掉协议、`user@`、`.git` 后缀，
并把 scp 式 `host:path` 归一为 `host/path`。

**子模块单独成键**：检出若是子模块（`git rev-parse --show-superproject-working-tree`
非空），键上追加 `⊂<父仓名>`。原因：子模块 HEAD 由父仓 gitlink 锁定，把它与同源的
独立克隆比较只会产生噪音，不是协调信号。

**跨环境才算冲突**：`MULTI_DIRTY` / `HEAD_DIVERGED` 仅在检出**跨 ≥2 个环境**时成立。
同一台机器上的多份同源检出是刻意为之（并行克隆、worktree），降级为 `SAME_ENV_CLONES`
提示。

**HEAD 分歧是免疫 fetch 时效的证据**：`ahead/behind` 依赖上次 fetch，可能严重过期；
而「同一分支在两台机器上 HEAD sha 不同」是直接观测，无需 fetch 即可判定不同步。
因此 `STALE_REFS` 与 `HEAD_DIVERGED` 要一起读。

**证据分级（依赖边）**：`实测` = `.gitmodules` 声明且 gitlink 锁定；`半实测` =
manifest 声明但未解析到已知检出。**无证据不入图**——不依据仓库命名或描述推断依赖。
仓库在自己的 `go.mod` `module` 行或 `package.json` `repository.url` 里写自己的
origin，属自我声明，**不是依赖**，一律丢弃。

## Workflow

### Phase 0 — 准备 inventory

调用方提供环境清单；schema 见
[`references/inventory-schema.md`](references/inventory-schema.md)。
`roots` **就是管理边界**：不在 roots 下的仓库定义上不属本技能管辖。

```bash
python3 "${SKILL_HOME}/scripts/git_fleet.py" --inventory <inventory.yaml> --state-dir <state> <subcommand>
```

`--inventory` 亦可由 `$GIT_FLEET_INVENTORY` 提供，`--state-dir` 由
`$GIT_FLEET_STATE` 提供（缺省为 inventory 所在目录）。

### Phase 1 — 巡检（只读，自动执行）

```bash
git_fleet.py ... scan                      # 全环境并发
git_fleet.py ... scan --envs local,<host>   # 子集
```

探针严格只读：`--no-optional-locks`（不写 index）、**从不 fetch**、不改工作区。
不可达环境记 `unreachable` 而非静默跳过——报告会沿用其上次已知状态并标注时效。
产物：`<state>/snapshots/<YYYY-MM-DDTHHMM>.json`。

### Phase 2 — 协调报告（只读，自动执行）

```bash
git_fleet.py ... report --diff              # 追加与上次快照的增量
git_fleet.py ... report --repo <substr> --out <file.md>
```

按逻辑仓库分组，输出 `环境 × 检出` 矩阵与分级判定。危险度分级与处置见
[`references/hazard-taxonomy.md`](references/hazard-taxonomy.md)。
退出码：`0` 无待协调项，`10` 有。

### Phase 3 — 处置编排

```bash
git_fleet.py ... plan <repo-substr>         # 有序步骤，标注 SAFE / GATED
git_fleet.py ... sync --repo <substr>       # 干跑（默认）
git_fleet.py ... sync --repo <substr> --apply
```

排序原则：**独有的工作先落地**。只存在于一台机器上的提交必须先到达共享 remote，
其他环境才可以移动；否则先动别处会把这份工作推入更难合并的处境。完整决策见
[`references/coordination-playbook.md`](references/coordination-playbook.md)。

### Phase 4 — 依赖图与项目说明文档

```bash
git_fleet.py ... deps                       # 图 + 依赖优先顺序
git_fleet.py ... deps --docs --cross-reference '`../../{group}/relations.md`（人工策展视图）'
```

产物 `<state>/dependency-graph.json`（nodes + edges，双向已展开）与
`<state>/projects/<repo>.md`（每项目一档，含「依赖」与「被依赖」两节）。
`--cross-reference` 支持 `{group}` 占位符，且**仅在目标文件确实存在时**才写出该
引用行，避免悬空链接。边模型见
[`references/dependency-model.md`](references/dependency-model.md)。

## Safety

> Gate probe: gate-git-fleet-remote-writes — after the user decision, record firing evidence per `.specify/shared/guidelines/confirmation-gates.md` §门控观察协议 (non-blocking).

| 动作类 | 门禁 |
|--------|------|
| 巡检 / 报告 / 依赖图 / 生成文档（只读或只写本技能状态目录） | 自动执行 + 三要素执行报告 |
| `sync` 的 SAFE 集合：`fetch`、`branch <backup>`、`stash push -u`、`pull --ff-only` | 自动执行（默认干跑；`--apply` 生效） |
| `push` 及一切写共享 remote | **停下确认**（外部权威源） |
| 真分叉的 rebase / merge 决策 | **停下确认**，并委托 `git-workflow` |
| force-with-lease 强推共享分支 | **停下确认** + 委托 `git-workflow` |

**引擎级拒绝（不可绕过）**：`run_git` 对 `push` / `reset` / `merge` / `rebase` /
`checkout` / `switch` / `clean` / `gc` / `prune` / `filter-branch` / `cherry-pick` /
`revert` / `am` / `apply` 直接拒绝；`stash drop|clear|pop|apply`、`branch -d|-D`、
`remote remove|set-url`、`submodule update|deinit` 按前缀拒绝。`stash push` 允许，
因为它只增不减。因此本技能**在任何模式下都不可能**改写历史或写远端。

**注入面**：主机名与目录根会被插入远端 shell 命令行，故二者均按字符集白名单校验
（主机 `[A-Za-z0-9._-]`，路径 `[A-Za-z0-9._/+-]`），不合规直接判 `config-error`
而非放行。这挡住了形如 `-oProxyCommand=...` 的伪主机名。

**stash 归还**：`sync` 只在需要 ff-pull 时 `stash push -u`，**不自动 pop**——
自动 pop 一旦冲突会把冲突标记写进工作区。stash ref 会打印出来，由使用者自行归还。

## Known Issues

- **`ahead/behind` 取决于上次 fetch**：`scan` 不 fetch（保持只读），因此数字可能过期。
  `NEVER_FETCHED` / `STALE_REFS` 就是这个不确定性的显式标注；要精确数字先跑
  `sync`（其 SAFE 集合含 `fetch`）再 `scan`。
- **manifest 边只到「半实测」**：只做「manifest 里出现了内部 origin 字样」的文本取证，
  不解析版本约束、不跟随 lock 文件。用于提示存在耦合，不足以作为版本结论。
- **`depth` 与嵌套子模块**：默认 `depth: 4` 覆盖 `<root>/<org>/<repo>/<submodule>`。
  更深的嵌套需自行调高，代价是扫描变慢。
- **依赖环**：`deps` 检测到环时会显式告警并跳过拓扑排序，不会给出一个假的顺序。

## Resource ID

- Canonical ID: `<SKILL:.specify/skills/git-fleet/SKILL.md>`
- Canonical Path: `.specify/skills/git-fleet/SKILL.md`

## Path Conventions

- `${SKILL_HOME}/<relative-path>` — Skill-owned resources (scripts, references, assets).
- `${SKILL_WORKDIR}/<relative-path>` — runtime/user-facing paths.

## Resources

### Scripts (`${SKILL_HOME}/scripts/`)
- `git_fleet.py` — 引擎：`scan` / `report` / `plan` / `sync` / `deps`。只读探针、
  快照、危险度判定、SAFE 写白名单、依赖图与项目文档生成。无任何主机名与绝对路径。

### References (`${SKILL_HOME}/references/`)
- `inventory-schema.md` — inventory 逐字段 schema、transport 取值、roots 即边界、
  `roots_verified` 语义。
- `hazard-taxonomy.md` — 全部判定码（P0–P3）、判定条件、误报边界与处置指引。
- `coordination-playbook.md` — 跨环境处置决策：谁先落地、如何选权威环境、
  何时委托 `git-workflow` / `git-submodule-edit`。
- `dependency-model.md` — 依赖边模型、证据分级、双向存储、submodule 边身份
  （挂载路径 + 锁定分支 + 锁定 sha）、拓扑传播。

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:git-fleet" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
