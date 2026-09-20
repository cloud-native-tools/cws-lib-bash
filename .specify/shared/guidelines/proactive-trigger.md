# Proactive Flow Trigger(主动触发纪律)

主动触发纪律的**单一真源**。指令模板(`templates/instructions-template.md`)的 `## Proactive Flow Trigger` 章节只承载摘要 + 指针,细节一律落在本文档;本文档的可达性由该章节自身的指针提供——即本文档路径 `shared/guidelines/proactive-trigger.md` 出现在那个新章节里。指针不依赖在既有章节(如文档地图表)内部新增一行,因为增量调谐只按整章节传播,既有章节内部的改动抵达不了已初始化项目。

机制目的:把"用户必须记得流程名才能用上框架能力"反转为"框架在每个回合主动提议下一步流程"。提议永远是非阻塞的——用户可采纳,也可忽略;忽略不影响其当前请求。

## Ownership

本文档是以下各节所述规范的 owner(单一真源 / single source of truth):Evaluation Cadence(评估节奏)、Evidence Budget & Escalation(证据预算与升级判据)、Suggestion Shape(建议形态)、Ordering Contract(顺序契约)、Telemetry & Retention(遥测与保留)、Tuning Protocol(调优协议)、Global Switch(全局开关)。

派生数据与运行状态的归属不在本文档:

- 情境→流程的规则数据归 `templates/proactive-trigger-seed.json`(出厂种子)与运行期状态存储;情境词表的权威定义随特性设计期的 `data-model.md` 记录。该设计期文档是 dated record(设计期记录,不随包分发、不作为当前现实被引用),因此与本文档并存不构成漂移。
- 引擎的信封形状、CLI 封闭枚举、退出码与运行期语义归 `contracts/trigger-engine.md`;本文档只列 action 名与用途一行,细节指向引擎 `--help`。
- 动作的破坏性/可逆判据归 `shared/guidelines/confirmation-gates.md`;本文档只以路径引用,不复述其分类表或清单。
- 面向用户的措辞与上下文规则归 `.specify/shared/guidelines/user-facing-comprehension.md`(本文件覆盖界面类 ⑥);本文档只以路径引用,不复述其白/黑名单与上下限条件集。本文档 § Suggestion Shape 的"一行非阻塞提示"形态是**该界面类既有的长度/形态约束**,由该纪律的上下文上限以引用方式沿用,两侧都不改写对方。

## Evaluation Cadence

**每个用户回合都评估**(every user turn):在回应回合请求的同一趟分析里,先判定当前是否处于某个已知情境,再决定要不要提议流程。

**评估是静默的**(assessment is silent):无适用流程、或状态自上次评估未变时,产出**零用户可见输出**(zero user-visible output)。静默是正常结果,不是失败——机制的价值来自命中时的准确,不来自每回合都出声。

**评估节奏 ≠ 建议节奏**:每回合评估不等于每回合建议。评估是廉价且总是发生的;建议只在情境命中且未被会话级抑制时才出现。

评估的调用形态是一趟紧凑的引擎调用(`assess`),agent 只传它已从环境上下文得知的粗粒度信号,不为此额外读文件。

## Evidence Budget & Escalation

**默认只用已在上下文中的信息**(only information already in context):agent 把它已经知道的生命周期阶段与待处理信号作为参数传入,引擎不打开任何制品文件。

默认不升级。仅当下列条件成立时才加 `--probe`,由引擎执行确定性状态探测:

| # | 升级条件 | 探测内容(引擎侧,确定性) |
|---|---|---|
| P1 | 环境上下文未出现当前特性目录/分支信息 | 特性目录下最高编号者 + 其 requirements/plan/tasks 三件的存在性 |
| P2 | 无法判断 requirements 是否含未决标记 | 对 requirements 做未决标记的**计数** |
| P3 | 无法判断 tasks 完成度 | 对 tasks 做开放/关闭/延后三态的**计数** |
| P4 | 无法判断反馈是否达阈值 | 调既有反馈引擎的状态 action 取阈值字段 |
| P5 | 无法判断指令文件是否陈旧 | 指令文件与指令模板的 `## ` 标题**集合差** |

探测 MUST 限于**存在性/计数/集合差**这类固定规则判定(Program-First),MUST NOT 读入制品全文(full artifact text);探测结果只回摘要,单条有长度上限。

**升级率上限**:探测升级的回合占比默认上限 20%,口径的分母是 `assess` 调用数(`assess` invocations)。该口径的局限见 Telemetry & Retention 的度量边界声明。

## Suggestion Shape

一条建议 = **一行非阻塞提示**(one non-blocking line),由两部分组成:该流程解决什么(用途说明)+ 引擎给出的**确切调用形式**(exact invocation form,可直接复制,不需用户回忆或改写)。

**频次有界,且边界由机制而非劝告定义**:同一会话内同一情境同一规则不重复产出——**会话级重复抑制**(session-level repeat suppression)由引擎侧提供结构保证(见 `contracts/trigger-engine.md`),不依赖 agent 自觉"不要刷屏"。

**多规则命中收敛为一条**(converge to a single suggestion):按规则优先级取最高者,不并列多条让用户挑选。

**无适用流程时如实不建议**(suggest nothing):MUST NOT 为凑数而给出弱相关流程。"本回合无建议"是合法且有价值的输出。

建议永远不阻断当前回合:用户不回应即视为忽略,忽略不改变任何状态,也不影响其正在做的事。

## Ordering Contract

**合规检查先行,流程选取在同一趟接续**(same analysis pass):回合内先完成既有的输入合理性与项目指令要求,紧接着在同一趟里判定情境——不分两次思考,也不把提议挪到回应之后。

建议 MUST NOT 早于合规检查产出(before the compliance check):先合规、再选流程。合规结论可能改变情境判断,顺序颠倒会给出错误建议。

MUST NOT 把规划期的逐原则枚举门控搬到每回合(every turn):`plan-template.md` 的 Constitution Check 属规划期制品义务,一次规划评一遍;每回合只承载轻量合理性检查。把逐原则枚举塞进每回合会让机制成本失控。

**调用引擎评估时 MUST 显式声明合规检查已完成**:传 `--compliance-done`。该 flag 缺省为 false;缺省即如实报 `ordering-violation`,使"先合规再建议"成为可度量的时序,而不是一句无法核验的劝告。

## Promotion & Safety Boundary

**晋升**:同一规则被连续采纳达阈值(默认 3)后晋升为免确认自动执行;**一次拒绝即重置**(a single decline resets),连续计数归零、晋升态回落。忽略与拒绝在重置上同效,但在统计里分列。

**破坏性/不可逆流程永不晋升**(never promoted):判据以路径引用 `shared/guidelines/confirmation-gates.md`,本文档不复述其分类表;**存疑从严**(when in doubt, treat as destructive)——分类是数据,引擎只读不算,任何本地调优都不得把破坏性规则改写为可晋升。

**自动执行仍出执行报告**(execution report):晋升不等于静默。自动执行的流程照该判据文档规定的报告形态呈现结果,使用户事后可修改。

**自动执行 MUST NOT 抢占用户当前请求**(preempt the user's current request):情境命中但用户正在推进别的事时 MUST 让位(yield)或延后到该请求收尾。引擎从不自行执行任何流程——它只产出建议;执行时机由 agent 掌握,本条约束的正是这个时机。

**用户可复位**(reset):单条规则可复位其连续计数与晋升态,也可全局降级(下调阈值或关闭机制)。复位是常态操作,留痕于状态存储。

## Telemetry & Retention

**每回合恰好一行遥测**(one row per turn)追加到 `telemetry.jsonl`:记录本回合的情境解析结果、是否产出建议、是否升级探测、是否有可见输出、以及合规时序标志。它是升级率与顺序契约两项度量的分母来源——没有自产遥测,这两项只能靠人工观察。

**保留窗口有界**:默认窗口 200 回合。写入即执行窗口约束,形成**追加即截断**(append then truncate)的恒真不变量——文件行数任何时刻都不超过已声明窗口,不需要"记得去清理"。

**轮转不清空学习结果**:晋升计数是规则上的**聚合态**(aggregate state),内嵌于状态存储;轮转或截断只作用于遥测行,MUST NOT 触及规则状态,因此轮转前后规则集与晋升态逐字节相等。

**度量边界(诚实声明)**:遥测**无法证明**(cannot prove)agent 跳过了某回合的评估——分母只统计实际发生的调用,静默跳过不留痕。故升级率的读数须附会话侧观察,不得当作"每回合都评估了"的证明。

## Tuning Protocol

调优由四类证据驱动:**命中率**、**拒绝率**、**误报**(建议了但情境判断本不成立)、**漏报**(该建议而未建议——由用户手动调用某流程、而当回合遥测显示无建议时取证)。

**小样本守卫**:`hits < 5`(默认下限 5)的规则 MUST NOT 产出提议;被跳过的规则在输出的 notes 里**具名**回显,使"为什么没提议它"可查,而不是静默略过。

**提议以候选形态呈现**(presented as candidates),每条附指标与样本数;**用户批准后写入**规则集,未经用户批准 MUST NOT 变更规则集。措辞上这是批准而非阻塞:提议摆在那里,用户可以直接采纳、改写或忽略,忽略不阻断任何流程。

**可回查**:提议走 `proposed → ratified → applied` 两段转移,批准后写下批准时间戳与 `evidenceRef`(证据引用),使任一条已生效的调优都能回溯到当初支撑它的数据。

语义判断(该不该采纳某条提议、新规则该配哪条流程)不由引擎裁定,经信封的待判断字段交回 agent;引擎只做确定性聚合。

## Global Switch

`config.enabled=false` 的语义是双重的:**不产出建议**且**不自动执行**(no suggestions, no auto-execution)——已晋升的规则同样停摆,不因为"以前批准过"就继续代用户行事。

**用户显式关闭优先于框架默认**(overrides the framework default):框架出厂开启不构成对用户选择的压制。

**关闭状态 MUST NOT 被指令再生覆盖**(overwritten by regeneration):运行状态与指令文件是分离的两个面——再生指令文件只重写指令内容,不触碰状态存储,故关闭状态跨再生、跨会话存活。

**由 false 转 true 时清空会话抑制态**(clears the session suppression state):重新开启意味着用户想重新看到建议,若沿用旧的抑制记录,会出现"开了却长时间不出声"的假死。

## Maintenance Duties

三项常设义务:

1. **改来源必同步种子**:改写任一命令模板的 `## Handoffs` 段(或 owning-section 类来源段落)后 MUST 同步(seed)种子文件,否则漂移检出契约会失败;**修复方式是同步来源与种子,而不是放宽测试**(loosen the test)——放宽测试等于把"响亮失败"换回"静默分歧"。
2. **词表扩展只经批准通道**:情境与信号词表的扩展 MUST 走用户批准通道(user approval channel),MUST NOT 临场造词(invent situation words on the fly)。临场造词会让同一状态在不同会话解析出不同身份,直接摧毁跨会话可比性。
3. **接口面变更同批修订契约**:新增 action、flag 或错误码 MUST 在同批变更(in the same batch)里修订 `contracts/trigger-engine.md` 的封闭集条款(C-9 action 枚举 / C-10 flag 封闭集 / C-22 错误码),否则封闭集断言与实际接口面失配,契约沦为装饰。
