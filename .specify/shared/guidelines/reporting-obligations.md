# 汇报义务(Reporting Obligations)

> **Single Source of Truth**: 本文档是框架「汇报义务」的唯一定义处,拥有下列**八件事**且仅此八件:
>
> 1. 义务的**范围谓词**(哪些流程必须汇报);
> 2. **长跑档缺省周期**(long-run cadence default);
> 3. **reporter 席位义务**(reporter-seat obligation);
> 4. **主从汇报义务**(master-reporting duty);
> 5. **停滞判定引用**(stall judgement reference);
> 6. **非周期汇报的触发事件**(out-of-cadence transition triggers);
> 7. **当前态摘要契约**(digest contract);
> 8. **零新增机制禁令**(zero-new-machinery prohibition)。
>
> 下列四件事**不由本文档拥有**,本文档只以路径 + 节锚点抵达,MUST NOT 复制其规则文本:
>
> - **周期锚点、汇报内容下限(四要素)、原子步骤补报规则、交互档缺省周期** → `.specify/shared/guidelines/progress-reporting.md`;
> - **产物三元组(artifact triplet)与三种执行模态** → `.specify/shared/definitions/subagent-definitions.md`;
> - **停滞阈值的数值表** → `.specify/skills/internal/create-team/references/patterns.md` § Monitoring → Stall Detection;
> - **注册表状态词表(`STATE_VALUES` / `ACTIVE_STATES`)** → `.specify/skills/sdd-loop-driver/scripts/line-registry.py`。
>
> 本文档所引用的每一份借用纪律都以路径 + 节锚点抵达,MUST NOT 在此重述;两份文档一旦对同一事实给出两种说法,以被引用的 owner 为准,本文档按缺陷修正。

**本义务防的失效是「并发即失明」**:流程一旦同时驱动多个单元、或把工作异步派发出去,用户那一侧的输出就退化为「要么全部完成,要么完全沉默」。成员各自在自己的上下文里推进,没有任何一条信息在运行**进行中**抵达用户;用户唯一能看到的时点是最末一次返回或一次失败。它防的不是「没人写日志」——记录往往已经在磁盘上——而是**没有任何人在约定的时刻把它说给人听**。

---

## 一 · 义务的范围是一个可判定谓词(Scope predicate)

一条流程**在范围内**(in scope)当且仅当满足下列两析取之一:

> 该流程派发**两个或更多并发单元**; **或** 该流程持有**一个或多个异步委托**,并在派发之后继续推进它们(不等待返回即结束)。

由此得到的判定后果,与上面一句同权:

- **单个同步步骤不在范围内**(out of scope):它没有并发、也没有跨派发的持续委托,它自己的返回就是汇报。
- 一条出界的流程 **MAY** 用一行说明「本条出界」,而不是产出一份空汇报:空汇报会被读者当作「在跑但无事」,那正是本义务要消除的歧义。
- **不维护任何按流程的豁免花名册**。判定只由上面的谓词给出;一个未在文档中列出的流程,审阅者与机器必须能得出同一个结论。因此本义务 MUST NOT 出现「已登记的例外清单」这种第二判据。

判据只依赖流程的结构(并发单元数、委托是否延续),不依赖它的时长、步数、文件数或工具调用次数。

## 二 · 长跑档缺省周期与覆盖(Long-run cadence default)

<!-- 092 handoff: D4 — 本节是汇报周期数值的**唯一 owner**（长跑档缺省值见本节第一段）；`.specify/shared/guidelines/progress-reporting.md` § 默认间隔与覆盖 只拥有交互档缺省，`.specify/skills/internal/create-team/references/create-mode.md` 与 `agents/reporter.agent.md` 只以指针抵达本节。本节文本保留不改。参见 092 D4，2026-11-09。 -->
框架从**同一个 owner** 读出两档周期,并用**一个已声明的条件**在两者之间选择:

- **长跑档(long-run profile)**:缺省 **30 seconds**。当该结构存在**至少一个活的汇报接收方**时使用——即它拥有一个运行期未被省略的 reporter 席位,或它是一个持有至少一个已派发子流程的监督者。
- **交互档(interactive profile)**:其缺省值与全部语义由 `.specify/shared/guidelines/progress-reporting.md` § 默认间隔与覆盖 拥有,本文档不携带该数值,也不改写它。当上面条件不成立时使用。

两档在同一运行内 MUST NOT 竞争:一次运行只在一档下计时,每条汇报都携带当时生效的档位;运行中途接收方消失(所有 team lane 结束、监督者停止)时,在**下一个边界**切到交互档并**说出来**,切换是被记录的,绝不静默,且 MUST NOT 把两档的 tick 当作同一节奏来报告。

**覆盖**:上面那个数值是**缺省值**,可按运行、按结构覆盖而**无需改源码**——覆盖值由用户或结构声明提供,与档位一起记录,使读者能区分「覆盖」与「定义处」。**本文档是该数值在框架源中的唯一定义处**:其他任何文件只以路径 + 节锚点引用它,唯二例外是一次运行的用户输入值与一份带日期的记录。

## 三 · reporter 席位义务(Reporter-seat obligation)

### 3.1 义务约束的人群

本席位义务绑定的**人群恰是两个集合,无第三个**:

- **(a)** 自交付本义务的提交起,**经框架的 team 创建入口**创建或修改的每一份 team 花名册;
- **(b)** 每一次**以路径显式交送给校验或运行**的花名册。

落在该人群**之外**的花名册——尤其是本义务落地时仓库里**已经存在**的那些——**不受约束**:本义务 MUST NOT 追溯修改它们,其既有修订 MUST NOT 被按席位义务判定,MUST NOT 因本义务而变得不可运行。**对它们不存在任何待办处置,回溯补齐(reporting-reason 回填)不是本义务的交付物。**

### 3.2 人群内的要求

- 每份花名册 MUST 携带**恰好一个** reporter 席位,绑定到框架随附的汇报模板(`agents/reporter.agent.md`),并声明该 reporter 的辖区(territory):读什么、写什么,写面恰好是它自己的流产物。
- 席位是既有 `members[]` 里的一行(判别式 `role: reporter`),不是一个平行的顶层键:花名册成员只有一处表达点。
- 缺少席位 MUST 被报告为一条**点名缺陷**(named defect):缺陷行 MUST 点名 `reporter` 与该队 slug,而不是一句笼统的失败。
- 席位至多一个:出现两行 `role: reporter` 是它自己的点名缺陷,不是通过。

### 3.3 恰好两条逃逸路径,每条都要记录理由

1. **花名册级理由**:该队确实无法承载 reporter(例如宿主不提供可承载它的运行面),于是记录理由值 `host-cannot-host-reporter`。
2. **运行期省略条件**:该队**全部 lane 都由当前会话执行**,**且**整轮运行**预期在一个周期间隔内结束**;此时记录理由值 `all-lanes-in-session-single-interval`,并由此让**编排会话自己承担汇报职责**。

两个理由值构成一个**封闭集合**,值域之外的理由是一条点名缺陷,与「忘记写席位」不是同一件事。**理由值只在席位运行期确实被省略时才存在**:席位照常执行时带着理由值是缺陷。除这两条之外**没有第三条逃逸**:不执行 reporter 而又不记录理由,就是沉默省略,那是本义务防的失效本身。运行期省略条件 MUST NOT 被按队伍逐个判断放宽——两个合取项同时成立才成立。

## 四 · 主从汇报义务(Master-reporting duty)

一个**监督流程**(派发并看守子流程的主控——例如 `skills/external/coaching-skills` 的教练循环)MUST 在每个周期 tick 汇报**每一个**已派发子流程**至少一次**,内容是每个子流程的三件事:

- 它的**身份**(该派发的稳定标签);
- 它的**状态**:`running` / `completed` / `stalled` / `failed`;
- 它**最近一次被观测到的活动**距今的**时长**。

由此派生的三条同权要求:

- **在场是闭合要求,不是抽样决策**:一个子流程在一个 tick 里被漏掉,就是一条以它标签点名的缺陷;它在两次 tick 之间完成时,仍须在观测到该完成的那个 tick 里以 `completed` 出现,**只有在那之后**才 MAY 离开活动集合。
- **只派发一个下级的流程仍在范围内**:它点名那**一个**,而不是报一份空集,也不是只报自己的进度。一个下级被派出并被继续看守,就已经满足范围谓词第二个析取项。
- **汇报描述子流程,不是描述主控**:主控自身的进度 MAY 附带,但 MUST NOT 取代对子流程的逐条陈述。

**停滞判定的引用**:每个子流程的状态判定 MUST 对照一份**已声明的**阈值作出,数值由 `.specify/skills/internal/create-team/references/patterns.md` § Monitoring → Stall Detection 的阈值表拥有——本文档不携带任何阈值数字,也不建立第二份数值表。判定 MUST 区分「比阈值慢(slow)」与「停滞(stalled)」:未超过阈值的静默是 `slow`(它是 `running` 的一个限定词,不是第五个状态);超过阈值才是 `stalled`。汇报 MUST 点名这次判定用了阈值表的**哪一行**(行身份)以及**实测静默时长**,使读者能复核判断;阈值 MUST NOT 按运行临时猜测,也 MUST NOT 由墙钟倒推。

## 五 · 非周期汇报的触发事件(Out-of-cadence trigger classes)

下列三类**显著状态转移** MUST 触发一条**即时**汇报——在**下一个 tick 之前**发出,**不等时钟**:

1. **子流程失败**(非零退出 / 终止哨兵);
2. **跨越停滞阈值**(从 `slow` 进入 `stalled`);
3. **派发失败**(派发本身未能成立)。

与这三类并列、由 `.specify/shared/guidelines/progress-reporting.md` § 不打断原子步骤 拥有的两类时序规则,本文档只抵达不重述:

- **阶段边界**:两次 tick 之间跨过阶段边界时,在边界处**额外**发一条;它 MUST NOT 重置周期计时(三 tick 仍按原锚点到来)。
- **落在原子步骤内部**:瞬时 tick MUST NOT 把不可分割的步骤切成两半;**在该步骤的下一个边界**补报,并**注明延迟原因**。补报是常态,隐藏延迟才是缺陷。

## 六 · 汇报内容与归属(Content and attribution)

每条汇报 MUST 携带四要素,其定义与反例由 `.specify/shared/guidelines/progress-reporting.md` § 汇报内容下限(四要素) 拥有——本文档只**命名**这四个标签,使消费者知道自己必须发出什么,而不复述定义:

| 标签 | 含义由谁定义 |
|------|--------------|
| **position** 位置 | `progress-reporting.md` § 汇报内容下限 |
| **delta** 增量 | 同上 |
| **remainder** 剩余(含粗糙估计,或给出给不出的理由) | 同上 |
| **blocker** 风险 / 阻塞 | 同上;无事时 MUST 显式写出 `no blocker` |

**归属**:每条汇报 MUST 点名发出它的结构身份——结构 slug 与运行戳(run stamp)。两个结构 MUST NOT 能产出字节相同而无法区分的行:一次会话里交错的多条汇报靠这两个字段可辨。运行戳沿用发出流程**已经在写**的那个,本文档不引入新的时间戳格式。

**可读性**:每条汇报是一个受 `.specify/shared/guidelines/user-facing-comprehension.md` 治理的表面;在该处存在用户可读名称时,MUST NOT 携带内部引擎标识符,其余事实以路径引用抵达。

## 七 · 汇报是单向陈述(Reporting is not a gate)

一条汇报 MUST NOT 成为审批请求:它**从不等待回应**,发送后继续执行;它**永不构成**任何动作已获授权的依据。需要用户裁定的动作按 `.specify/shared/guidelines/confirmation-gates.md` 自己的判据**前置征询**——那是确认门,与本义务的节奏无关,两者 MUST NOT 互相替代:一条常规汇报不构成确认门,一次确认征询也不必等到下一个 tick。

由此得出两条可机械判定的形态要求:一条汇报里 MUST NOT 出现疑问句、审批请求或豁免征询;发出汇报这一事实 MUST NOT 授权任何动作。

## 八 · 三种执行模态、两种载体(Three modes, two carriers)

本义务**同等**约束 `.specify/shared/definitions/subagent-definitions.md` § Three Execution Modes 的三种模态(native / virtual / external),无一被豁免:

- 一个**没有原生活跃控制台**的模态,使用其**已经声明的流产物流载体**(该契约 § External Dispatch Visibility Contract 定义的三元组中的 liveness 日志),而不是新造一个通道;
- 一次运行 MUST **在它已经在写的那份运行记录里**记录**模态**与**实际接收汇报的载体**:二者一起记录,读者才能判断「该模态应有的那个面」是否就是被用的那个;
- 载体取值恰好两种:**live console**,或**该流程已声明的流产物路径**。**不引入第四种模态,也不引入第二个载体**,并且不要求把每条汇报单独落成一个工件——被记录的只有「谁收到了它」。

## 九 · 当前态摘要契约(Digest contract)

除按节奏的汇报之外,框架 MUST 提供一条**按需**的当前态摘要,其契约为:

- 输出是**一份有界的**汇总:活动的 line 及其状态、已派发的 agent 及其最近一次观测活动与距今时长、以及最近完成的若干条;
- 它**读状态工件**,不要求任何 reporter 进程存活——摘要必须在汇报流本身停滞时仍可回答;
- **staleness 必须显式**:过期的条目**带其时长一并标记为 stale**,MUST NOT 把过期数据当作当前数据呈现;
- 存在一个**显式的「无人在跑」状态** `nothing-running`:空集合渲染为它,而不是渲染成一份空摘要;
- 有一个**已声明的条目上限**,截断时以 `omitted=<n>` 声明被省略的条数;清单只列**当前工作区**的条目。

命令名与脚本路径由 plan 阶段固定,本文档按名引用:入口为薄命令 `.specify/templates/commands/status.md`(`/speckit.status`),其背后是确定性脚本 `.specify/scripts/python/status-digest.py`。摘要渲染、守卫裁决与单行状态渲染**共享同一次状态读**:第二个 parser 或第二个 renderer 就是本条所指的缺陷,本文档不再描述任何第二个渲染面。

### 9.1 效率维度落在这两个面上(Efficiency dimension on the same two surfaces)

效率维度**不是第三张报表**,而是上述状态行与摘要各自**已有条目的一段内容**:不新增行、不新增条目、不新增小节、不新增节奏,也不新增单位。本维度的渲染字面量只有两个,均以本小节为唯一定义点:`not-evaluated` 与 `no measurements`;元素的具体字段名、宽度界值与渲染位置归交付脚本与其契约片段(`efficiency-element.contract.md` C-63…C-71),此处只按名抵达,不复述。**契约片段在本框架内按名引用,不给出任何仓内路径**:交付仓里的 spec 目录是那一仓自己的开发文档,不随框架分发,写进路径即把框架文本绑到一个仓的布局上。

- **单位是步骤(step identity)**:一条记录的 `(unit_id, unit_type)` 对,而不是任何清单的一行。状态行上的一个元素属于**发出该行的那个步骤**;摘要上的元素属于**本次运行的步骤,或最近的步骤**,其条数由 § 九 已声明的条目上限界定——存储**从不扩大**任一表面自己已经点名的步骤集。
- **来源只读、只读一次**:两个面都从 `.specify/memory/exec-quant/` 读,且只经由存储引擎既有的读取路径读一次;第二个 parser、第二个 renderer 或任何写回都是缺陷,与 § 九 末段的「同一次状态读」是同一条规则。
- **选记录只有一条规则**:同一步骤取 `collected_at` 最新的一条;`collected_at` 并列时,按记录自身的标识(记录文件名的主干)升序取,永不依赖文件系统枚举顺序。不做平均、求和、排名或生命周期聚合——那是 `/speckit.measure` 的问题,不是本维度的。
- **缺失的量渲染为 `not-evaluated`**:一条记录没有携带某个量时,渲染这个标记,MUST NOT 渲染为 `0`、用平均值顶替、或整个省略。一个被点名的步骤即使存储里没有它的任何记录,也仍然带着标记(元素不消失)——省略挨着邻居的数字,会被读成「更快」。
- **存储缺失或为空渲染 `no measurements`**:这是**存储可用性**状态,不是某个步骤的标记;此时行与摘要的其余内容(单位、内容下限、排序、上限、退出码)与不带本维度的渲染逐字一致,并且它不是错误。
- **越界就整体退让**:token 与调用次数只在整段元素容得下时才追加;容不下时从**该次渲染的每一个步骤**上一起撤下,并在该渲染**已有的**省略汇总里点名被撤下的量。两个步骤被描述成两种深度,是不可比的,属于缺陷。

## 十 · 汇报失败要上浮,不得吞掉(A reporting failure is surfaced)

- **发出流程自己的汇报循环** MUST NOT 吞掉自己的失败:一轮运行在预期 tick 无法发出汇报时,MUST 把这件事作为一条**点名的条件**上浮(以 `trigger: reporter-failure` 的那条行),并 MUST NOT 继续把运行说成健康。**「没有行」绝不可被读作「在推进」。**
- 上一条只治理**那个循环**。一个 reporter **成功发出过一条之后再不长进**,是另一个事件:它是与其它派发无异的派发,由编排者**既有的**活性信号与既有阈值表判为 stalled(见 § Monitoring → Stall Detection),再由编排者的汇报点名。本义务**不引入第二个探测器**,也不为它新增判定面。

## 十一 · 零新增机制(Zero-new-machinery prohibition)

本义务 MUST NOT 引入下列任何一项——这是一条**禁令**,由变更文件集的审计判定,不是一句愿景:

**MUST NOT 引入** 调度器(scheduler)、定时器服务(timer service)、常驻进程(daemon)、第三方依赖(third-party dependency)、新的持久化存储(new persistent store)、新的控制台通道(new console channel)、第二份注册表(second registry)、第二份状态脊(second state spine)、或任何台账(ledger)。

节奏由**运行中的流程在它自己的两个步骤之间**执行——这与既有进展汇报纪律已经要求的机制相同——因此既不需要也不允许一个常驻的汇报运行时。本义务读取的每一份状态**都已经有 owner**;若某事实需要一个新的 owner,它被声明为一个新概念,而不是就地内联定义。

---

## 判定边界

- 本文档拥有上面八件事;**不**拥有周期的锚点、内容下限、补报规则、交互档数值(归 `progress-reporting.md`),不拥有三元组与模态(归 `subagent-definitions.md`),不拥有停滞阈值的数值(归 `create-team/references/patterns.md`),不拥有状态词表(归 `line-registry.py`)。
- 与**快速失败纪律**(`.specify/shared/guidelines/fast-fail.md`)的边界:本义务与快速失败注入子句**共用同一条派发载荷通道**,并**不改动**那条子句;reporter 没有被授予修复或中止任何事情的权限(它只观察、只汇报,写面仅限自己的流产物;任何越界改动都是缺陷)。
- 与 **Token 效率纪律**(`.specify/shared/guidelines/token-efficiency.md`)的边界:状态行与摘要是**摘要优先的投影**——只带判定与计数,不把日志或文件原文搬进对话。
- 与**确认门纪律**(`.specify/shared/guidelines/confirmation-gates.md`)的边界:见 § 七。本义务不新增任何确认门。
- 与**单次执行证据纪律**(`.specify/shared/guidelines/single-run-evidence.md`)的边界:那侧管昂贵执行的输出是否完整落盘且后续不重跑;本侧管运行**进行中**向用户暴露什么。汇报中的数字 SHOULD 取自那份留痕,而不是为了取数再跑一遍。
- 与**运行判定**(`.specify/shared/workflow/feedback-step.md` § Run Determination)的边界:本义务是运行**进行中、每隔一段时间**的节奏;运行判定是**收尾时一次**的测量;两者不互相替代,也不互相触发。

## 守卫与证据

本义务的一部分命题是可机械判定的,由 `.specify/scripts/python/status-digest.py --action guard` 裁决。**命题的编号与主题只由契约拥有**:`reporting-obligations.contract.md` C-01…C-13 定义全部十三条命题(`RO-01`…`RO-13`),其他任何表面只按 id 抵达、只陈述「守卫读什么」,不得重述命题断言的内容。本文档不复述那十三条命题清单。

同样由契约拥有、本文档只按 id 抵达的范围:四要素的标签集与归属字段、摘要的条目上限与过期界限的具体位置(分别见 `status-report.contract.md`、`status-digest.contract.md`、`ownership-map.contract.md`)。

框架内的下游表面只以路径引用本文档:MUST NOT 复制上文的八项所有权、范围谓词、周期数值、席位义务文本、主从义务文本、触发类清单或禁令术语表。若某下游表面需要让读者不必打开本文档即可行动,它可以给**摘要 + 指针**,不得给运营细节。
