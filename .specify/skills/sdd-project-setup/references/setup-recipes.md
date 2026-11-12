# Setup Recipes — bootstrap 执行细则（sdd-project-setup）

> 本文件是 **bootstrap 侧**的操作手册：S1 盘点、S2 安装/刷新、S2.5 首批内容、HANDOFF。
> 周期性 reconcile / strengthen / verify / 记录回收 / 候选清单归 `sdd-house-keeping`，细则见
> `sdd-house-keeping/references/maintenance-recipes.md`。全部命令自包含可用；路径/用户/别名
> 全部入口参数化（`<alias>` `<run-user>` `<project-dir>` `<tool>`）。

## 目标解析

共享唯一契约：`.specify/shared/workflow/target-resolution.md`。**setup 不依赖 `.specify/`**：
未给目标 → **当前项目**（git root；非 git 取会话 cwd）；显式目标优先；拒绝 basename `.specify`；
**不向上搜索 `.specify/`**——目标没有 `.specify/` 时由本 skill 创建/刷新。远端目标只在执行侧
扫描/执行。

## 机制矩阵维度定义（S1）

`.specify/scripts/mechanism-inventory.py` 对 `<project-dir>/.specify/` 输出以下维度（每个 ok/missing）：

| 维度 | 判定 | 对应机制 |
|------|------|----------|
| const | `.specify/constitution.md` 存在 | 合法基线 |
| feat | `.specify/features.md` + `features/` 目录 | 特性注册表 |
| gloss | `.specify/glossary.md` | 项目词汇锚 |
| fb | `.specify/memory/feedback/` 目录 | 反馈库 |
| reg | `.specify/register.md` | ID 登记 |
| kb | `.specify/memory/knowledge/` | 长期知识库 |
| session | `.specify/memory/session/` | 会话记忆 |
| tools | `.specify/tools.md`（§ Helper Tools Index）+ `tools/` | 工具注册表 |
| skills | `.specify/skills/` 非空 | 安装技能集 |
| tmpl | `.specify/templates/` | 阶段模板 |
| specs | `.specify/specs/` | 规格产物目录（计数） |
| src | `.specify/source.json` | 框架版本 provenance |
| compat | 兼容符号链接完好 | 多工具兼容层 |

**状态分级判据**（脚本自动判定）：

- `absent`：`.specify/` 目录不存在。
- `degraded`：const 缺失，或 skills+feat 两者皆缺。
- `partial`：const 在位但矩阵有 2+ 项 missing，或 compat 链接断。
- `complete`：const+feat+skills+tmpl 全在位且 compat 完好（其余维度允许按项目需要缺失，但进凭证
  「未激活清单」）。

## S1 盘点命令

```bash
python3 <skill>/scripts/mechanism-inventory.py --project <project-dir> --json
python3 <skill>/scripts/logical-framework.py --project <project-dir> --json
```

远端（SSH 传输 owner：`ssh-utils`；`<ssh-utils>` 为其技能目录）：
`python3 <ssh-utils>/scripts/ssh-exec.py --host <alias> --user <run-user> --cwd <project-dir> --script <skill>/scripts/mechanism-inventory.py --script-arg=--project --script-arg=<project-dir> --json`
`python3 <ssh-utils>/scripts/ssh-exec.py --host <alias> --user <run-user> --cwd <project-dir> --script <skill>/scripts/logical-framework.py --script-arg=--project --script-arg=<project-dir> --json`
拓扑形态仍是 `ssh <alias>` → `su - <run-user>` → `cd <project-dir>`；`ssh-exec.py` 固定带 `-o RemoteCommand=none`（主机预置 `RemoteCommand` 时裸 ssh 会与命令行冲突）。通用远端命令形态见 `.specify/shared/workflow/external-dispatch-recipes.md`。

逻辑矩阵：required（instructions / features / docs）、recommended（goals / glossary / register /
knowledge）、conditional（agents / teams）。退出码 `0` required 全 ok；`1` required 缺口；`2` 非
Spec Kit 项目。`--strict` 把 recommended 缺口也计为失败。**缺≠错**：recommended/conditional
缺口按项目语境声明，不自动算 fail。

## S2 INSTALL

S2 分两层，**CLI 层先于项目层**：S2-0 python 运行时解析 → S2-1 specify CLI ensure/安装 → S2-2 项目
init / 刷新。全部命令运行在**执行侧**（目标项目所在环境）；编排侧只做盘点派发，不安装 speckit。

### S2-0 Python 运行时解析

阶梯：`--python` / `SPECIFY_PYTHON` → `<project-dir>/.venv/bin/python` → 既有安装的 python →
PATH `python3`（`python`）→ 系统 bin 目录最高版 `python3*`。失败即停：三级全缺 → 报错退出
（exit 2），**绝不自动安装 Python**；pip 缺失同样报错退出。实现本体与 `--help` 以仓根
`install.sh` 为准。

### S2-1 specify CLI 安装（ensure / install）

- **ensure**：`command -v specify` 在位 → 跳过安装。
- **install**：委托仓根 `install.sh`（三源回退、`specify check` 终验、退出码 0/2/3/5）；非 0 一律
  视为安装未完成，按码处置不重试盲跑。
- 远端：以上判定与安装经 `ssh-utils` 的 `ssh-exec.py --host <alias> --user <run-user> --cwd <project-dir> --cmd '...'` 在执行侧运行（拓扑形态 `ssh <alias>` → `su - <run-user>` → `cd <project-dir>`；包装器固定 `-o RemoteCommand=none`）。

### S2-2 项目 init / 刷新

**absent → 全新安装（specify init）**：

```bash
specify init <project-dir> --ai <tool> --script sh --no-git --force --skip-tls [--ignore-agent-tools]
```

`--ai all` 一次性全 agent（默认推荐）：roster 固定 `claude → copilot → opencode → qoder`，其中
claude/opencode/qoder 加 `--ignore-agent-tools`、copilot 不加。安装后立即跑 S1 复扫确认 baseline。

**partial/degraded → 刷新**：走 `/speckit.instructions`（非破坏性 reconcile）；禁止手工整目录覆盖
`.specify/`。若刷新报告 `BUDGET ... over`，不要在本技能实现 R3——交给 house-keeping H2 的
Budget convergence（见下）。

## S2.5 BOOTSTRAP CONTENT（首批内容，只补缺失项）

只执行 S1 判定缺失的项；每项登记 `executed / existing / skipped + reason`。未处理项交给
house-keeping H5 的**未处理清单**。**不执行** sanitize、history、research 或完整 reconcile——这些
归 house-keeping H2/H3。五族前置检查与失败处置链的权威落点是
`.specify/skills/internal/run-agent/references/dispatch-preflight.md`；setup 不复制检查表。

| 次序 | 命令 | 触发 | 产出 |
|---|---|---|---|
| 1 | `/speckit.constitution` | `const` 缺 | 宪法 bootstrap（模板→项目语境→版本裁决） |
| 2 | `/speckit.feature` | `feat` 缺 | 注册表种子（对既有代码 reconcile） |
| 3 | `/speckit.docs` | `docs/` 缺 | 文档空间基线树 |
| 4 | `/speckit.goal` | goals 缺 | 定义 3–5 个项目目标 |
| 5 | `/speckit.agents` / `/speckit.team` | **按需**：用户明确需要 | 代理/团队定义；未使用则保持 `not-configured` |

**Carrier**：本地每个命令的派发 MUST 缺省用 **fork 承载**（同族 `qodercli` 子进程经
`.specify/skills/sdd-loop-driver/scripts/stage-runner.sh`）；异构 agent MUST 用 **subprocess 承载**
（该 agent 自身 CLI 的独立子进程）；宿主内建 in-process subagent 路径 **BANNED**，MUST NOT 被呈现
为一个选项。远端每个命令经 run-agent 在
`<project-dir>` 下执行——`ssh <alias>` → `su - <run-user>` → `cd <project-dir>`；subagent CLI 缺省
取 execution-config defaults（`cli: qodercli`），可按 agent/inline 覆盖。底层 SSH 传输一律经
`ssh-utils`，见下节。

S2.5 完成后，**首次 goal/agents/team 不得悬空**：目标项目若仍缺 goal 且用户未明确要求跳过，
setup 必须在 handoff 前完成或把 `bootstrap-gap: goal` 写入 handoff 凭证，由 house-keeping H3
回交 setup；house-keeping 不静默跳过。

## SSH 传输约定（owner: ssh-utils）

- 任何远端命令 MUST 经 `ssh-utils/scripts/ssh-exec.py`；它固定带 `-o RemoteCommand=none`。目标主机可能在 ssh_config 预置 `RemoteCommand`，裸 `ssh <alias> "..."` 会报 `Cannot execute command-line and remote command`——这是配置冲突，不是安全拦截。
- 传输失败先跑 `ssh-exec.py --host <alias> --check`：`remotecommand` 非 `none` 即证实该冲突；认证/引号/su/超时按 `ssh-utils/references/pitfalls.md` 分诊。
- `--user` 包装为 `su - <run-user> -c '...'`；`--cwd` 负责 `cd <project-dir>`；脚本用 `--script` 经 stdin 推送，不落远端临时文件；退出码原样传播（`124` 本地超时、`255` 传输失败）。

## HANDOFF（bootstrap → house-keeping）

1. 调用 `sdd-house-keeping` H0–H4（同一目标、同一模式；`check` 默认）。它负责 H1 盘点、H2 调协
   （含 `/speckit.sanitize --lane retention`）、H3 强化、H4 验证。
2. **ready 凭证**：只有 house-keeping H4 三条件同时成立，才返回 `ready`。house-keeping 不可用时
   返回 `bootstrap-complete / maintenance-pending` + `unprocessed` 缺口清单；不得冒充 ready。
3. **候选清单**：由 house-keeping H5 产出；setup 不再产出 `sdd-candidates-*.yaml`。
4. 目标项目已初始化且本次只需维护 → 直接加载 `sdd-house-keeping`，不重跑 `specify init`。

### Budget convergence pointer（S3.4 / R3）

完整 S3.4/R3（`BUDGET`、`placeholder=yes`、`pending`）归 house-keeping
`maintenance-recipes.md` § Budget convergence；setup 只转发生成器报告，不实现 R3。

### Hook health pointer（S4-H）

`hook-health.py` 与 `S4-H` 归 house-keeping H4；`vendor-managed` hook 只报告不自动改。本地拓扑
只适用 ④ LLM 配置/⑤ framework 可用性，①–③ 记 `n/a`。

## 幂等与重入

一个项目可多次执行本技能。收敛契约：每次执行 = S1 盘点定缺口 → 仅缺口项执行 S2/S2.5 → HANDOFF。
同一稳定态上重复执行零结构写、零内容重建。

| 动作 | 就绪态重入行为 |
|---|---|
| python 解析（S2-0） | 每次按阶梯重新解析；三级全缺 → 报错退出 |
| CLI 安装（S2-1） | `specify` 在位 → 不重装 |
| `specify init`（S2-2） | 触发条件仅 S1=absent；非 absent MUST NOT 带 `--force` 重跑 |
| `/speckit.instructions`（S2-2） | 非破坏性 reconcile；`within` 稳定态零写 |
| `/speckit.constitution`（S2.5） | 宪法在位 → 跳过；不重写已 ratify 的宪法 |
| `/speckit.feature`（S2.5） | 注册表在位 → 不重建；house-keeping H2 负责 drift reconcile |
| `/speckit.docs`（S2.5） | docs 树在位 → 不重建；house-keeping H2 负责漂移收敛 |
| `/speckit.goal`（S2.5） | goal 在位（3–5 个）→ 跳过 |
| `/speckit.agents` / `/speckit.team`（S2.5） | 未使用 → 跳过；不预建 |

## 软协同契约（三技能）

- **非强绑定**：三个技能各自可独立运行。
- **setup → house-keeping**：bootstrap 完成后 handoff H0–H4；ready 凭证来自 H4。
- **house-keeping → setup**：目标项目缺 `.specify/`/constitution，或 H3 发现 goal/agents/team
  bootstrap-gap 时回交 setup。
- **setup → sdd-loop-driver**：候选工作清单由 house-keeping H5 提供，是建议而非强制；不携带
  任何「必须调用 sdd-loop-driver」的语义。
- **sdd-loop-driver → setup**：其 preflight ⑤ fail 时 handoff setup 做 bootstrap；bootstrap 完成
  后再按需 handoff house-keeping 做周期维护。
- 职责切分线：bootstrap = setup；周期维护 = house-keeping；SDD 阶段循环 = loop-driver。
