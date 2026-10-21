<!-- AUTO-GENERATED from templates/commands/feature.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Interpret scope: empty → full-registry reconcile; concrete context (commit/PR/branch) → context mining; description → locate-and-converge.

## Outline

本命令维护项目特性注册表,一次调用 = 委派 **`manage-features`** 技能执行全部注册表工作。

**Delegation (mandatory)**: load `.specify/skills/internal/manage-features/SKILL.md` and execute per its Reconcile Model and Workflow (Actions 0–9)。注册表是持久制品空间,按 reconcile 模型收敛(`.specify/shared/patterns/reconcile-pattern.md`);容差带、archive-not-delete、never-regress-status(及其 gate probe)、格式要求与边界均以该技能为单一事实源,本模板不复述。

### 技能输入(本命令解析 `$ARGUMENTS` 后传入)

- Scope(同 User Input 三分):无参 → 全注册表 reconcile;commit/PR/branch 上下文 → fan-out mining;特性描述 → 单目标收敛。
- 可读的 repo context(README / docs / build config)——期望状态由此计算,无上下文则无法 diff。

### 技能产出

- `.specify/memory/features/<ID>.md` 详情文件(从 `.specify/templates/feature-details-template.md` 实例化)与 `.specify/memory/features.md` 索引表(`FEATURE_COUNT` 自动派生)。
- README "Feature List" 段同步(Functional / Non-functional)。
- 残差报告:收敛行 / 容差行 / 新增行 / 需用户决策项;无变更时如实说明。

## Handoffs

**Before**: `/speckit.constitution` if governance rules change. Ensure repo context (README/docs) available.

**After**: Proceed to `/speckit.requirements` for a chosen feature.