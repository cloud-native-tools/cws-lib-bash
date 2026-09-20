# Confirmation Gates(确认门控治理判据)

框架级确认门控的唯一判据真源。原则:**与其等待用户确认,不如先按设定执行,执行完允许用户修改;只有不可撤销、具备破坏性的动作才保留前置用户确认。** 概念基础为 `shared/patterns/reconcile-pattern.md` § Tiered confirmation(安全本地写自动、外部权威源停等、破坏性停等),本文档将其推广为全框架统一约定。

命令模板与技能 MUST 以单行引用接入本文档,MUST NOT 在模板内复制判据正文。

面向用户的措辞与上下文规则由 `.specify/shared/guidelines/user-facing-comprehension.md` 统一定义(本文件覆盖界面类 ①②⑩⑪);MUST NOT 在本文件内复制其条件集。

## 两级判据

1. **破坏性/不可撤销动作** → MUST 保留前置用户确认,确认后方可执行。
2. **可逆动作** → MUST NOT 以阻塞等待用户确认为执行前置条件;MUST 自动执行(按设定直接执行),完成后按本文档「执行报告」节呈现,用户事后修改。

动作分类由「破坏性动作清单」与「治理保留清单」确定性判定;两清单均未命中时按「存疑从严」规则处理。

## 破坏性动作清单

保守、可枚举;扩展 MUST 以修订本文档的形式进行,MUST NOT 分散到各命令模板:

- 删除文件或数据(delete / 清空存储)
- 移动/归档既有工件(move / archive / restructure)
- 远程推送(push / force-push / 远程分支操作)与写入外部权威源(issue 跟踪、平台注册表等本空间之外的系统)
- 覆盖用户既有内容(含覆盖用户既有权威条目,如 glossary 用户条目冲突写入、同名目录覆盖清空)

## 治理保留清单

以下门控凭本清单保留,不参与可逆性推断(intrinsic 与 governance-kept):

| 门控 | 所在面 | 保留理由 |
|------|--------|----------|
| 访谈退出门与访谈问答 | interview-pattern / `/speckit.interview` | 确认即产品形态(intrinsic) |
| 宪章不可撤销动作确认 | constitution-template.md | 宪章自身要求(intrinsic) |
| git commit 显式批准 | todo.md / implement.md 收尾 | 与宿主安全规范对齐(governance-kept) |
| implement gate.yaml CONFIRM 判定 | implement.md | 机械安全门禁(governance-kept) |
| git-workflow 远程操作门控 | skills/git-workflow | 远程推送属破坏性桶 |
| tools invoke 预览门控 | tools.md / tool-definitions.md | 任意脚本执行,存疑从严(governance-kept) |
| feedback consume 删除前确认 | feedback.md | 前置原子删除,破坏性桶 |
| docs 移动/归档/删除分级 | docs.md | 破坏性桶(reconcile R4/R5) |
| session 导出同名覆盖确认 | session.md | 同名覆盖清空,破坏性桶 |
| feature 状态回退确认 | feature.md | 治理状态保护(governance-kept) |
| analyze 补救批准 | analyze.md | 严格只读命令的例外写批准(governance-kept) |
| glossary 冲突/覆盖用户条目确认 | shared/workflow/glossary.md | 覆盖用户权威数据,破坏性桶 |
| continuous 循环分级门控 | create-team references(operating-loops / project-cluster) | 长时运行资源占用,既有分级门控保留 |

## 存疑从严

无法按两级判据与上述清单明确归类的动作,MUST 按破坏性处理(保留前置确认)。宁可多一次确认,MUST NOT 多一次不可撤销的损失。

## 回流约束

新增或修订命令/技能 MUST NOT 引入非破坏性阻塞确认门控。该约束由两道机械检查执行:

1. 结构契约测试(`tests/contract/test_confirmation_gates_*.py`);
2. 门控扫描脚本 `scripts/python/scan-confirmation-gates.py`——治理后复扫若检出仍以阻塞形态存在的可逆门控(`violations` 非空且提供基线时),退出码 2。

## 执行报告

每个改为自动执行的动作 MUST 在完成后呈现执行报告,三要素缺一不可:

1. **执行内容**——做了什么;
2. **产出/变更工件**——落盘或变更对象,逐项可定位;
3. **修改途径**——既有修订命令或编辑入口。

粒度与形态规则:

- **琐碎并入**:单个琐碎动作(如自动写入一条术语条目、记录一条反馈)MUST NOT 独立出完整报告,MUST 并入所属流程的收尾报告逐项列明;仅流程主要产出动作独立出完整三要素报告。
- **合并呈现**:同一流程多个自动执行动作 MUST 合并为一次收尾呈现,逐项列出,MUST NOT 逐动作打断用户。
- **失败如实报告**:自动执行中途失败 MUST 报告失败点、原因与已产生的中间产物,MUST NOT 静默跳过或掩盖。

收尾阶段达阈值触发的反馈提交提示 MUST 为**非阻塞**一次性提示,MUST NOT 阻塞收尾,MUST NOT **自动传输**任何内容。该提示**面向用户的措辞**——给出用户视角途径、存在途径时 MUST NOT 暴露引擎调用形态——不由本节规定,归本纪律真源统一约束(见头部所有权区那一行指称);本节只拥有该提示的非阻塞与一次性形态。

## 门控观察协议 (Gate Observation Protocol)

每个保留门控(intrinsic 除外:访谈问答/退出门、宪章不可撤销动作确认)挂一个必要性 probe(注册表 `shared/definitions/probe-definitions.md` 的 command-gate / skill-gate 类)。门控触发且用户作出决定后,执行 agent MUST 自动记录观察事实,为框架层确认设计积累证据。

**时机**:门控解除后(用户已作出决定)立即记录;MUST NOT 在决定前记录,MUST NOT 替用户作答。

**记录内容**(仅观察事实,零额外提问):

- `gate_id` — probe 对象的 object_id;
- `fired_during` — 实际调用单元与运行(注册表 unit 为确定性归属单元,实际触发单元只出现在正文);
- 触发上下文一句话;
- 用户决定与决策信号:approved-as-is(照单放行)/ modified(修改后放行)/ asked-questions(追问后放行)/ denied(否决)。

**方法**:

```bash
python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
  --unit-id "<归属单元>" --unit-type "<command|skill>" \
  --lifecycle-point "<gate_id>" --run-id "gate:<gate_id>:<UTC ts>" \
  --review "<观察事实,正文 MUST 含字面标记 confirm-gate>" --points-file "<要点文件>"
```

聚合分析:`--action list --contains confirm-gate`(summary-first,不整文件注入)。

**红线**:

1. 只自动记录;MUST NOT 向用户追加提问;MUST NOT 阻塞宿主流程;
2. 记录失败 MUST NOT 使宿主流程失败——报告警告后继续;
3. gate 对象的锚点是门控点位的单行指针 `> Gate probe: <object_id> — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).`,不参与 wrap-up embed 对账;
4. 指针措辞 MUST NOT 命中 `scan-confirmation-gates.py` 的阻塞模式(不得新增扫描器门控计数)。
