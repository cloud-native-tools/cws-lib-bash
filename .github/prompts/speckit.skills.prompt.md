> Note
>
> - Argument Format: `<name> - <description>` (e.g., `testing - Unit testing utils`)
> - Or use flags: `--name <name> --description <desc>`

## User Input

```text
$ARGUMENTS
```

## Outline

目标：在当前对话上下文中，帮助用户创建或整理高质量 SpecKit Skill，确保结构规范、触发清晰、资源可复用，并为每个技能生成可复用的确定性 `skill_id`。

主流程：
1. 优先从现有对话提炼可复用工作流
2. 仅在必要时做最小澄清（一次一个问题）
3. 迭代完善 `SKILL.md` 与配套资源，直到可直接使用

## Skill Specification

### 1) Skill 基础结构

每个 Skill 至少包含 `SKILL.md`，可选携带资源目录：

```
<skill-name>/
├── SKILL.md            # 必需
├── tools/              # 工具说明（可选）
├── .specify/scripts/            # 可执行脚本（可选）
├── references/         # 按需加载的参考资料（可选）
└── assets/             # 输出使用的静态资源（可选）
```

### 2) Skill 存放位置（官方兼容）

支持以下目录（项目级或个人级）：

- `.github/skills/<name>/`
- `.agents/skills/<name>/`
- `.claude/skills/<name>/`
- `~/.copilot/skills/<name>/`
- `~/.agents/skills/<name>/`
- `~/.claude/skills/<name>/`

### 3) `SKILL.md` 规范

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

### 4) 资源目录使用准则

#### `tools/`

项目工具清单来自 `tools/`（由 `refresh-tools.sh` 生成 JSON）：

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

### 5) 上下文加载与体量控制

采用渐进加载：

1. 发现阶段：读取 `name` + `description`
2. 命中后：读取 `SKILL.md` 正文
3. 需要时：再读取 `.specify/scripts/`、`references/`、`assets/`

约束：

- `SKILL.md` 建议 < 500 行
- 引用链尽量一层（从 `SKILL.md` 直达资源）
- 资源路径统一使用相对路径（建议 `./`）

### 6) 不要放入 Skill 的内容

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

1. **Initialize / Refresh**
   - 执行 `.specify/scripts/bash/create-new-skill.sh --json $ARGUMENTS` 创建或刷新结构，并解析 JSON 输出。
   - 若输出含 `"status": "refreshed"`：展示脚本消息并停止。
   - 若输出含 `"SKILL_DIR"`：解析 `SKILL_DIR`、`SKILL_NAME`、`SKILL_DESCRIPTION`、`SKILL_ID`，确认创建成功。
   - `SKILL_ID` 必须是 `.github/skills/<skill-name>/SKILL.md` 的工作区相对路径。

2. **ID-first reuse**
   - 如果输入中提供 `skill_id`，先按 ID 精确定位 skill。
   - 仅在 `skill_id` 缺失或失效时回退到自然语言发现。
   - 当 `skill_id` 与文本提示冲突时，必须显式报错并停止自动继续。

3. **Extract from Conversation (Default)**
   - 先复用当前对话，提炼流程、分支与验收标准。

4. **Clarify if Needed (Fallback)**
   - 仅在提炼不足时触发。
   - 约束：每轮只问 1 个问题，等待用户答复后继续。

5. **Draft & Refine**
   - 持续更新 `SKILL.md`，围绕薄弱点小步修订，直到可执行。

6. **Tailored Implementation**
   - 更新 frontmatter `{{DESCRIPTION}}` 与正文关键章节（如 `## Overview`、`## Workflow / Instructions`、`## Constraints`）。
   - 若模板中 `## Applicable Scenarios` / `## 适用场景` 与 frontmatter 重复且无增量价值，可删除。
   - 按需脚手架资源：
     - 自动化逻辑/API 调用 → `.specify/scripts/`
     - 文档/Schema/策略 → `references/`
     - 模板/样板工程 → `assets/`
     - 工具说明 → `tools/`
   - 更新 `SKILL.md` 的资源链接，并询问用户是否导入已有文件。

7. **Register `skill_id` in instructions template**
   - 创建或更新 skill 后，必须在 `.ai/instructions.md` 的 `## Resource Registry` → `### Skills` 小节中追加一个结构化列表条目，字段名称参考 `.specify/templates/skills-template.md`。
   - 条目中必须包含 `Skill Name`、`Skill ID`、`Description`、`Canonical Path`；若模板中存在对应 frontmatter，也应按相同字段名补充。
   - 条目使用 `skill_id` 的规范值；若同一 ID 已存在则不得重复写入。
   - 保持 Skills 列表排序、去重；一旦存在真实条目，移除 `- None yet.`。

8. **Completion**
   - 总结 Skill 能力与目录结构。
   - 给出示例提示词。
   - 给出下一步可选定制项。
   - 输出 `SKILL.md` 路径与 `skill_id`。

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