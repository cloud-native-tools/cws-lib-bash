# Setup Recipes — 五步执行细则（sdd-project-setup）

> 本文件是 S1–S5 每步与 S3+ 强化序列的**操作手册**：判据、命令形态、凭证 schema、依赖契约。全部命令自包含可用；路径/用户/别名全部入口参数化（与 sdd-loop-driver 的参数占位约定一致：`<alias>` `<run-user>` `<project-dir>` `<tool>`）。

## 机制矩阵维度定义（S1）

`.specify/scripts/mechanism-inventory.py` 对 `<project-dir>/.specify/` 输出以下维度（每个 ok/missing）：

| 维度 | 判定 | 对应机制 |
|------|------|----------|
| const | `.specify/memory/constitution.md` 存在 | 合法基线（41/41 项目全有） |
| feat | `.specify/memory/features.md` + `features/` 目录 | 特性注册表（fork 扩充核心，fleet 采用率 37/41） |
| gloss | `.specify/memory/glossary.md` | 项目词汇锚（~63% 采用） |
| fb | `.specify/memory/feedback/` 目录 | 反馈库（feedback-utils 引擎载体） |
| reg | `.specify/memory/register.md` | ID 登记（最新机制，fleet 仅 2/41——激活优先级低但不静默） |
| kb | `.specify/memory/knowledge/` | 长期知识库 |
| session | `.specify/memory/session/` | 会话记忆 |
| tools | `.specify/memory/tools.md` + `tools/` | 工具注册表 |
| skills | `.specify/skills/` 非空 | 安装技能集 |
| tmpl | `.specify/templates/` | 阶段模板 |
| specs | `.specify/specs/` | 规格产物目录（计数） |
| src | `.specify/source.json` | 框架版本 provenance（版本+时间戳） |
| compat | `AGENTS.md`/`CLAUDE.md`/`QODER.md`/`.github/copilot-instructions.md` 是指向 `.specify/instructions.md` 的完好符号链接 | 多工具兼容层 |

**状态分级判据**（脚本自动判定）：

- `absent`：`.specify/` 目录不存在。
- `degraded`：const 缺失，或 skills+feat 两者皆缺（fleet 实测形态：asi-podinfo / alert-center / weekly-report-publish 类——只有零星目录）。
- `partial`：const 在位但矩阵有 2+ 项 missing，或 compat 链接断。
- `complete`：const+feat+skills+tmpl 全在位且 compat 完好（其余维度允许按项目需要缺失，但进凭证「未激活清单」）。

## S1 盘点命令形态

本地：`python3 <skill>/scripts/mechanism-inventory.py --project <path> [--json]`
远端：`ssh <alias> "python3 -" < <skill>/scripts/mechanism-inventory.py --project <project-dir>`（或先 scp 脚本再执行；只读，无副作用）

## S2 INSTALL

S2 分两层，**CLI 层先于项目层**：S2-0 python 运行时解析 → S2-1 specify CLI ensure/安装 → S2-2 项目 init / 刷新。

**执行侧界定**：S2 全部命令运行在**执行侧**（目标项目所在环境；远端形态经 `ssh <alias> "su - <run-user> -c '...'"` 在远端执行），编排侧本地宿主只做盘点派发、不安装 speckit、不误触发安装链——两侧角色划分、安装归属与反模式清单的真源见 `.specify/shared/workflow/execution-topology.md`（执行拓扑模型），本节只保留 S2 的应用。

### S2-0 Python 运行时解析（CLI 层前置）

> **所有权声明**：python 解析阶梯的**实现本体**已收归 spec-kit 仓根 `install.sh`（单一事实源）；本节只保留技能侧的适用要点，阶梯明细（含 `--python` / `SPECIFY_PYTHON` 优先级）不再在此复述——以 `bash install.sh --help` 与 install.sh 源码为准。

要点：

- 阶梯为 `--python` / `SPECIFY_PYTHON` → `<project-dir>/.venv/bin/python` → **既有安装的 python（upgrade-in-place）** → PATH `python3`（`python`）→ 系统 bin 目录最高版 `python3*`；install.sh 在其**运行目录**（`$PWD`）探测 `.venv`，故远端/本地均应 cd 到目标项目目录后再执行。升级与安装同路（clean reinstall）：无钉死/无 cwd venv 时优先升级既有安装所在环境，避免在无关 python 里装出第二份。
- **失败即停**：全缺 → 报错退出（exit 2），**绝不自动安装 Python**；pip 缺失同样报错退出（不代装）——缺运行时是环境缺口，自动安装会掩盖环境问题且不可控（fast-fail）。
- 选定环境后，可执行文件落在该环境的 bin 目录（venv 情形为 `<project-dir>/.venv/bin/`）——后续 `specify` 调用以该 bin 目录优先（`PATH=<bin>:$PATH` 或全路径调用），不得假设裸 `specify` 一定指向刚安装的环境。

### S2-1 specify CLI 安装（ensure / install 语义）

> **所有权声明（2026-10-21 起）**：specify CLI 冷启动安装逻辑的**单一事实源**是 spec-kit 仓根 `install.sh`（python 阶梯、内网优先三源回退、pip index 成对预检、uv opt-in、`specify check` 终验、退出码阶梯 0/2/3/5 全部在那里）。本技能与 cws-lib-bash 的 `specify_install` 均为**定位并委托** install.sh 的消费方，不持有任何安装逻辑副本；安装源清单、index 处理的变更只改 install.sh 一处。

- **ensure（幂等门）**：`command -v specify` 在位 → 跳过安装（升级 = 重新执行 install.sh，clean reinstall 语义，阶梯内 upgrade-in-place 级优先既有安装的 python）。
- **install（委托 install.sh）**：
  1. 获取 install.sh——本地 spec-kit checkout 直接用（`<spec-kit-checkout>/install.sh`）；无 checkout 时 `git clone --depth 1 <三源之首> /tmp/spec-kit` 后用其根目录 install.sh；
  2. `cd <project-dir>` 后执行 `bash <install.sh> [args]`——参数直接透传（`--python` 钉阶梯、`--intranet-only` 纯内网、`--index-url` 显式指定、`--dry-run` 只看计划）；
  3. 退出码契约：`0` 成功 · `2` 缺前置（python/pip/git/uv）· `3` 无可用「源 × index」组合或全源安装失败 · `5` `specify check` 终验失败——非 0 一律视为安装未完成，按码处置不重试盲跑。
- **验证**：install.sh 内置 `specify check` 终验；独立补验时在选定 bin 目录优先的前提下执行。
- **远端形态**：以上判定与安装命令整体经 `ssh <alias> "su - <run-user> -c '...'"` 在执行侧运行（占位约定同 S4）；install.sh 与 python 阶梯均在该侧判定与执行。

### S2-2 项目 init / 刷新

**absent → 全新安装（specify init）**——命令形态与脚本对齐（`<project-dir>` 默认 `.`）：

```bash
# 本地，单工具；--ignore-agent-tools 规则：claude/opencode/qoder 加，copilot 不加
specify init <project-dir> --ai <tool> --script sh --no-git --force --skip-tls [--ignore-agent-tools]
# 远端（经 su 与 sdd-loop-driver 同约定）
ssh <alias> "su - <run-user> -c 'cd <project-dir> && specify init . --ai <tool> --script sh --no-git --force --skip-tls [--ignore-agent-tools]'"
```

**`--ai all` 一次性全 agent（默认推荐，用户惯例）**：一次性更新所有 agent 的 init 产物——roster 固定 `claude → copilot → opencode → qoder` 逐工具执行同一命令，其中 **claude/opencode/qoder 加 `--ignore-agent-tools`、copilot 不加**（保留其 agent 工具检查，脚本原行为）。本地多 agent 工作站默认 all；远端/单工具场景按入口指定。

要点：`--force` 跳过非空确认、`--no-git` 不动 git、`--script sh` 选 POSIX shell 脚本、`--skip-tls` 容忍内网证书、`--ignore-agent-tools` 跳过对应 agent CLI 在位检查。安装后立即跑一次 S1 复扫确认 baseline。

**partial/degraded → 刷新**：走 `/speckit.instructions`（在目标项目以对应 agent 执行）——非破坏性 reconcile（自定义内容恢复、共享文件先备份、兼容符号链接重建）。**禁止**手工整目录覆盖 `.specify/`。

## S3 RECONCILE（基础调协——按 S1 缺口按需逐项，惯常次序）

**次序固定、按需触发**：以下五个治理命令按此顺序执行，但**只执行 S1 判定存在缺口的项**——已就绪的项跳过并登记；不存在的机制不预建（tools/register 等低频机制缺≠错）。

| 次序 | 命令 | 触发条件（S1 矩缺） | 调协效果 |
|------|------|---------------------|----------|
| 1 | `/speckit.constitution` | const 缺 | 宪法 bootstrap（模板→项目语境→占位填充→版本裁决） |
| 2 | `/speckit.sanitize` | 框架资料存在陈旧残留（过期索引/死链/镜像漂移；complete 状态也可能有） | 框架资料卫生治理，陈旧残留按两级判据清理 |
| 3 | `/speckit.feature` | feat 缺 | 特性注册表种子（对既有代码 reconcile，非空仓常翻出大量 Implemented） |
| 4 | `/speckit.instructions` | compat 断、instructions 过期、partial/degraded 刷新、**instructions 体积超预算（generator `BUDGET ... over`）** | 项目指令文件 + 各工具兼容符号链接重建；超预算时执行 § S3.4 收敛 |
| 5 | `/speckit.docs` | 文档空间与实况漂移（docs 树与代码/特性不一致） | 文档空间治理（委托 create-docs 收敛核对） |

每项执行后登记（执行/已存在/跳过+理由）；全部处理或声明后接强化序列。**不做整建**：五项之外的机制（glossary/feedback 目录/知识库目录等）仅在 S1 判缺且项目语境需要时逐个补建，否则进「未处理清单」。

### S3.4 Instruction size-budget convergence（R3 fallback）

`/speckit.instructions` 的生成器报告（`BUDGET: <size> <budget> over`）是**收敛触发**，不是转述给用户的装饰性告警。处理顺序：

1. **先走 owner 的 R1/R2**：`/speckit.instructions` 已内置 `manage-instructions` Action 5 的 R1（模板拥有章节压缩）与 R2（project-owned 章节 >4 KB 外迁）；若报告回到 `within`，本步结束，登记 `converged(R1/R2)`。不要在 setup 侧重实现 R1/R2。
2. **R3 回退（project-filled 大章节外迁）**：仅当 R1/R2 无合法候选、报告仍 `over` 时执行。读取生成器的 section table，按 `live B` 降序选择 `placeholder=yes` 且 `delta > 0` 的 project-filled 章节（排除纯指针/纯汇总章节，如 `## Documentation Map` 本身）：
   - 先找该章节已声明的 owner 文档；没有则在 `docs/` 下新建 owner 文档（复用 `create-docs` 的目录约定），把章节正文**机械迁移**过去；
   - 断言每条 bullet/段落都已落到 owner 文档且仅出现一次；断言通过后才把 instructions 中的章节替换为“一段摘要 + owner 文档指针”；
   - 在 `## Documentation Map` 增加该 owner 文档行；保留原有内容，不得手工转写或丢弃；
   - 每次只迁移一个章节，迁移后重跑 `/speckit.instructions`（或生成器）复测，直到 `within` 或没有可迁移章节。
3. **仍超预算 = pending**：列出剩余最大章节与原因，向用户给出三项选择——上调预算（`INSTRUCTIONS_BUDGET_BYTES` 的 owner 决策）/ 拆分章节 / 接受超预算；不得静默宣布完成，也不得删除项目内容换取绿色。
4. **幂等**：`within` 稳定态重复执行零写动作；R3 只处理 `over` 的 project-filled 候选。

**Guardrails**：R3 是 setup 初始化场景的回退路由；R1/R2 的 owner 仍是 `manage-instructions`，本步骤不改变其判据。不得修改预算常量、不得 push、不得把 owner 文档迁移变成手工摘要。

## S3+ STRENGTHEN（强化序列——机制就绪后的增值建设，按需逐项）

基础调协让机制就绪；强化序列用框架的内容类命令把项目从「机制可用」推进到「知识与规划在位」。**按需触发**（沿用声明式缺口原则）：对应资产已存在且无退化时声明跳过；入口可显式指定只跑其中某几项。次序有依赖，不并行：

| 次序 | 命令 | 触发条件（缺什么） | 强化效果 |
|------|------|---------------------|----------|
| 1 | `/speckit.history` | `.specify/history/` 缺或明显落后于会话存量 | 蒸馏当前工具的会话历史为主题聚合知识库（增量式，重跑只补新会话）——产出素材待 docs 挂载 |
| 2 | `/speckit.docs` | 有待挂载的新素材（history 产物）或文档空间待深化 | 文档建设深化：吸收 history 蒸馏的素材为文档与知识库添加资料（委托 create-docs 引擎收敛） |
| 3 | `/speckit.research` | 项目尚无深度调研结论（spec 侧无 research 产物/知识库无调研记录） | 对项目做深度调研与分析（技术栈/架构/依赖/风险），结论落 spec 侧，供 feature 与 goal 消费 |
| 4 | `/speckit.feature` | 特性注册表空/稀疏，或调研结论揭示特性缺口 | 基于调研结论生成合适的特性列表（对既有代码 reconcile 出注册表条目） |
| 5 | `/speckit.goal` | 项目无 goal 定义 | 分析项目最佳演进方向与终态（吸收调研结论），定义 **3–5 个**项目级目标——数量下界保证有牵引，上界防目标稀释 |

衔接要点：

- **history → docs**：history 先蒸馏素材，docs 随后建设（顺序有依赖：素材先行，docs 消费）。
- **research → feature → goal**：调研结论是特性生成与演进方向分析的共同输入；goal 收链尾。
- 强化产物自然进入 S5 候选清单（features 来源此时非空；goal 定义的目标是清单的天然推进项）。
- 每项执行后登记（执行/已存在/跳过+理由），与基础调协同一声明式缺口纪律。
- 边界：强化是项目级内容建设，**不推进任何特性的 SDD 开发阶段**（requirements→…→review 归 sdd-loop-driver）。

## 幂等与重入语义（多执行收敛）

一个项目可多次执行本技能。**收敛契约**：每次执行 = S1 盘点定缺口 → 仅缺口项执行 → S4 复核 → S5 候选清单刷新；**同一稳定态上重复执行零结构写动作、零内容重建**（N 次执行收敛到 1 次执行的效果）。缺口凭据永远是**本次** S1 盘点（机制矩阵 + S3+ 触发条件逐项判定），不是上次执行的记录——禁止凭记忆跳过或重做。

**逐命令重入语义**（重复执行时各命令的行为保证）：

| 命令 | 就绪态重入行为 | 保证 |
|------|----------------|------|
| python 解析（S2-0） | 每次执行都按阶梯重新解析（结果绑定本次 pip/specify 操作）；三级全缺 → 报错退出 | 无隐藏状态 |
| CLI 安装（S2-1） | `specify` 在位 → **不重装**（clean reinstall 仅限显式升级请求）；三源全败 → 缺口停止 | 环境不重建 |
| `specify init`（S2-2） | **不执行**——触发条件仅 S1=absent；非 absent 项目 **MUST NOT** 带 `--force` 重跑（会覆盖既有 `.specify/`，破坏性） | 结构不重建 |
| `/speckit.instructions`（S2/S3） | 非破坏性 reconcile：自定义内容恢复、共享文件先备份、符号链接重建——重跑安全 | 幂等收敛 |
| `/speckit.constitution`（S3） | 宪法在位 → 跳过（仅 bootstrap 缺失项）；不重写已 ratify 的宪法 | 内容不覆盖 |
| `/speckit.sanitize`（S3） | 可重入——陈旧残留按两级判据清理，无残留则零动作 | 天然幂等 |
| `/speckit.feature`（S3/S3+） | 注册表在位 → reconcile 式补条目（对既有代码翻出新特性），非重建 | 增量幂等 |
| `/speckit.docs`（S3/S3+） | 委托 create-docs 收敛核对——重跑只处理新漂移 | 天然幂等 |
| `/speckit.history`（S3+） | **增量式**——重跑只蒸馏新会话，既有主题聚合不重建 | 增量幂等 |
| `/speckit.research`（S3+） | 调研结论在位且未过期 → 跳过；过期/缺失 → 补调研 | 按需 |
| `/speckit.goal`（S3+） | goal 定义在位（3–5 个）→ 跳过；不重复定义 | 内容不覆盖 |

**稳定态快路径**：S1 判 complete 且 S3+ 触发条件全不命中 → 直接 S4 复核 → S5 候选清单刷新，**零写动作**（候选清单刷新是唯一输出）。

## S4 VERIFY（五族前置检查 + 矩阵 + 链接）

**五族前置检查**（2026-10-16 上收——权威落点 `.specify/skills/internal/run-agent/references/dispatch-preflight.md`，本节引用不复写；结论每项 ≤3 行摘要写入凭证。本技能处置后仍缺 = ⑤ fail 语义）。

加上：机制矩阵复扫达 complete（或 partial 且缺口已声明）、compat 链接核验 `find <project-dir> -maxdepth 2 -type l ! -exec test -e {} \; -print` 为空。三者齐备才进 S5。

**远端命令形态与占位约定**（`<alias>`/`<run-user>`/`<project-dir>`/`<tool>`）同 `.specify/shared/workflow/external-dispatch-recipes.md`（远端拓扑）——本文件仅保留 setup 特有命令（python 解析 / CLI 安装 / specify init / 机制盘点脚本），通用派发形态坍缩为引用（analyze C-31）。

## S5 候选工作清单（建议而非强制）

调协完成后产出一份**候选工作清单**——提示接下来可以做哪些事。三个内部来源（无用户明确指定时）：

1. **未完成的 feature**：`/speckit.feature` 维护的注册表中状态非 Implemented/Completed 的条目（Draft/Planned/Ready for Review 的推进项）；
2. **feedback 反馈的规模较大改进**：feedback 库中反复出现、标记为需要框架级或跨特性处理的条目（高频= toll，已到阈值的上送件也算）；
3. **speckit TODO 事项**：`/speckit.todo` 命令及相关机制维护的 TODO 表（SPECKIT TODO 块 + parked ideas）。

清单 schema（落宿主工作目录）：

```yaml
# sdd-candidates-<project-slug>-<YYYYMMDDTHHMM>.yaml
target: {alias|local-path, run-user, project-dir}
reconcile: {grade_before, grade_after, matrix, actions, unprocessed: [...]}
sources:
  features: [{id, name, status, next: "推进到 <下一状态>"}]
  feedback: [{entry, count_or_signal, suggestion}]
  todos: [{item, location}]
suggestion: >-
  以上为候选工作；如需以 SDD 全流程推进某项，可调用 sdd-loop-driver
  （可选，非强制；sdd-loop-driver 亦可不经本技能独立运行）。
```

**语义红线**：清单是「有哪些可做的事」的提示，不携带任何「必须调用 sdd-loop-driver」的语义；调用与否由用户或上游流程决定。

## 软协同契约（与 sdd-loop-driver）

- **非强绑定**：两技能各自可独立运行。本技能不要求 sdd-loop-driver 存在，sdd-loop-driver 也不依赖本技能先行——其 preflight 已上收 run-agent 公用承载（`.specify/skills/internal/run-agent/references/dispatch-preflight.md`，analyze C-30），⑤ fail 时经该处置链 handoff 给本技能。
- **本技能 → sdd-loop-driver**：S5 候选工作清单是建议入口之一；sdd-loop-driver 的输入源除清单外还包括用户明确指定的特性/切片。
- **sdd-loop-driver → 本技能**：其 preflight 发现 `.specify/` 缺失/宪法不在位/机制退化时，把处置 handoff 给本技能（模式由探测定：缺失=install，退化=refresh），处置完成后回到循环。
- 职责切分线：**框架调协（install/reconcile/strengthen/verify/候选清单）** = 本技能；**SDD 完整阶段循环/状态脊/收尾纪律** = sdd-loop-driver。互不越界，互不强依赖。
