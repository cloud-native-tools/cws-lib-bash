# Run mode — 行为细则（`/speckit.humanize` 的运行模式分支）

**归属**: 本文件是 `.specify/skills/humanize-conclusion/SKILL.md` 运行模式分支的行为细则所有者：入口解析、模式路由、迁移提示与派发。报告面（五节、元数据块、证据与来源清单、语言与保真）的所有者是 `references/report-shape.md`；`SKILL.md` 正文只声明分支边界，不复述这里的步骤、字段或字面量。

**外部所有者**: 派发载体的步骤、拓扑声明与快速失败注入子句归 `run-agent` 技能的 Run Mode；`data-model.md` § E2 / § E5 拥有解析字段与信封字段；requirements FR-019 拥有 verdict 集合与映射；requirements § Shared Strings 拥有全部固定 literal。本文件只固定 humanize-conclusion 侧必须满足的部分，不复制它们。

---

## Parse

入口解析是**纯语法过程**：同样的 argv 得到同样的结果；解析 MUST NOT 读取指令内容来猜测意图，MUST NOT 用「这段文本像内容还是像指令」来决定分支。

1. **选项集**：`--tone`、`--audience`、`--file`、`--inline`、`--output`、`--force`。选项只出现在指令之前。
2. **终止与起点**：`--` 终止选项解析，其后全部逐字进入指令；无 `--` 时，第一个不可识别为选项的 token 即指令起点。
3. **指令逐字**：选项之后的剩余文本整体是**待执行指令**，逐字保留（含换行与引号）；MUST NOT 改写、摘要或规范化它。裸文本 MUST NOT 再被解释为待改写内容——这是 A4 的破坏性变更，迁移方式见 § Migration Hint。
4. **选项语义（沿用 062，不新增取值、不改缺省）**：
   - `--tone`：取值域 `professional` / `humorous` / `empathetic` / `colloquial`；空值、纯空白与集合外取值按 `unknown-tone` 拒绝并列出支持集合。
   - `--audience`：自由文本，只作用于表达层；空字符串或纯空白视为**未提供**（不拒收、不改变表达层缺省）。
   - `--force`：覆盖语义沿用既有契约（目标已存在时需要它）。
   - `--output` 的写入语义按模式分属：内容模式沿用既有契约；运行模式由 FR-024 独占拥有（扩展名封闭集、原子写、会话回显摘要）。
5. **解析结果**：字段集 owner 是 `data-model.md` § E2 —— `tone`、`audience`、`file`、`inline`、`output`、`force`、`instruction_text`、`mode`、`reject_code`。`mode` 只有 `run` / `content` / `reject` 三值；不存在第四种或「模糊」形态。

解析不写任何文件、不派发、不读内容：它只产出一份 E2 结构。

## Mode Routing

判定表是封闭的、按顺序求值，**顺序不可调换**（判据与 `reject_code` 封闭集的 owner 是 `data-model.md` § E2）：

| # | 内容源（`file`/`inline`） | 指令文本 | 判定 |
|---|--------------------------|----------|------|
| 1 | 有 | 非空 | `reject` / `both-sources-and-instruction` |
| 2 | 有 | 空 | `content` |
| 3 | 无 | 非空 | `run` |
| 4 | 无 | 空 | `reject` / `no-input` |

- **两者同现（第 1 行）**：内容源与非空指令同现时 MUST 拒绝并**点名两者**（源名与指令前缀）。MUST NOT 走「内容优先」或「指令优先」的任何猜测分支；该拒绝优先于其他路由判断。
- **空内容源**：内容源自身为空或纯空白时按第 4 行走，拒绝为 `empty-input`——空内容不是内容。MUST NOT 因「有一个内容源参数」而落进内容模式。
- **无输入（第 4 行）**：拒绝消息三项齐全——**用法行**、**支持的内容源**（`--file` / `--inline`）、**迁移提示整句**；MUST NOT 猜测用户意图。
- **拒绝面**：任何拒绝路径 MUST NOT 产生派发、MUST NOT 留下占位、MUST NOT 写入任何文件；拒绝消息 MUST 含原因码对应的点名要素（表 owner 同上，本文件不复述触发条件）。
- **内容模式**：走 `SKILL.md` 的 Stage 1–Stage 7；不派发执行体、不生成动作报告、不读取动作结果、不取得并发占位。

## Migration Hint

迁移提示是**语言不变的固定通知**（与五个英文小节标题同属契约面固定 literal，不随正文语言翻译、不因 `--tone` / `--audience` 改写）。整句原文是：

> 已按指令执行；改写文本请用 --file/--inline

- **触发**：运行模式且调用中**无**任何显式内容源时输出该整句一次；内容模式与拒绝路径不输出该行。
- **落点**：`data-model.md` § E7 `migration_hint`，位于载体标记行之后、五个 H2 之前；MUST NOT 构成第六节；同一运行至多一行。
- **不写文件**：它是调用级会话通知，只在会话回显一次，MUST NOT 写入 `--output` 文件（FR-005 / FR-024）。

## Dispatch

运行模式每次调用 MUST 派发**恰好一个**顶层执行体；一次调用两次派发、或「先试一个再补一个」都判违反。

- **载体**：派发 MUST 经既有 `run-agent` 载体（Run Mode）发起；MUST NOT 引入第二套派发机制、MUST NOT 新建派发脚本、MUST NOT 直接调用某宿主的私有会话 API。
- **执行体**：执行体是**会话级临时执行体**——不写入 `.specify/agents/`、不产生 `.agent.md`、不占 Agent 席位；本次派发不声明 SDD 执行席位；`run-agent` 的「按名解析已存 Agent」分支不适用于本次派发，MUST NOT 因此就在磁盘上创建一个只为本次运行存在的 Agent 定义。若指令本身要启动一次 SDD 运行，那次运行的授权由指令所属单元自己的入口判定，本命令不代替判定。
- **载体模式**：按宿主能力二选一——具备原生派发通道 → `native`；不具备 → `in-session`（会话内执行，不是可选）。`run-agent` 的独立 CLI 进程模式 MUST NOT 被本命令使用：它会带来进程、凭据与网络面。
- **载体标记**：载体标记 MUST 与真实载体一致且恰一个——`native` → `mode: subagent`；`in-session` → `mode: in-session-degraded`。MUST NOT 冒充、MUST NOT 双写、MUST NOT 漏写。降级不得冒充子代理，也不得把会话内执行的推断当作子代理的观测。

## Payload

派发载荷是执行体在本跳能看到的**全部**上下文——它拿不到本会话的其余部分。载荷 MUST 按下列顺序携带六项，顺序本身是契约面（EX-06）：

1. **快速失败注入子句**：第一项，置于载荷开头的**独立段落**，不与其他规则混排。其内容 MUST 与 `.specify/shared/guidelines/fast-fail.md` § 子代理派发注入 的拥有者字面量**逐字节相等**；本文件只引用该所有者，MUST NOT 在此改写、摘要、缩写或重排它。缺该子句即判载荷不合格，按 `contracts/execution-dispatch.contract.md` EX-11 处理：MUST NOT 以「补发一次」修复。
2. **指令原文**：逐字（含换行与引号），与 § Parse 解析出的 `instruction_text` 完全相同。MUST NOT 附加步骤编号、注释、执行提示或「建议先读某文件」一类的先验。
3. **回传信封的字段与封闭取值**：点名回传 MUST 是 `data-model.md` § E5 的信封，并列全该表的字段名；`status` 的取值域只引用 requirements FR-012（本文件不复述枚举）。执行体 MUST NOT 自创字段或改写取值。
4. **不得撰写最终报告**：执行体只回传信封；报告由 humanize-conclusion 主会话撰写，形态归 `references/report-shape.md`。执行体写了报告也算违约，其输出不做报告来源。
5. **不得重试、不得代替用户答复确认**：失败即失败；确认由指令自身的步骤处理，执行体与主会话都 MUST NOT 代答、MUST NOT 推断「用户大概会同意」。
6. **指令自身再调用本命令即拒绝并回传**：指令文本命中封闭 token 集时按 `data-model.md` § E2 的 `nested-invocation` 拒绝，拒绝结果作为信封内容回传，MUST NOT 继续执行该指令。

载荷 MUST NOT 把指令改写成步骤清单、MUST NOT 预先替指令挑选实现路径、MUST NOT 把 humanize-conclusion 的报告要求当作指令的执行目标（EX-07）。载荷 MUST 声明：**指令自身的确认步骤与权限边界优先**——执行体遇需确认且无法取得答复时**停在该步**，MUST NOT 继续推进、MUST NOT 换一个等价动作绕开；该停点按 § Envelope 的 `blocked_at` 回传（EX-08）。

## Envelope

回传 MUST 是 `data-model.md` § E5 的**消息**，不是报告文件：执行体只回传信封，MUST NOT 以「写了报告文件」代替回传；本次运行对报告不做任何磁盘写入（**零写入**，A9 / EX-09）。

### 逐字段语义

- `status`：七个取值；取值域的拥有者是 requirements FR-012，本文件不复述枚举。三个取值在 humanize-conclusion 侧另有落点：
  - `denied`：用户**明确拒绝**确认。该步 MUST NOT 被执行，且 MUST NOT 执行任何替代动作；报告 verdict 按 FR-019 的映射取 `aborted`（映射 owner 是 FR-019），文案 MUST 写明「用户拒绝确认」与未执行范围。
  - `needs-confirmation`：需确认而无法取得答复；不变量见下，报告口径由 § Confirmation Missing 拥有。
  - `not-an-action`：指令不是可执行动作；报告措辞见 `references/report-shape.md` § Conclusion。
- `products`：`{path, kind: created|modified}` 列表，只写**指令造成**的写入，逐项。
- `evidence`：`{pointer, kind: command|path|reading}` 列表——命令与退出码、产物路径或测试读数，供报告前逐项核对可定位性（EX-14）。
- `failures`：`{where, what}` 列表，失败坐标与信息；无失败为空列表。
- `blocked_at`：需确认却无法询问时停下的位置；无卡点为 null。
- `anomaly_line`：显式异常行。无异常写 `未发现异常`；有异常以**行首** `ANOMALY:` 逐条列出。子句本身的物理注入归 § Payload 第 1 项。

### 不变量

- `needs-confirmation` ⇒ `blocked_at` 非空，且 `products` 只含该步**之前**已完成的写入。
- `completed` 且无输出、无产物 ⇒ 报告如实写「无可报告输出」，`## Evidence` 写 `none`（`none` 的字面量 owner 是 requirements § Shared Strings）；MUST NOT 编造证据填空。
- **缺显式异常行即判信封不完整**：其结论 MUST NOT 被消费，报告按失败/不完整处理，并在 `## Conclusion` **点名缺失项**（EX-10）。这是硬判定，不是风格建议——沉默 MUST NOT 被读作干净。

## Context Assembly

报告动笔之前 MUST 装配三类上下文，并**逐类**记录状态（三态语义与判定 owner 是 requirements FR-014；字段集 owner 是 `data-model.md` § E6）：

| 类 | 内容 | 读取口径 |
|----|------|----------|
| 动作输出/证据 | 回传信封的 `final_output`、`products`、`evidence`、`failures` | 逐项核对可定位性；核对不上的记「未能核实」 |
| 项目治理（四件） | `.specify/instructions.md`、`.specify/constitution.md`、`.specify/glossary.md`、`.specify/features.md` 的 062 / 079 行 | 摘要优先：治理文档取相关段落，Feature 注册表取行投影 |
| 本次会话 | 调用方在本次会话里已给出的指令、确认与答复 | 只取可复核的部分；推断不算读取 |

- **摘要优先**：MUST NOT 把机器管理的原始数据文件整文件注入——Feature 注册表 MUST 只取行投影，治理文档 MUST 只取相关段落。整文件注入既浪费上下文，也会把无人阅读的细节误当作「已装配的上下文」。
- **尝试并记录**：装配是 attempt-and-record，不是「必须可读」。路径不存在或不可读记 `unavailable`，本轮未尝试记 `not-read`，实际载入记 `read`。MUST NOT 为了来源清单好看把未载入的来源记为 `read`。
- **落点**：三类来源的读取状态决定 `references/report-shape.md` § Risks & Limits 的来源清单与缺失声明；装配本身不写盘（零写入），也不产生任何中间文件。

## Failure & No Retry

失败就是失败：本次运行至多一次执行尝试，不自动重试，也 MUST NOT 用第二次派发补救第一次的失败。

- **不补发**：载荷发出后才发现缺快速失败注入子句时，MUST 停止消费该次结果并按失败报告；MUST NOT 以「补发一次」修复——补发本身就是第二次派发，按 § Dispatch 的恰好一个与 EX-11 判违反。
- **失败坐标**：派发失败、超时或执行体中止时，MUST 在 `## Evidence` 记录失败坐标——载体（`native` / `in-session`）、阶段（parse / dispatch / execution / report）、错误信息——与已完成部分；MUST NOT 改写为成功，MUST NOT 用「基本完成」掩盖失败。
- **超时不可判**：超时的定义与阈值归执行载体/宿主所有；载体不提供超时信号时该失败类别不可判，MUST 在 `## Risks & Limits` 声明，MUST NOT 自设阈值。
- **用户中止**：指令被用户中止时，MUST 记录中止点与已完成部分，报告口径为「已中止」；MUST NOT 使用成功措辞。
- **证据可定位性核对**：执行体回传的 `products` 与 `evidence` MUST 逐项核对——路径存在且可打开、命令与退出码自洽、读数可复核；核对不上的项 MUST NOT 作为证据写进报告，MUST 在 `## Risks & Limits` 记为「未能核实」。核对是报告前的动作，不是可选的形式检查。
- **派发计数不因失败而变**：`## Evidence` 的 `dispatches:` 行在失败路径仍须出现，取值口径归 `references/report-shape.md` § Evidence（只计 humanize-conclusion 发起的顶层派发）；失败 MUST NOT 被计成第二次派发。

## Confirmation Missing

执行体执行到**需要用户确认**的步骤、而它无法向用户提问时，行为是 fail-closed：不执行该步，不猜、不代答、不绕开。

- **停在该步**：该步 MUST NOT 被执行；`blocked_at` MUST 记录卡点（步骤位置），`## Conclusion` MUST 写「需要确认，未获答复」并给出一句可直接行动的理由（例如需要用户确认哪一步）。
- **其余已完成部分照常报告**：卡点之前已完成的部分 MUST 照常写进报告；`products` 只含该步之前已完成的写入，MUST NOT 把未执行的步骤算作完成。
- **不代答**：humanize-conclusion 主会话 MUST NOT 代替用户回答该确认，MUST NOT 以「用户可能同意」继续，MUST NOT 换一个等价动作绕开该步；转达请求或答复不等于代答。
- **用户明确拒绝（`denied`）**：当用户明确拒绝确认时，该步 MUST NOT 被执行，且 MUST NOT 执行任何替代动作（零副作用）；`## Conclusion` MUST 写明「用户拒绝确认」与未执行范围，`## Evidence` MUST 列出拒绝原因与未执行范围；verdict 按 FR-019 的映射取 `aborted`（映射 owner 是 FR-019）。拒绝路径 MUST NOT 派发、MUST NOT 留下占位、MUST NOT 写入任何文件。
- **不是失败，也不是成功**：确认缺失停在卡点并如实报告，等待用户答复后才能继续；MUST NOT 把它写成失败或成功。

## Degradation & Boundaries

宿主没有原生派发通道时，命令 MUST 降级为会话内执行（不是可选），并声明降级：载体标记写 `mode: in-session-degraded`，派发记录为 `dispatches: 0`。降级不是失败，也不是冒充——MUST NOT 冒充 `mode: subagent`。

- **只把可观察结果当事实**：会话内执行能看到什么就写什么；MUST NOT 把推断描述为子代理的观测，MUST NOT 声称有独立上下文或独立工具集，MUST NOT 假装有一条并不存在的派发通道。
- **降级不改报告契约**：五节、证据义务与保真底线在降级下完全不变；降级只改载体标记与该载体带来的限制描述（例如「无独立上下文，观测来自本会话」写进 `## Risks & Limits`）。
- **humanize-conclusion 自身的边界**：humanize-conclusion 自身 MUST NOT 发起网络请求、MUST NOT 调用外部服务或模型 API。指令自身按其契约产生的联网行为（例如指令要求查询某个服务）MUST 在 `## Evidence` / `## Key Changes` 披露，MUST NOT 记作 humanize-conclusion 的外发；披露不等于授权——指令自身的权限边界由指令所属单元判定。
- **零写入边界**：未给 `--output` 时 humanize-conclusion 不写报告、不写副本；指令造成的写入按 § Envelope 的 `products` 逐项披露。

## Reservation & Nesting

运行模式的并发与嵌套判定是 fail-closed 的；内容模式不取占位、不受并发拒收影响。

### 占位（E4）

- **仓库级占位**：派发前 MUST 在 `.specify/.tmp/humanize-conclusion/<run_id>.run` 建立仓库级占位（一文一件，文件名即 `run_id`）；同一仓库（`git rev-parse --show-toplevel`）同一时刻至多一个未过期占位。
- **已有占位 → `active-run`**：已有未过期占位时 MUST 拒绝为 `active-run`，点名冲突 `run_id` 与起始时间；MUST NOT 排队等待、MUST NOT 复用他人占位。
- **目标级占位**：给 `--output` 时 MUST 同时取得目标级占位；目标已被另一未过期运行占用时 MUST 拒绝为 `output-occupied`，点名目标路径与冲突 `run_id`。
- **遗弃占位**：超过 24h 的占位视为遗弃，MUST NOT 阻断本次运行，MUST NOT 删除他人文件，只在 `## Risks & Limits` 点名「检测到遗弃占位」。
- **出口记账**：任一出口——正常、失败、中止、异常——MUST 释放本人占位；占位残留即判违反，不留残骸。

### 嵌套（封闭 token）

- **`nested-invocation`**：指令文本含封闭 token 集 `speckit.humanize`（大小写不敏感）时 MUST 拒绝为 `nested-invocation` 并点名命中的字面量。这是**保守判定**：宁可误拒提及该名称的指令，也不放过一次真实嵌套；拒绝消息 MUST 说明这一点。

### 拒绝路径与计数口径

- **拒绝路径零副作用**：任何拒绝路径 MUST NOT 产生派发、MUST NOT 留下占位、MUST NOT 写入任何文件；拒绝消息 MUST 含原因码对应的点名要素（owner = `data-model.md` § E2 `reject_code` 表）。
- **派发记录口径**：`## Evidence` 的 `dispatches:` 行只计 humanize-conclusion 发起的顶层派发（原生 `1` / 降级 `0`）；指令自身再发起的派发归该指令单元，MUST NOT 重复计数。计数口径的 owner 是 `contracts/execution-dispatch.contract.md` EX-21，报告面落点见 `report-shape.md` § Evidence。

## Output

运行模式给 `--output` 时 MUST 写出一份完整五节报告；未给 `--output` 时报告只回会话（零写入，见 § Envelope）。

- **扩展名封闭集**：运行模式的目标扩展名只有 `.md` / `.markdown` / `.txt`（大小写不敏感）；集合外拒绝为 `bad-extension` 并点名该值与支持集合。运行模式没有输入格式可对齐，MUST NOT 复用内容模式的「扩展名跟随输入」规则。
- **写入内容**：写入的 MUST 是与目标内容一致的完整五节报告，并在五个 H2 之前包含载体标记行、`verdict:` 行与 `dispatches:` 行（行格式与取值口径的 owner 是 `references/report-shape.md`）。MUST NOT 写入迁移提示行——迁移提示是调用级会话通知（§ Migration Hint）。
- **会话回显**：写文件后会话 MUST 回显一份摘要；摘要只作索引，MUST NOT 替代报告，MUST NOT 成为报告的第六节。
- **原子写**：写入 MUST 是原子写——先在同目录写临时文件，再重命名到目标；失败时删除临时文件。
- **覆盖与失败**：目标已存在且未给 `--force` → 拒绝覆盖，目标逐字节不变；目标不可写（父目录缺失、权限不足）→ 拒绝，删除临时文件，不留部分文件，既有目标逐字节不变。
- **内容模式不变**：内容模式的 `--output` 语义完全不变——扩展名与输入格式族一致、文件只含改写文本（见 `SKILL.md` Stage 7 与 IP-17）。
