---
name: study-code
description: 对任意 git 仓库做"减法式"源码研读——先浅拷贝并剥离工程配置、脚手架与测试用例（删除清单保留为技术栈证据），再产出代码清单与文档清单，然后深入核心概念、基本架构、组件构成与核心实现，最后生成一份**可索引**的报告（索引表 + 稳定锚点 + 证据路径），供后续追问时快速反查。Use when the user mentions "study this repo", "study-code", "深读源码", "源码研读", "strip repo", "代码清单", "文档清单", "architecture analysis", "code analysis", "UML", "UML diagram", "component diagram", "deployment diagram", "sequence diagram", "架构分析", "组件构成", "核心实现".
skill_id: "<SKILL:.specify/skills/study-code/SKILL.md>"
classification: external
---

# study-code — 减法式源码研读

五步固定流程，逐步落盘，最终交付一份可索引报告。每一步的产物都写到 `$STUDY_DIR`（见 § Workspace），最终报告与证据归档到 `$STUDY_ARCHIVE`。

## Invocation modes

- **Direct**: 用户要求研读某仓库 → 按五步流程执行。
- **Delegated by `/speckit.research` (SDD mode)**: 研究流程的自身项目研读即本技能对当前项目的调用——先复用 `.specify/studies/<repo>-study/`（`target-commit.txt` 与 HEAD 一致且结论仍适用时），否则执行研读；证据路径回流到 `research.md` 的 Project Context Analysis 与 References。
- **Standalone research carrier**: `/speckit.research` 独立模式在子问题落在代码实现时选择本技能；报告即交付物（单载体充分时不再另写综述）。

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.

## Workspace & inputs

- **目标**：`owner/repo`、GitHub/GitLab/Gitee URL 或本地路径；缺省 = 当前工作区仓库。
- **`$WORK_DIR`**：原始仓库根（本地路径时即它本身）；**绝不修改原仓库**。
- **`$STUDY_DIR`**：研读工作区，按回退阶梯选定（逐级先探写权限；目标项目有临时目录纪律时以其受治理临时根为准）：
    1. 缺省 `$WORK_DIR/../study-code/<repo>-study/`；
    2. 不可写 → 宿主仓库的受治理临时根 `.specify/.tmp/study-code/<repo>-study/`；
    3. 仍不可写 → `~/tmp/study-code/<repo>-study/`。
  选定后在 `strip-manifest.md` 记录所选根与理由。所有剥离与清单都在这里，不碰原仓库。
- **`$STUDY_ARCHIVE`**：宿主项目中承载研读成果的持久归档目录，固定为 `<宿主项目根>/.specify/studies/<repo>-study/`。最终报告（`docs/overview.md`）、图源（`docs/figures/`）、`strip-manifest.md`、`outline-*.md`、`deep-study.md`、`self-check-evidence.txt`、`target-commit.txt` 从 `$STUDY_DIR` 归档到这里；`stripped/` 研读副本留在 `$STUDY_DIR`（一次性工作区，不归档）。目标仓库只读——任何产物都不得写进 `$WORK_DIR`。

## Step 1 — strip-repo（减法）

1. **源完整性预检**（本地目标）：克隆前在 `$WORK_DIR` 运行 `git fsck --no-dangling`，确认 `refs` 与 index 可读。失败时不修原仓库——校验对象库一致后用 `cp -a "$WORK_DIR/." "$STUDY_DIR/stripped/"` 物化工作树，并把目标提交哈希（`git rev-parse HEAD`；读不到则记不可得）写入 `$STUDY_DIR/target-commit.txt`；此后溯源以该哈希为准，不以拷贝内 `.git` 为准。
2. 浅拷贝：远端用 `git clone --depth 1 <url> "$STUDY_DIR/stripped"`；本地用 `git clone --depth 1 "file://$WORK_DIR" "$STUDY_DIR/stripped"`（保留一份 `.git` 供追溯）。
3. 在拷贝内删除三类干扰项（**只删拷贝，不删原件**）：
   - **工程类配置**：`package.json` 及 lockfile、`pyproject.toml`/`setup.*`、`tsconfig*.json`、`*.config.{js,ts,mjs,cjs}`、`Makefile`、`Dockerfile`、`docker-compose*`、CI 目录（`.github/`、`.gitlab-ci.yml` 等）、`.gitignore`/`.editorconfig`。
   - **脚手架/生成物**：`dist/`、`build/`、`out/`、`generated/`、`vendor/`（纯第三方 vendor）、`node_modules/`、`__pycache__/`。
   - **测试用例**：`tests/`、`test/`、`spec/`、`__tests__/`、`*.spec.*`、`*_test.*`、`test_*.py`、`fixtures/`。
4. 产出 `$STUDY_DIR/strip-manifest.md`：按类别的删除文件数，**并为每个被删的配置文件写一行用途**（如 `package.json — 声明运行时依赖与脚本入口`）。这份清单是 Step 4 技术栈判断的证据来源——删除的是噪音，不是事实。
5. 报告删除总量与保留文件数；若某删除命中"疑似核心目录"（如名为 `build/` 但内容是源码），保留并记录例外。

## Step 2 — outline-code（代码清单）

- 对 `stripped/` 产出**简单**清单：目录树（两三层）、语言与文件数、每文件的 LOC、入口点候选（main/index/cli/server/app 等）、模块边界初判。
- 写入 `$STUDY_DIR/outline-code.md`（表格 + 一段话总述）。不做深度评价——那是 Step 4。

## Step 3 — outline-docs（文档清单）

- 清点 `README*`、`docs/`、`doc/`、`ADR/RFC`、`CONTRIBUTING`、设计笔记；每个条目一行主题摘要 + 可信度标记（官方/历史/过期）。
- 写入 `$STUDY_DIR/outline-docs.md`。标注与代码可能冲突的文档（供 Step 4 交叉验证）。

## Step 4 — deep-study（核心研读）

四个必答维度，顺序固定：**核心概念 → 基本架构 → 组件构成 → 核心实现**。

- **核心概念**：项目用自己的词汇解决什么问题；术语表（概念 → 一句话定义 → 代码落点）。
- **基本架构**：系统边界、分层/分区、依赖方向、运行拓扑；主视图用 draw-diagram 渲染标准 UML（组件/部署/时序），次视图可用 Mermaid。
- **组件构成**：核心 vs 次要组件（按业务功能划分），每个组件的职责、对外接口、依赖与被依赖。
- **核心实现**：关键路径的机制拆解（为什么这样设计、替代方案的代价），以 `文件:行` 为证据。

方法论与深度标准见 references：`architect-analysis-guide` / `tech-stack-analysis-guide`（读 Step 1 的删除清单）/ `module-analysis-guide` / `git-analysis-guide` / `deployment-analysis-guide` / `uml-visualization-guide`。核心原则保留：**Why > What**、设计级叙述而非贴代码、结论必须有 `路径[:行]` 证据、每个局部结论要连回整体设计。draw-diagram 渲染后端不可达时按 `uml-visualization-guide` 的降级分支处理（Mermaid 草图 + 保留 `.puml` + 可见降级注记），该步不因渲染失败而失败。

产出 `$STUDY_DIR/deep-study.md`（四节 + 证据指针）。规模大时可按组件并行子代理，但主代理不得重复读子代理的领地，且必须等全部返回后统一校验。

## Step 5 — report（可索引报告）

写 `$STUDY_ARCHIVE/docs/overview.md`，**必须可索引**，供用户后续追问时快速反查：

1. **索引表（必备，置于报告开头）**：`概念/组件 → 章节锚点（相对链接） → 证据路径（file:line）`，一行一条，覆盖全部核心概念与组件。
2. **稳定锚点**：每个章节与组件小节使用固定、可预测的标题（锚点由标题派生），不得中途改名；跨引用使用相对锚点链接。
3. **查表指南（Lookup guide）**：给常见追问形态配"去哪找"（如"某行为在哪实现" → 核心实现节 + 证据路径；"依赖谁" → 组件构成节）。
4. **证据密度**：每个结论携带 `路径[:行]`；没有证据的推断标注 `推断`。
5. 图表：主视图的 UML 图文件放 `$STUDY_ARCHIVE/docs/figures/`（PNG + `.puml` 源），图中要点回链索引表。
6. 交付前自检：索引表的每个锚点可跳转、每个证据路径存在、章节标题与索引一致。

默认中文（跟随用户语言）；直接写结论，不要"见上文/见草稿"式导航。

## Output Requirements

- **UML 主视图**：架构结构、关键行为流、部署拓扑等主视图用标准 UML（经 draw-diagram 渲染；PNG + `.puml` 源放 `$STUDY_ARCHIVE/docs/figures/`，报告内以相对路径 + 简短图注嵌入）；**Mermaid 仅限次要内容**（速览草图、小流程、小组件）。
- **证据密度**：每个结论带 `路径[:行]`；没有证据的推断显式标注 `推断`。
- 默认中文（跟随用户语言）；交付前完成 Step 5 自检（索引锚点可跳转、证据路径存在、标题与索引一致）。

## Report Output Location

`$STUDY_ARCHIVE/docs/overview.md`（`<宿主项目根>/.specify/studies/<repo>-study/docs/overview.md`）— the single deliverable file the user consumes. 归档同目录另含 `strip-manifest.md`、`outline-code.md`、`outline-docs.md`、`deep-study.md`、`self-check-evidence.txt`、`target-commit.txt` 与 `figures/`；`stripped/` 不归档。

## References

| 文档 | 内容 |
|------|------|
| [architect-analysis-guide.md](references/architect-analysis-guide.md) | 宏观架构框架、业务优先分析法、叙述标准 |
| [tech-stack-analysis-guide.md](references/tech-stack-analysis-guide.md) | 语言/框架/构建/生态适配分析（配置证据读 Step 1 清单） |
| [module-analysis-guide.md](references/module-analysis-guide.md) | 模块分析法、完备度标准、子代理提示模板 |
| [git-analysis-guide.md](references/git-analysis-guide.md) | 提交/标签/分支历史与架构演进信号 |
| [deployment-analysis-guide.md](references/deployment-analysis-guide.md) | 运行拓扑、打包、交付管道与可运维性 |
| [uml-visualization-guide.md](references/uml-visualization-guide.md) | 视图→UML 图型映射、图件约定、渲染委派与降级规则 |

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:study-code" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:study-code" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:study-code" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
