# Execution Topology (执行拓扑) — 编排侧与执行侧的两环境模型

Single source of truth for the **two-side execution topology** of the SDD-driving external skills (`sdd-project-setup`, `sdd-loop-driver`). It exists because the two skills are routinely misread as running "wherever the project is" — the most costly misreading is installing or initializing the speckit framework on the wrong side. Per-skill files keep only their own application of this model and point here; command shapes stay in [`external-dispatch-recipes.md`](external-dispatch-recipes.md) (§ Two Topologies), the dispatch *declaration* stays in [`../definitions/subagent-definitions.md`](../definitions/subagent-definitions.md) (§ Execution Topology Declaration), and preflight stays in run-agent `references/dispatch-preflight.md`.

## The Two Sides

| | 编排侧 (orchestration side) | 执行侧 (execution side) |
|---|---|---|
| **是谁** | 加载技能手册的宿主 agent 所在环境（通常是本地开发机 / IDE 会话） | 目标项目所在、承载 `specify` 与 `/speckit.*` 命令的环境（通常是远端开发机，经 `ssh <alias>` + `su <run-user>` 进入） |
| **跑什么** | 技能编排逻辑本身（盘点派发、阶段循环 U0–U6、日志轮询、独立校验、状态脊） | 子代理 agent CLI（如 `qodercli`）+ 目标项目内的 `/speckit.*` 与 `specify` 命令 |
| **需要 speckit 吗** | **不需要**（`specify` CLI、python-speckit 运行时、`.specify/` 均非必需） | **需要**——`.specify/` 结构 + `specify` CLI 是执行 `/speckit.*` 的前提 |
| **缺 speckit 时** | 不构成缺口；**不得误触发安装链** | 构成缺口 → sdd-project-setup S2 在此环境安装（python 解析阶梯 + 三源 pip 回退） |
| **到达方式** | —（就是本会话） | `ssh`/`su`，或本地退化形态直接执行 |

```text
编排侧（本地宿主 agent，加载 sdd-project-setup / sdd-loop-driver）
  │  ssh <alias>  →  su - <run-user>
  ▼
执行侧（远端开发机 · 目标项目目录）
  └── 子代理 agent CLI（qodercli -w <project-dir>）
        ├── /speckit.* 阶段与治理命令        ← 需要 .specify/
        └── specify init / specify check     ← 需要 specify CLI（S2 在此安装）
```

**本地退化形态**：目标项目就在编排侧本机时，两侧坍缩为一侧——判定基准始终是「目标项目所在环境」：speckit 的安装、初始化、`/speckit.*` 执行都发生在那个环境里，与宿主 agent 恰好也在这台机器上无关。

**技能与子代理不同环境是常态而非例外**：技能（编排侧）通常在本地 agent 中运行，经 ssh 登录远端开发机启动子代理执行操作。编排侧缺 `specify`/venv 不是缺口、不触发安装；一切安装与初始化动作都在执行侧发生。

## Per-Skill Mapping

| 技能 | 编排侧执行的部分 | 执行侧执行的部分 |
|------|------------------|------------------|
| **sdd-project-setup** (S0–S5) | 加载手册、跑 `mechanism-inventory.py`（只读脚本经 ssh 推送到执行侧执行）、派发与登记、S4 复核汇总、S5 候选清单 | S2 全部（python 解析阶梯 → specify CLI 安装 → `specify init`，远端经 `ssh … "su - <run-user> -c '…'"`）；S3/S3+ 治理与强化命令（以子代理承载或远端直执） |
| **sdd-loop-driver** (U0–U6) | 加载者即驱动者：U0 入口、U1 断点探测（ssh 只读探测）、U2 派发（写 prompt/runner 文件到执行侧）、U3 轮询、U4 独立校验、U5 卡死处置、U6 收尾汇总——全部亲自执行，不委托 subagent | 阶段子代理在项目目录内执行 `/speckit.*` 阶段命令（runner 脚本承载，后台执行 + 日志回传） |

两侧一致的判定线：**凡是读写目标项目、调用 `specify`/`/speckit.*` 的动作 → 执行侧；凡是编排、判定、轮询、校验、落状态脊的动作 → 编排侧。**

## Anti-Patterns (误读纠正)

- **在编排侧安装 speckit**：宿主 agent 没有 `specify` 就本地 `pip install` —— 错。执行侧（目标项目环境）才需要；编排侧安装无法让远端子代理用上，且污染编排环境。
- **把 S1 盘点跑在编排侧本地路径**：目标项目在远端时，盘点脚本必须经 ssh 推送到执行侧对 `<project-dir>` 运行；本地路径上的扫描结果与目标项目无关。
- **把驱动循环嵌进子代理**：驱动者（编排侧宿主 agent）亲自执行 U0–U6；子代理只收阶段提示词（嵌套驱动禁止，义务真源见 subagent-definitions § Dispatch-Time Governance Obligation）。
- **用编排侧视角解读执行侧的缺口报告**：S2 报「python 三级全缺 / 三源安装全败」指的是**执行侧**环境缺这些，不是编排侧。

## Boundary

- 本文档拥有**两侧角色划分 + speckit 安装归属**这一模型；两拓扑（remote/local）的具体命令形态归 [`external-dispatch-recipes.md`](external-dispatch-recipes.md)，派发生命周期与可见性契约归 [`../definitions/subagent-definitions.md`](../definitions/subagent-definitions.md)，五族前置检查归 run-agent `references/dispatch-preflight.md`。若本文与命令配方冲突，角色模型以本文为准，命令以配方为准。
- 团队（/speckit.team）经 `dispatch.sh` 的派发不改变本模型：团队座位同样是执行侧形态。
