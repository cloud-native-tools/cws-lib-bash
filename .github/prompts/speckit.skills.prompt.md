> Note
>
> - Argument Format: `<name> - <description>` (e.g., `testing - Unit testing utils`)
> - Or use flags: `--name <name> --description <desc>`

## User Input

```text
$ARGUMENTS
```

需要根据用户的输入提取SKILL核心的两个元素：name 和 description

1. *name*: 一个简单命令的英文单词组合，不应该包含特殊字符，只包含字母、数字和'-'、'_'等编程中常用的变量名格式
2. *description*: 一段关于SKILL的功能描述和一个触发SKILL的关键词列表，例如：This skill can xxx. Use this when the user mentions [ "key word 1", "key word 3", ... ].

## Outline

目标：在当前对话上下文中，帮助用户创建或整理高质量 SpecKit Skill，确保结构规范、触发清晰、资源可复用，并为每个技能生成可复用的确定性 `skill_id`。

主流程：
1. 优先从现有对话提炼可复用工作流
2. 仅在必要时做最小澄清（一次一个问题）
3. 迭代完善 `SKILL.md` 与配套资源，直到可直接使用

## Skill Specification

### 1) SKILL_ROOT 与基础结构

**SKILL_ROOT** 是 Skill 所在的根目录。一个 Skill 的主体为 `${SKILL_ROOT}/SKILL.md`，其余资源目录均相对于 `SKILL_ROOT` 解析。

典型结构：

```
${SKILL_ROOT}/
├── SKILL.md            # 必需，Skill 主体
├── tools/              # 工具说明（相对 SKILL_ROOT，可选）
├── .specify/scripts/            # 可执行脚本（相对 SKILL_ROOT，可选）
├── references/         # 按需加载的参考资料（相对 SKILL_ROOT，可选）
└── assets/             # 输出使用的静态资源（相对 SKILL_ROOT，可选）
```

**存放位置**：`SKILL_ROOT` 可位于以下任一路径（项目级或个人级）：

- `.github/skills/<name>/`
- `.agents/skills/<name>/`
- `.claude/skills/<name>/`
- `~/.copilot/skills/<name>/`
- `~/.agents/skills/<name>/`
- `~/.claude/skills/<name>/`

后续所有资源引用统一使用相对于 `SKILL_ROOT` 的路径（推荐 `./.specify/scripts/x.py` 形式）。

### 2) `SKILL.md` 规范

#### Frontmatter

最少包含：

- `name`（必需，建议与目录名一致）
- `description`（必需，描述“做什么 + 何时触发”）

可选（按需，遵循官方行为）：

- `argument-hint`
- `user-invocable`
- `disable-model-invocation`

说明：本项目默认以 `name` 与 `description` 作为核心触发元数据；仅在确有需要时再引入可选字段。

#### Body

Body 只写执行说明，不写冗余背景。应包含：

- 结果目标
- 关键步骤（可执行、可检查）
- 资源引用（使用相对路径，如 `./.specify/scripts/x.py`）

### 3) 资源目录使用准则

#### `tools/`

Skill 根目录下的 `tools/` 用于说明本 Skill 可用的工具。项目级工具清单来自 `.specify/scripts/bash/refresh-tools.sh` 生成的 JSON：

- [MCP Tools JSON](tools/mcp.json)
- [System Tools JSON](tools/system.json)
- [Shell Tools JSON](tools/shell.json)
- [Project Scripts JSON](tools/project.json)

#### `.specify/scripts/`

用于重复率高、需要确定性的任务（Python/Bash 等）。

- 适用：重复写同类逻辑、或操作易错需稳定复现
- 价值：省 token、可执行、可复用

#### `references/`

用于按需加载的文档知识（如 schema、API、策略）。

- 适用：信息量大、但非每次都需要
- 原则：细节放 `references/`，`SKILL.md` 只保留导航和核心流程
- 大文件建议：在 `SKILL.md` 提供检索提示；参考文件超过 100 行建议加目录

#### `assets/`

用于输出物依赖但不必进入上下文的资源（模板、图片、字体、样板工程等）。

### 4) 上下文加载与体量控制

采用渐进加载：

1. 发现阶段：读取 `name` + `description`
2. 命中后：读取 `SKILL.md` 正文
3. 需要时：再读取 `.specify/scripts/`、`references/`、`assets/`

约束：

- `SKILL.md` 建议 < 500 行
- 引用链尽量一层（从 `SKILL.md` 直达资源）
- 资源路径统一使用相对路径（建议 `./`）

### 5) 不要放入 Skill 的内容

Skill 仅保留执行任务所需内容，不增加无关文档：

- `README.md`
- `INSTALLATION_GUIDE.md`
- `QUICK_REFERENCE.md`
- `CHANGELOG.md`
- 其他流程回顾/测试记录类附加文档

## Design Principles

### 1) 合理控制自由度

- 高自由度：文本策略，适合多路径问题
- 中自由度：伪代码/参数化脚本，适合有主路径但可配置
- 低自由度：固定脚本/固定步骤，适合高风险易错操作

### 2) 描述可发现

`description` 必须包含关键词与触发场景，避免模糊描述。

### 3) 反模式

- 描述空泛，无法触发
- `SKILL.md` 过大且不拆分
- 目录名与 `name` 不一致
- 缺少可执行步骤

## Planning Strategy (Official Workflow Aligned)

### Step A: 先提炼，再提问

先从当前对话提炼：

- 可复用步骤
- 决策分支
- 质量检查点

若提炼充分，直接进入草稿。

### Step B: 必要时澄清

仅当关键信息不足时提问，且**一次只问一个问题**。优先问：

- 目标产出是什么？
- 作用域是 workspace 还是 personal？
- 需要 checklist 还是完整多步骤流程？

### Step C: 迭代收敛

1. 起草并保存
2. 找出最薄弱点
3. 定向追问并修订
4. 产出可用版本（含示例提示词与后续定制建议）

## Execution Steps

创建一个 Skill 的核心流程如下：

### Step 1: 确定 SKILL_ROOT 与元数据

从用户输入（User Input）解析 `skill name` 与 `description`：

- **skill name** 用于确定 `SKILL_ROOT` 路径。例如 `name = "testing"` 且选用项目级存放位置时，`SKILL_ROOT = .github/skills/testing/`。
- **description** 用于描述"做什么 + 何时触发"，必须包含关键词与触发场景，避免模糊描述（参见 Design Principles 第 2 点）。

若输入信息不足，进入 Step 3 的提问环节补充。

### Step 2: 获取可用 Tools 信息

执行脚本获取当前项目/工作区可用的工具清单，为后续 Skill 的资源编排提供依据：

- 运行 `refresh-tools.sh`（或等价方式）刷新并输出 JSON。
- 参考工具清单分类：
  - **MCP Tools** → [mcp.json](tools/mcp.json)
  - **System Tools** → [system.json](tools/system.json)
  - **Shell Tools** → [shell.json](tools/shell.json)
  - **Project Scripts** → [project.json](tools/project.json)

可根据需要调用以下命令获取工具清单：

```bash
.specify/scripts/bash/refresh-tools.sh --json
```

获取到工具列表后，结合 Skill 目标筛选可用工具，作为 `SKILL.md` 中工具引用的参考。

### Step 3: 逐步明确 Skill 细节

通过提问方式补充 `SKILL.md` 所需信息。**每轮只问一个问题**，等待用户答复后继续。

优先问：

- **目标产出**：Skill 最终要产出什么？
- **适用场景**：在什么触发条件下应该加载此 Skill？
- **资源需求**：是否需要脚本、参考资料、模板或固定工具链？

迭代修订 `SKILL.md` 直至：

1. Frontmatter 完整（`name`、`description`）
2. Body 包含清晰可执行步骤
3. 资源目录（`tools/`、`.specify/scripts/`、`references/`、`assets/`）按需就位
4. 所有资源链接使用相对 `SKILL_ROOT` 的路径

### Step 4: 注册 Resource ID 与写入 Instructions

生成 `SKILL.md` 的 Resource ID 并持久化：

- **Canonical ID（`skill_id`）**：`.github/skills/<name>/SKILL.md` 的工作区相对路径。
- **Canonical Path**：`${SKILL_ROOT}/SKILL.md` 的工作区相对路径。

将以下信息写入 `.ai/instructions.md` 的 `## Resource Registry` → `### Skills` 小节：

- `Skill Name`
- `Skill ID`
- `Description`
- `Canonical Path`

约束：

- 条目字段名称参考 `.specify/templates/skills-template.md`。
- 同一 `skill_id` 已存在时不得重复写入。
- 列表保持排序与去重；存在真实条目后，移除 `- None yet.`。

### Completion

- 总结 Skill 能力与目录结构。
- 给出示例提示词。
- 给出下一步可选定制项。
- 输出 `SKILL.md` 路径（即 `SKILL_ROOT/SKILL.md`）与 `skill_id`。

## Slash Behavior Notes

技能在 `/` 菜单中的表现受 frontmatter 控制：

- 默认：可手动调用 + 可自动触发
- `user-invocable: false`：不可手动调用，但可自动触发
- `disable-model-invocation: true`：可手动调用，但不自动触发
- 两者同时设置：都禁用

## Continuous Improvement

1. 用真实任务验证 skill
2. 记录卡点与低效步骤
3. 回改 `SKILL.md` 或资源目录
4. 再次验证，形成稳定迭代