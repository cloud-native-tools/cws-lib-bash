> Note: `$ARGUMENTS` 为**可选补充输入**，可能包含以下类型的内容：
> - **背景信息**：提供上下文、约束条件或业务背景
> - **任务大纲**：用户提供的高层次任务分解或结构
> - **额外任务条目**：具体的任务项，需要整合到生成的任务列表中
> 
> 当本次调用未提供任何 `$ARGUMENTS` 时，仍须按下文流程基于当前 feature 的 `requirements.md`、`plan.md` 等设计文档自动生成完整、可执行的 `tasks.md`。

## User Input Analysis & Processing

```text
$ARGUMENTS
```

### Input Type Detection and Handling Strategy

1. **背景信息类型**：如果 `$ARGUMENTS` 主要包含描述性文本、业务上下文、约束条件或非结构化信息
   - 将这些信息作为上下文整合到任务生成过程中
   - 在相关任务描述中引用或体现这些约束条件
   - 不直接转换为具体任务条目

2. **任务大纲类型**：如果 `$ARGUMENTS` 包含结构化的任务分解、阶段划分或高层次任务组织
   - 将大纲结构作为任务组织的主要框架
   - 基于大纲填充具体的实现细节和文件路径
   - 确保生成的任务遵循指定的结构和顺序

3. **额外任务条目类型**：如果 `$ARGUMENTS` 包含具体的、可执行的任务项（通常以列表形式）
   - 解析并标准化这些任务条目，确保符合任务格式规范
   - 将其整合到相应的用户故事阶段或基础任务中
   - 维护任务ID的连续性和依赖关系的正确性

You **MUST** first analyze the content and structure of `$ARGUMENTS` to determine its type, then apply the appropriate handling strategy. Do NOT treat the input as a standalone instruction that replaces the command logic.

## Outline

1. **Setup**: Run `.specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse REQUIREMENTS_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Load design documents**: Read from REQUIREMENTS_DIR:
   - **Required**: plan.md (tech stack, libraries, structure), requirements.md (user stories with priorities)
   - **Optional**: data-model.md (entities), contracts/ (API endpoints), research.md (decisions), quickstart.md (test scenarios)
   - Note: Not all projects have all documents. Generate tasks based on what's available.

3. **Generate task list workflow**:
   - **Analyze $ARGUMENTS input type**: Determine if input contains background context, task outline, or additional task items
   - Load plan.md and extract tech stack, libraries, project structure
   - Load requirements.md and extract user stories with their priorities (P1, P2, P3, etc.)
   - If data-model.md exists: Extract entities and map to user stories
   - If contracts/ exists: Map endpoints to user stories
   - If research.md exists: Extract decisions for setup tasks
   - **Integrate $ARGUMENTS content**: 
     - For background info: Apply as contextual constraints in task generation
     - For task outlines: Use as primary organizational structure
     - For additional tasks: Parse, standardize, and merge into appropriate phases
   - Generate tasks organized by user story (see Task Generation Rules below)
   - Generate dependency graph showing user story completion order
   - Create parallel execution examples per user story
   - Validate task completeness (each user story has all needed tasks, independently testable)

4. **Generate tasks.md**: Use `.specify/templates/tasks-template.md` as structure, fill with:
   - Correct feature name from plan.md
   - Phase 1: Setup tasks (project initialization)
   - Phase 2: Foundational tasks (blocking prerequisites for all user stories)
   - Phase 3+: One phase per user story (in priority order from requirements.md)
   - Each phase includes: story goal, independent test criteria, tests (if requested), implementation tasks
   - Final Phase: Polish & cross-cutting concerns
   - All tasks must follow the strict checklist format (see Task Generation Rules below)
   - Clear file paths for each task
   - Dependencies section showing story completion order
   - Parallel execution examples per story
   - Implementation strategy section (MVP first, incremental delivery)

5. **Report**: Output path to generated tasks.md and summary:
   - Total task count
   - Task count per user story
   - Parallel opportunities identified
   - Independent test criteria for each story
   - Suggested MVP scope (typically just User Story 1)
   - Format validation: Confirm ALL tasks follow the checklist format (checkbox, ID, labels, file paths)

Context for task generation: 
- Design documents from REQUIREMENTS_DIR: {AVAILABLE_DOCS}
- User input analysis result: {ARGUMENTS_ANALYSIS_RESULT}
- Input type handling strategy: {INPUT_HANDLING_STRATEGY}

The tasks.md should be immediately executable - each task must be specific enough that an LLM can complete it without additional context. When $ARGUMENTS contains additional task items, ensure they are properly integrated with correct formatting, sequential IDs, and appropriate story labels.

## Feature Integration

The `/speckit.tasks` command automatically integrates with the feature tracking system:

- If a `.specify/memory/features.md` file exists, the command will:
  - Detect the current feature directory (format: `.specify/specs/###-feature-name/`)
  - Extract the feature ID from the directory name
  - Update the corresponding feature entry in `.specify/memory/features.md`:
    - Ensure status is "Implemented" (maintains status from planning phase)
    - Keep the specification path unchanged
    - Update the "Last Updated" date
  - Automatically stage the changes to `.specify/memory/features.md` for git commit

In addition, **tasks 阶段必须复核 Feature 列表**：

- 任务拆分可能暴露新的 Feature 或提示旧 Feature 不再适用。
- 确保功能性/非功能性 Feature 分类保持一致。
- 若发现 Feature 变更，必须同步更新：
   - `.specify/memory/features/<ID>.md`
   - `.specify/memory/features.md`
- 在 Feature 详情中记录任务拆分带来的“关键变化/备注”。

This integration ensures that all feature task generation activities are properly tracked and linked to their corresponding entries in the project's feature index.

## Task Generation Rules

**CRITICAL**: Tasks MUST be organized by user story to enable independent implementation and testing.

**Tests are OPTIONAL**: Only generate test tasks if explicitly requested in the feature specification or if user requests TDD approach.

### Checklist Format (REQUIRED)

Every task MUST strictly follow this format:

```text
- [ ] [TaskID] [P?] [Story?] Description with file path
```

**Format Components**:

1. **Checkbox**: ALWAYS start with `- [ ]` (markdown checkbox)
2. **Task ID**: Sequential number (T001, T002, T003...) in execution order
3. **[P] marker**: Include ONLY if task is parallelizable (different files, no dependencies on incomplete tasks)
4. **[Story] label**: REQUIRED for user story phase tasks only
   - Format: [US1], [US2], [US3], etc. (maps to user stories from requirements.md)
   - Setup phase: NO story label
   - Foundational phase: NO story label  
   - User Story phases: MUST have story label
   - Polish phase: NO story label
5. **Description**: Clear action with exact file path

**Examples**:

- ✅ CORRECT: `- [ ] T001 Create project structure per implementation plan`
- ✅ CORRECT: `- [ ] T005 [P] Implement authentication middleware in src/middleware/auth.py`
- ✅ CORRECT: `- [ ] T012 [P] [US1] Create User model in src/models/user.py`
- ✅ CORRECT: `- [ ] T014 [US1] Implement UserService in src/services/user_service.py`
- ❌ WRONG: `- [ ] Create User model` (missing ID and Story label)
- ❌ WRONG: `T001 [US1] Create model` (missing checkbox)
- ❌ WRONG: `- [ ] [US1] Create User model` (missing Task ID)
- ❌ WRONG: `- [ ] T001 [US1] Create model` (missing file path)

### Task Organization

1. **From User Stories (requirements.md)** - PRIMARY ORGANIZATION:
   - Each user story (P1, P2, P3...) gets its own phase
   - Map all related components to their story:
     - Models needed for that story
     - Services needed for that story
     - Endpoints/UI needed for that story
     - If tests requested: Tests specific to that story
   - Mark story dependencies (most stories should be independent)

2. **From Contracts**:
   - Map each contract/endpoint → to the user story it serves
   - If tests requested: Each contract → contract test task [P] before implementation in that story's phase

3. **From Data Model**:
   - Map each entity to the user story(ies) that need it
   - If entity serves multiple stories: Put in earliest story or Setup phase
   - Relationships → service layer tasks in appropriate story phase

4. **From Setup/Infrastructure**:
   - Shared infrastructure → Setup phase (Phase 1)
   - Foundational/blocking tasks → Foundational phase (Phase 2)
   - Story-specific setup → within that story's phase

### Phase Structure

- **Phase 1**: Setup (project initialization)
- **Phase 2**: Foundational (blocking prerequisites - MUST complete before user stories)
- **Phase 3+**: User Stories in priority order (P1, P2, P3...)
  - Within each story: Tests (if requested) → Models → Services → Endpoints → Integration
  - Each phase should be a complete, independently testable increment
- **Final Phase**: Polish & Cross-Cutting Concerns

## Handoffs

**Before running this command**:

- Run `/speckit.plan` to produce a plan and design artifacts.

**After running this command**:

- Optionally run `/speckit.analyze` to check cross-artifact consistency before implementation.
- Optionally run `/speckit.checklist` to create quality gates.
- Then run `/speckit.implement` to execute the tasks phase-by-phase.