# Git workflow observation hook（观测钩子）与初始化模板

本页是 git-utils 作用域 A 的**机制说明**：初始化模板播种、probe + handler 观测钩子、
`observe` 动作面、以及「Observed facts (machine, dated)」小节的语义。

**边界（机制 / 策略分离）**：

| 面 | 所有者 | 内容 |
|----|--------|------|
| **策略（声明）** | `.specify/workflow/git.md` 的 `GIT_WORKFLOW` 托管块 | 工作流模型、分支结构、同步/合并关系、收口策略——只经 Bootstrap 与用户确认变更 |
| **策略骨架（初始文件）** | 框架源 `.specify/templates/workflow/git.md` | `specify init` 在目标缺失时播种为 `.specify/workflow/git.md` |
| **机制（观测）** | `.specify/scripts/python/git-workflow-observe.py`（运行态 `.specify/scripts/python/`） | 只刷新 `GIT_OBSERVED` 标记间的机器观测小节 |

三条硬规则：

1. **观测不等于声明**：观测小节只记录可从仓库/状态文件直接读到的事实；模型与分支声明
   （`GIT_WORKFLOW` 标记之间）**永不**由观测动作写入。
2. **托管块渲染模板唯一**：托管块的渲染模板是 `${SKILL_HOME}/assets/git-workflow-block.md`；
   `.specify/templates/workflow/git.md` 只是文件级骨架（文件头 + `None yet.` 占位块），不分叉块内容。
3. **单数据源不变**：分支名仍只在 `GIT_WORKFLOW` 托管块；观测小节不成为第二个数据源。

## 1. 初始化模板（specify init）

- 源：`.specify/templates/workflow/git.md`；`specify init` 在 `.specify/workflow/git.md` **缺失时**播种，
  已存在时**永不覆盖**（升级/重跑安全——既有文件是项目策略）。
- 骨架内容：机器维护文件头 + `GIT_WORKFLOW_START/END` 标记 + `- **Workflow model**: None yet.`
  占位行——这正是 Bootstrap 作用域的判定依据。
- Bootstrap 之后：文件已含标记，按 `instructions-lookup.md` 的「只替换标记之间内容」规则填充。

## 2. 钩子（probe + handler 机制，056 二期）

注册表行（`.specify/shared/definitions/probe-definitions.md`，运行时镜像 `.specify/shared/definitions/`）：

| 面 | 行 |
|----|----|
| Handler | `h-git-workflow-observe` · kind=engine · action=`observe` · non-blocking · order 20 · behavior_owner `.specify/scripts/python/git-workflow-observe.py` |
| HandlerBinding | `h-git-workflow-observe` · `@point:situation` · scope `all` |

**运行期派发**（实测事实）：`@point:situation` 是声明性订阅（无编译面）；情境引擎
`trigger-utils.py --action assess` 在写完本回合遥测行与触发状态之后，按注册表查询
`@point:situation` 的 kind=engine handler，并逐个以各自脚本的 `--action <action>` 调用——
排除属于 assess 引擎自身 action 闭集的 handler（即 `h-situation-assess` 自身，保证不递归）。
非阻塞：任何失败（注册表缺失、查询失败、handler 崩溃、超时）只落入 assess 信封的 `notes[]`，
不影响退出码与遥测。

校验命令（三个面各自绿才算接好）：

```bash
python3 .specify/scripts/python/probe-utils.py --action handlers --validate
python3 .specify/scripts/python/probe-utils.py --action compile-embeds --check   # 二期行不进 wrap-up 编译面 ⇒ 零漂移、指纹不变
python3 .specify/scripts/python/probe-utils.py --action probes --validate --reconcile
```

## 3. `observe` 动作面

```bash
python3 .specify/scripts/python/git-workflow-observe.py --action observe [--check] [--json] [--workspace PATH]
```

| 项 | 行为 |
|----|------|
| 读取 | `.specify/workflow/git.md`（定位沿用显式 `--workspace` > 引擎自定位 > CWD 上溯）+ 只读 git 事实：本地分支、远程名、声明行 |
| 写入 | 只写 `GIT_OBSERVED` 标记之间的观测小节；托管块与块外其他内容字节保持 |
| 幂等 | 事实未变时不写（`--check` 退出 0）；事实变化才改写，并刷新 `Observed at` |
| `--check` | 不写；有待更新退出 `10`，无则 `0` |
| 退出码 | `0` ok（更新/未变/跳过）· `1` usage · `2` 输入错误 · `10` `--check` 有待更新 |
| 跳过（退出 0） | `workflow-state-file-absent` / `workflow-block-unusable` / `observed-markers-unusable`（不修复、不猜测） |

观测项（固定标签）：`Trunk`（声明来源优先，缺失时按 `main`/`master` 本地存在性探测）、
`Remotes`、`Remotes vs declaration`（声明 ↔ 实际差集）、`Feature-branch naming`（非声明
本地分支的命名形态统计）、`Closeout declaration`（`Closeout` 行存在性）。非 git 仓库时记为
`Repository: not a git repository`。

## 4. 观测小节的读取语义

- 小节位于 `GIT_WORKFLOW_END` 之后，由 `<!-- GIT_OBSERVED_START -->` / `<!-- GIT_OBSERVED_END -->`
  包围；`Observed at` 是观测时间，只在其他事实变化时刷新。
- 它是**证据**：为下一次 Bootstrap 的模型推荐、全维度体检的残差判断提供机器读数；
  任何流程都不得把小节内容当作声明读取（声明只读托管块）。
- 体检（Phase 2）可手动刷新：命令见 `health-check-commands.md` § 观测事实刷新。
