# Feedback Probe Definitions(反馈插点真源)

> **Single source of truth** for Feedback Probe(反馈插点)definitions — canonical at
> `shared/definitions/probe-definitions.md`, mirrored to `.specify/shared/definitions/`.
> Two-layer model:
> **Probe Class**(插点类,特征定义)× **Probe Object**(插点实例,系统落点);
> each Class carries an **internal/external** kind. Derived views (probe-map, command
> mode-1 overview) MUST be rebuilt from this file — never hand-copied.
> Invariants: five class features non-empty; ids unique; every Object belongs to exactly
> one Class; internal units match `/speckit.*` or `skill:*`; external ids carry the `ext-`
> prefix and `custom:` units. Validate with `--action probes --validate`.

## Slices

- commands — 框架命令模板域
- skills — 框架技能域
- scripts / templates / docs — 预留切片维度(暂无活动 probe)
- host-custom — 宿主项目自定义单元域(仅外部 probe)

## Classes

| class_id | kind | collection | target_slice | processing | insertion_type |
|----------|------|------------|--------------|------------|----------------|
| command-wrapup | internal | 命令单次运行的回顾与 ≥1 条单元级优化点 | commands | record→threshold→package→manual→mark-submitted | wrap-up |
| skill-wrapup | internal | 技能单次运行的回顾与 ≥1 条单元级优化点 | skills | record→threshold→package→manual→mark-submitted | wrap-up |
| external-custom | external | 宿主项目自定义单元运行的回顾与优化点 | host-custom | record→local-consumption(不上送) | wrap-up |
| command-gate | internal | 保留确认点触发后的用户决定观察事实(门控必要性证据) | commands | record→threshold→package→manual→mark-submitted | confirm-gate |
| skill-gate | internal | 保留确认点触发后的用户决定观察事实(门控必要性证据) | skills | record→threshold→package→manual→mark-submitted | confirm-gate |
| skill-evaluation-form | internal | 绘图技能交付产物后由用户主动给出的 Evaluation Form(绘制评价单),用于评价该次已交付结果 | skills | record→threshold→package→manual→mark-submitted | evaluation-form |

## Objects

> SC-001 对账基准(历史快照,仅作当时留痕,不代表当前数量):彼时的隐式埋点
> 与嵌入点清单一一对应,`/speckit.feedback` 命令自身的 Object 随命令模板落地
> 同变更登记(见 contracts/probe-registry.md C-3.4)。当前生效的埋点集合以本
> 注册表为准,用 `feedback-utils.py --action probes --validate` 读取与对账,
> MUST NOT 在他处复写计数。
>
> 51–70 行为 044 Phase 7 的门控必要性 probe(insertion_type=confirm-gate):
> 每个非 intrinsic 保留确认点一个 Object,锚点是点位的单行 probe 指针
> (非 `## Feedback` 嵌入),故不参与 wrap-up embed 对账;unit 为确定性归属单元,
> 实际触发单元记在条目正文 `fired_during` 字段。行序即解析优先级:wrap-up 行
> 在前,保证无 lifecycle_point 的 record 调用行为不变。

| object_id | class_id | unit | lifecycle_point |
|-----------|----------|------|-----------------|
| speckit-analyze-wrapup | command-wrapup | /speckit.analyze | wrap-up |
| speckit-checklist-wrapup | command-wrapup | /speckit.checklist | wrap-up |
| speckit-clarify-wrapup | command-wrapup | /speckit.clarify | wrap-up |
| speckit-derive-wrapup | command-wrapup | /speckit.derive | wrap-up |
| speckit-docs-wrapup | command-wrapup | /speckit.docs | wrap-up |
| speckit-goal-wrapup | command-wrapup | /speckit.goal | wrap-up |
| speckit-history-wrapup | command-wrapup | /speckit.history | wrap-up |
| speckit-implement-wrapup | command-wrapup | /speckit.implement | wrap-up |
| speckit-instructions-wrapup | command-wrapup | /speckit.instructions | wrap-up |
| speckit-interview-wrapup | command-wrapup | /speckit.interview | wrap-up |
| speckit-plan-wrapup | command-wrapup | /speckit.plan | wrap-up |
| speckit-requirements-wrapup | command-wrapup | /speckit.requirements | wrap-up |
| speckit-research-wrapup | command-wrapup | /speckit.research | wrap-up |
| speckit-review-wrapup | command-wrapup | /speckit.review | wrap-up |
| speckit-sanitize-wrapup | command-wrapup | /speckit.sanitize | wrap-up |
| speckit-session-wrapup | command-wrapup | /speckit.session | wrap-up |
| speckit-skills-wrapup | command-wrapup | /speckit.skills | wrap-up |
| speckit-tasks-wrapup | command-wrapup | /speckit.tasks | wrap-up |
| speckit-todo-wrapup | command-wrapup | /speckit.todo | wrap-up |
| speckit-tools-wrapup | command-wrapup | /speckit.tools | wrap-up |
| skill-archive-session-wrapup | skill-wrapup | skill:archive-session | wrap-up |
| skill-browser-extension-wrapup | skill-wrapup | skill:browser-extension | wrap-up |
| skill-browser-utils-wrapup | skill-wrapup | skill:browser-utils | wrap-up |
| skill-clone-website-ui-wrapup | skill-wrapup | skill:clone-website-ui | wrap-up |
| skill-code-review-wrapup | skill-wrapup | skill:code-review | wrap-up |
| skill-collect-evidence-wrapup | skill-wrapup | skill:collect-evidence | wrap-up |
| skill-create-agent-wrapup | skill-wrapup | skill:create-agent | wrap-up |
| skill-create-docs-wrapup | skill-wrapup | skill:create-docs | wrap-up |
| skill-create-pages-wrapup | skill-wrapup | skill:create-pages | wrap-up |
| skill-create-skills-wrapup | skill-wrapup | skill:create-skills | wrap-up |
| skill-create-team-wrapup | skill-wrapup | skill:create-team | wrap-up |
| skill-create-tools-wrapup | skill-wrapup | skill:create-tools | wrap-up |
| skill-database-utils-wrapup | skill-wrapup | skill:database-utils | wrap-up |
| skill-document-utils-wrapup | skill-wrapup | skill:document-utils | wrap-up |
| skill-draw-d3js-wrapup | skill-wrapup | skill:draw-d3js | wrap-up |
| skill-draw-diagram-wrapup | skill-wrapup | skill:draw-diagram | wrap-up |
| skill-draw-drawio-wrapup | skill-wrapup | skill:draw-drawio | wrap-up |
| skill-draw-echarts-wrapup | skill-wrapup | skill:draw-echarts | wrap-up |
| skill-draw-excalidraw-wrapup | skill-wrapup | skill:draw-excalidraw | wrap-up |
| skill-draw-mermaid-wrapup | skill-wrapup | skill:draw-mermaid | wrap-up |
| skill-draw-plantuml-wrapup | skill-wrapup | skill:draw-plantuml | wrap-up |
| skill-git-submodule-edit-wrapup | skill-wrapup | skill:git-submodule-edit | wrap-up |
| skill-git-workflow-wrapup | skill-wrapup | skill:git-workflow | wrap-up |
| skill-improve-agent-wrapup | skill-wrapup | skill:improve-agent | wrap-up |
| skill-improve-docs-wrapup | skill-wrapup | skill:improve-docs | wrap-up |
| skill-improve-skills-wrapup | skill-wrapup | skill:improve-skills | wrap-up |
| skill-improve-team-wrapup | skill-wrapup | skill:improve-team | wrap-up |
| skill-improve-tools-wrapup | skill-wrapup | skill:improve-tools | wrap-up |
| skill-manage-agents-wrapup | skill-wrapup | skill:manage-agents | wrap-up |
| skill-memory-recall-wrapup | skill-wrapup | skill:memory-recall | wrap-up |
| skill-memory-record-wrapup | skill-wrapup | skill:memory-record | wrap-up |
| skill-study-project-wrapup | skill-wrapup | skill:study-project | wrap-up |
| skill-summarize-project-wrapup | skill-wrapup | skill:summarize-project | wrap-up |
| skill-think-skills-wrapup | skill-wrapup | skill:think-skills | wrap-up |
| speckit-feedback-wrapup | command-wrapup | /speckit.feedback | wrap-up |
| gate-feature-status-regression | command-gate | /speckit.feature | gate-feature-status-regression |
| gate-implement-checklist-waiver | command-gate | /speckit.implement | gate-implement-checklist-waiver |
| gate-sanitize-destructive-cleanup | command-gate | /speckit.sanitize | gate-sanitize-destructive-cleanup |
| gate-session-export-overwrite | command-gate | /speckit.session | gate-session-export-overwrite |
| gate-tools-invoke-entry | command-gate | /speckit.tools | gate-tools-invoke-entry |
| gate-tools-invoke-mode | command-gate | /speckit.tools | gate-tools-invoke-mode |
| gate-tools-invoke-rule | command-gate | /speckit.tools | gate-tools-invoke-rule |
| gate-tools-invoke-prompt | command-gate | /speckit.tools | gate-tools-invoke-prompt |
| gate-rubric-high-stakes | command-gate | /speckit.instructions | gate-rubric-high-stakes |
| gate-glossary-user-entry-overwrite | command-gate | /speckit.instructions | gate-glossary-user-entry-overwrite |
| gate-create-docs-tiered-disposition | skill-gate | skill:create-docs | gate-create-docs-tiered-disposition |
| gate-create-docs-write-plan | skill-gate | skill:create-docs | gate-create-docs-write-plan |
| gate-create-team-presence-loop | skill-gate | skill:create-team | gate-create-team-presence-loop |
| gate-create-team-noninteractive-call | skill-gate | skill:create-team | gate-create-team-noninteractive-call |
| gate-create-tools-no-execute | skill-gate | skill:create-tools | gate-create-tools-no-execute |
| gate-git-workflow-tiered-mode | skill-gate | skill:git-workflow | gate-git-workflow-tiered-mode |
| gate-git-workflow-remote-ops | skill-gate | skill:git-workflow | gate-git-workflow-remote-ops |
| gate-improve-tools-no-test-invoke | skill-gate | skill:improve-tools | gate-improve-tools-no-test-invoke |
| gate-summarize-project-four-gates | skill-gate | skill:summarize-project | gate-summarize-project-four-gates |
| gate-summarize-project-structure-freeze | skill-gate | skill:summarize-project | gate-summarize-project-structure-freeze |
| gate-summarize-project-degraded-gates | skill-gate | skill:summarize-project | gate-summarize-project-degraded-gates |
| skill-draw-diagram-evaluation-form | skill-evaluation-form | skill:draw-diagram | evaluation-form |
| skill-draw-d3js-evaluation-form | skill-evaluation-form | skill:draw-d3js | evaluation-form |
| skill-draw-drawio-evaluation-form | skill-evaluation-form | skill:draw-drawio | evaluation-form |
| skill-draw-echarts-evaluation-form | skill-evaluation-form | skill:draw-echarts | evaluation-form |
| skill-draw-excalidraw-evaluation-form | skill-evaluation-form | skill:draw-excalidraw | evaluation-form |
| skill-draw-mermaid-evaluation-form | skill-evaluation-form | skill:draw-mermaid | evaluation-form |
| skill-draw-plantuml-evaluation-form | skill-evaluation-form | skill:draw-plantuml | evaluation-form |

## External Probe 登记契约

宿主项目的外部 probe 不写入本文件,登记于项目侧
`.specify/memory/feedback/probes/<object_id>.md`(YAML frontmatter,一文件一 probe):

```yaml
object_id: ext-<slug>        # MUST 以 ext- 开头(内外命名空间强制隔离)
class_id: external-custom    # MUST 引用 kind=external 的 Class
unit: custom:<owner>/<name>  # MUST 匹配 ^custom:[a-z0-9._/-]+$
lifecycle_point: wrap-up
```

- 注入路径:`/speckit.feedback` § Probe Injection(引擎 `--action probe-inject`)。
- 外部条目(`kind: external`)保留在宿主项目本地,**永不进入**框架上送打包路径
  (engine `--action package` 100% 排除,见 contracts/engine-cli.md C-4)。
- 校验:`--action probes --validate` 覆盖本文件 Classes/Objects 与外部 probe 文件。
