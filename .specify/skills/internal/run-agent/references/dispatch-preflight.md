# Dispatch Preflight — 派发前置检查（run-agent 公用承载）

> 本文件是 run-agent 派发任何外部子代理前的**前置检查表与失败处置链**（上收落点——原 sdd-loop-driver 自持表与 sdd-project-setup S4 表坍缩至此，行集行为平价；裁定日期 2026-10-16，provenance 见规格链）。所有路径、用户名、别名均为入口参数占位——机制零硬编码。检查先于派发：任一项不通过，MUST NOT 进入派发。

## 五族前置检查

任一项无法自动核验或核验结果不确定时，停在前置阶段、提示用户补充或按失败分类处置。检查结论（逐项 ok / fail / uncertain）以**每项 ≤3 行摘要**写入调用方的状态脊/派发凭证的前置检查段（不全文回显）。

| # | 检查 | 命令形态 | 判定 |
|---|------|----------|------|
| ① | SSH 连通性（**本地拓扑跳过**） | `ssh -o ConnectTimeout=5 -o BatchMode=yes <alias> true` | 限时内 0 = ok；超时/拒绝 = fail |
| ② | 非 root 运行用户存在性 | `ssh <alias> "id <run-user>"` | uid≠0 = ok；不存在或 uid=0 = fail |
| ③ | 子代理 CLI 可用性与版本 | `ssh <alias> "su - <run-user> -c '<cli> --version'"` | 版本串 = ok（版本号记录进凭证）；不在 PATH = fail |
| ④ | 大语言模型配置（**已解析配置**） | 在**目标项目侧**运行 `python3 .specify/scripts/python/execution-config.py --action resolve --agent <slug> [与派发相同的 inline 拓扑/覆盖输入；external 派发至少含 --mode external] --workspace-root <project-dir> --format json`（远端经既有 `ssh` 族在目标项目侧执行） | exit 0 且 `config_id` 非空 = ok；external 派发还要求 `requires_external=true`。失败 = **uncertain → 列待补清单**（按引擎消息补齐字段：model / effort / context 等；默认层缺失指向 `specify init`） |
| ⑤ | spec-kit 框架可用性（目标项目侧） | `ssh <alias> "su - <run-user> -c 'cd <project-dir> && test -d .specify && test -f .specify/memory/constitution.md && cat .specify/source.json 2>/dev/null'"` | 在位 = ok；缺失/退化 = **fail → handoff sdd-project-setup**（见下） |

## 失败处置链（软协同）

- **①②③ fail**：停线并按上送件四要素报告（发现了什么 / 为何吃重 / 已产生的中间产物逐项可定位 / 可选处置）——网络/凭证/别名（①）、用户配置（②）、CLI 安装（③）。
- **④ uncertain**：列出**待用户补充的信息清单**——按 `execution-config.py` 的解析错误逐字段补齐（model / effort / context 的生效值、external 的 `cli`、默认层缺失时运行 `specify init`）；绑定后的配置必须重新 `resolve` 并取得非空 `config_id`，不得绕过解析器手工拼参数。
- **⑤ fail（`.specify/` 缺失或宪法不在位）**：**handoff 给 sdd-project-setup 技能**做 bootstrap——缺失 = install 模式、退化 = refresh 模式（模式由探测定）；本技能不执行框架初始化。setup 返回：
  - `ready`（bootstrap + 首次维护 H4 已完成）→ 回调用方循环，重跑本前置检查；
  - `bootstrap-complete / maintenance-pending` → 再 handoff 给 **sdd-house-keeping H1–H4** 做首次维护，取得 `ready` 后重入；house-keeping 不可用时，只有本前置检查 ⑤ 通过才可继续，并在凭证记 `maintenance=not_evaluated`，不得冒充 ready。
- 与 setup / house-keeping 的完整边界见 setup `references/setup-recipes.md`「软协同契约」与 house-keeping `references/maintenance-recipes.md`；本表是 preflight 的唯一权威落点——三技能侧仅存引用。

## 参数占位约定

`<alias>`（登录别名或 IP）/ `<run-user>`（运行身份，uid≠0）/ `<project-dir>`（目标项目目录）/ `<cli>`（子代理 CLI：qodercli/claude）——与 `.specify/shared/workflow/external-dispatch-recipes.md` 的占位约定一致。
