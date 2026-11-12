# Evidence Discipline — 四条证据纪律与 evidenceState 七态

> 语义移植自 Better Harness `models/agent-work-loop.md`(上游 commit `b2e621d`);
> 本文件是全部证据消费方共享的**语义单一事实源**(各态语义、四条纪律)。七态的**取值域**——成员、次序、基数——
> 不在这里,由 `.specify/shared/declarations/facts/evidence-seven-states.yaml#/statement` 单一拥有。任何消费方不得裁剪或
> 重定义状态语义,只能自定义响应方式。

## 四条证据纪律

1. **配置存在 ≠ 观察到使用**。资产/机制在配置里出现,只证明它 `Present`;是否被真实执行走到,必须由观察证据(会话/运行工件)支撑。禁止把"配了"当"用了"。
2. **未观察保持 Unobserved,不推断**。观察不到的环节如实标 `Unobserved`——它既不是"好",也不是"坏",更不是缺陷。诚实的空白优于编造的结论。
3. **计数只路由检查,不产生发现**。资产数、会话数、运行数等计数信号只用于决定"往哪看",不得直接生成优化点、候选或结论。
4. **隐私:语义面片,不出原文**。任何证据落盘不得包含原始 prompt、原始命令、私有绝对路径、密钥;只允许语义级摘要(semantic facets)与不可逆引用。脱敏漏斗不得绕过。

## evidenceState 七态

**取值域不在本节。** 七态的**成员、次序与基数**由声明层单一拥有：
`.specify/shared/declarations/facts/evidence-seven-states.yaml#/statement`（`kind: closed-set`，框架源相对路径；
客户项目读 `.specify/shared/declarations/` 下的同一份镜像）。本节只保留各态**语义**——语义是本文件拥有的
判据，取值表不是；MUST NOT 把本节读作第二份封闭集，也 MUST NOT 据此新增或重排状态。

各态语义按术语使用列出（术语在此只被解释，不被枚举；成员与次序以上述声明为准）：

- `Present` — 资产/机制在配置或仓库中存在(静态可见)。
- `Wired` — 已接线:存在且被引用/注册/挂载到执行路径上,但尚无执行证据。
- `Exercised` — 观察到真实执行走到了它(会话/运行工件中有使用痕迹)。
- `Outcome-supported` — 不仅被执行,且有前后对比证据支撑其产生了预期效果(compare 判定)。
- `Missing` — 预期应存在的机制不存在(有明确期望基线时才可用此态)。
- `Unobserved` — 无法观察或本次未观察到——保持空白,禁止推断(纪律 2)。
- `Not applicable` — 对该目标单元不适用,跳过。

状态间的典型升格链:`Present → Wired → Exercised → Outcome-supported`;升格只能由**证据**驱动,不能由推断驱动。降格(如 Exercised 声明缺乏引用支撑)同样需要证据。

## 采集子集边界(防侵蚀)

采集子集(`.specify/scripts/js/better-harness/`)**只进事实,不进观点**:上游的评分、严重度、建议目录、渲染层永久排除在子集之外(清单见其 `UPSTREAM.md` 与 contracts/engine-subset-boundary.md)。向子集新增文件必须同步更新 UPSTREAM.md 清单,且不得来自排除清单。

## 消费方响应约定(参考)

消费方(improve-* 等)按 `.specify/shared/workflow/evidence-step.md` 的分拣表响应各状态;红线(Unobserved 不修、计数不产生发现、候选冻结)对全部消费方生效。
