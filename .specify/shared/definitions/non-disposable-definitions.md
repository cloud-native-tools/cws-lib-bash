# Non-Disposable Definitions — 「不可一次性处置」的唯一 owner

> **Merged into `090-re-anchoring`**（2026-11-09 用户裁定）：本页原属特性 `092-non-disposable`，该特性整体并入
> `090-re-anchoring` 作为其附加章节。本页的路径、条目编号与封闭集成员**不变**；变化的只有承接特性的编号，
> 以及本页在其中的位置。特性侧的合并形态（章节追加、条款 id 命名空间、任务重编号）由
> `.specify/specs/090-re-anchoring/` 拥有，本节只记录这条归属事实。

**本文档是「Non-Disposable（不可一次性处置）」的唯一真源（owner）。** 它拥有，并且只拥有以下这些条目
（FR-001 要求文件头部逐条声明所拥有的条目）：

| # | 拥有的条目 | 章节 |
|---|---|---|
| 1 | 理念定义与「过期 / 无用 / 延期」的可观察定义 | `## Non-Disposable` |
| 2 | 检测类别的封闭集（八类）与每一类落在哪个读物上 | `## Detection Categories` |
| 3 | 判定主体的封闭两值（`deterministic` / `semantic`）及其边界 | `## Detection Subject` |
| 4 | 回顾面的定义（十个 `.specify/` 历史根）与「不读 git 历史」边界 | `## Review Surface` |
| 5 | 处置集的封闭四值 | `## Disposition Set` |
| 6 | 豁免形态与到期语义 | `## Exemption` |
| 7 | 两套处置词汇之间的两张封闭映射表与唯一裁决规则 | `## Disposition Bridge` |
| 8 | 处置的落盘通道（归档是移动、删除不是处置） | `## Disposal Pathways` |
| 9 | 取代协议与取代登记行 | `## Supersede Protocol` |
| 10 | 重编号判据面（活绑定四形态 / 历史记录不可改写） | `## Renumber-Face` |
| 11 | 报告条目与报告封套的字段义务 | `## Report Entry` · `## Report Envelope` |
| 12 | 检出引擎的调用面（退出码、参数、分片、确定性、投射） | `## Engine Contract` |
| 13 | 改动前读数的捕获规则（四项读数 + 基线不是阈值） | `## Capture Rule` |
| 14 | 档 II 移交标记的落点与计数口径 | `## Handoff Rows` |
| 15 | 与 sanitize / history 的边界 | `## Boundary with Sanitize and History` |
| 16 | 执行段不得绕过确认设计行（与 C-410 同一条读数；named 与 confirmed 两侧） | `## Seam Bypass` |
| 17 | 与宪法的关系（未新增原则的裁定与理由；与 One Source of Truth / Fast Fail / Directory Governance / Re-Anchoring 的四条分界） | `## Relation to the Constitution` |

其他任何位置——命令模板、技能、指令面、契约、守卫、检查器——MUST 以「摘要 + 路径」引用本文档，MUST NOT
复制本文档的封闭集成员、矛盾表格子或处置映射表。检出引擎 `.specify/scripts/python/non-disposable-check.py` 的
`--emit-categories` 输出与本文档 § Detection Categories MUST 双向一致；不一致是缺陷，不是可选配法。

**不在本文档（只给指针，不复述）**：

| 主题 | 所有者 |
|------|--------|
| 条目的字段集、状态机、豁免字段形状、证据文件形状 | `.specify/specs/092-non-disposable/data-model.md`（E-1…E-9） |
| 闭环裁决、reason code、验证词表、smoke 记录 | `.specify/shared/workflow/acceptance-hardening.md` § Closure Verdict / § Verification Vocabulary |
| 材料卫生的类别 / 处置 / 状态 / 判定主体四个封闭集 | `.specify/scripts/python/sanitize-utils.py` 的 `CATEGORIES` / `DISPOSITIONS` / `STATES` / `DETECTIONS`（契约 `045-sanitize-command`） |
| 活绑定 / 历史记录的路径判据 | `.specify/scripts/python/renumber-utils.py` 的 `EXCLUDED_PREFIXES` / `MACHINE_PREFIXES` / `EVIDENCE_SEGMENTS` / `DATED_RE` |
| 特性注册表状态值的状态机 | `.specify/shared/workflow/feature-integration.md` § Status State Machine + `.specify/templates/feature-details-template.md` § Canonical Status State Machine |
| 决定张力记录的形态与判据 | `.specify/shared/guidelines/decision-tension.md` + `.specify/scripts/python/validate-decision-tensions.py` |
| `**Path**:` 标记的位置与取值域 | `.specify/shared/workflow/acceptance-hardening.md` § Closure Verdict（`### Input contract — the Path marker`） |
| 声明层的读取入口与 YAML 子集 | `.specify/scripts/python/declaration_reader.py` |
| 一条条款的语法与引用组 | `.specify/shared/definitions/contract-clause-definitions.md` |
| 档 II 移交的**行**（语料编号 → 承接特性 → 落地面） | `.specify/specs/092-non-disposable/plan.md` § Shift List |

**权威次序**：代码 > 生成物 > 撰写物。本文档与 `.specify/scripts/python/non-disposable-check.py` 的常量冲突时，
代码赢，本文档 MUST 被修订（宪法 VIII）。本文档与 `.specify/shared/declarations/facts/non-disposable-review-surface.yaml`
在回顾面成员上冲突时，声明层赢（`data-model.md` E-8）。

**框架源与运行时投影**：框架源为本文件 `.specify/shared/definitions/non-disposable-definitions.md`；运行时镜像为
`.specify/shared/definitions/non-disposable-definitions.md`，由 `.specify/scripts/python/sync-mirrors.py` 生成，
MUST NOT 手改。

---

## Non-Disposable

**理念**：任何过程与文档都不是**用过即丢**（use and throw）。历史是必读输入，而不是可以不再打开的存档；
因此一个载体 MUST 时常被回顾，并在不再成立时被**处置**。

本文档要消灭的是把一个已知问题**推到将来**的行为，其两种常见形态是：「这个没用了，但是留在这里」与
「这个过时了，但是我现在不想删除」。两者共同的结构都是**沉默的留存**：树上没有任何一处记录这个决定，
于是下一位读者只能靠自己重新发现它。

### 三类被判定状态的**可观察定义**（FR-002 / FR-003）

一个状态 MUST 被判为「过期 / 无用 / 延期」当且仅当它命中下表的那一条**可判定判据**。判据 MUST 是有限项，
MUST 落在程序可读或带引用的语义读物上；MUST NOT 以「作者认为」或「读者感觉」为判据。

| 状态 | 可观察定义 | 判定主体 |
|------|-----------|---------|
| **过期**（stale） | 载体与当前事实不符：它引用的路径 / 计数 / 状态字段 / 版本标识与树上的当前读数不一致 | `deterministic` |
| **无用**（useless） | 载体对当前任何消费者都无输入作用：无入向引用、不在任何注册表或索引中、不被任何引擎读取 | `deterministic`（可解析引用形态）· `semantic`（"谁引用谁"的自然语言形态） |
| **延期**（deferred） | 载体上存在一处**未附到期条件**的留存声明（"以后再说"／"暂时保留"／"留待下轮"） | `deterministic`（引用其到期字段的字面形态） |

这三项是**可判定状态的名称**，不是形容词：只写类别名而不写「可观察定义 + 判定主体 + 不可判定时的降级形态」
三件套的类别，MUST NOT 进入封闭集。

### 判定的降级形态（FR-005）

不可判定 MUST 有降级形态且 MUST NOT 降级为「干净」：

- `deterministic` 类输入缺失、不可解析或引擎读取失败 → 该条目落 `unevaluated`；
- `semantic` 类 subagent 返回缺失或不合规 → 该片落 `unevaluated`。

`unevaluated` MUST 在报告中可见，并 MUST 计入「未闭合」总数；MUST NOT 被计为「无检出」。
`unevaluated` 是两个不同结论的分界：**"我看过了，没有"** 与 **"我没能看"**。把后者写成前者，就是把一次
失败的读取冒充成一次干净的回顾。

## Detection Categories

**八类是封闭集**（FR-001 / FR-003 / FR-010）。第九类是一次契约修订（先改本文档，再改
`contracts/detection-categories.contract.md`），绝不是引擎侧的局部新增；引擎遇到一个不在本节的类别名时，
MUST 报一条 `unknown-class` 条目，MUST NOT 把它当作一个额外的类别静默发出。

| # | 类别 | 状态轴 | 一句话判据 |
|---|------|--------|-----------|
| 1 | `superseded-live` | 过期 | 一段被取代的正文 / 守卫 / 证据路径仍以「当前有效」的姿态活着 |
| 2 | `multi-owner` | 过期 | 同一个名称 / 常量 / 计数在同一轴上被独立地定义或独立地陈述了两处以上 |
| 3 | `orphan-path` | 过期 | 一处被引用的路径在树上不存在 |
| 4 | `renumber-live-binding` | 过期 | 一处**活绑定**携带的特性编号与其所在目录的编号不一致 |
| 5 | `status-unreadable` | 过期 | 一处状态声明与它据以成立的读物矛盾，或该读物缺字段 |
| 6 | `false-closed-set` | 过期 | 一处被声称的封闭集恒等式，复算后两侧不成立 |
| 7 | `stale-constant` | 过期 | 同一个常量在两处以不同的当前值出现，而其中一处不是该值的 owner |
| 8 | `deferral-marker` | 延期 | 一处留存声明没有到期条件 |
| — | `unknown-class` | — | 引擎发出的类别名不在上表：这是一条**发现**，不是一个新的类别 |

`unknown-class` 不是第九类：它是本表被违反时的**报告形**，因此不出现在 `--emit-categories` 的集合里。

### 四个结构类（`contracts/detection-categories.contract.md` C-103）

| 类别 | 判据（程序可读的读物） | 证据义务 |
|------|----------------------|---------|
| `superseded-live` | 一个正文被标记（或其语义被判断）为被取代，而它仍然被**活守卫**按旧行为断言；或该正文缺少指向新载体的指针 | 条目 MUST 同时点名**正文的 path:line** 与**守卫的 path:line**；两者缺一即「两处只报了一处」 |
| `multi-owner` | 同一名称 / 常量 / 计数在同一轴上出现两处独立定义（不是指针引用），且两处值可被并排读出 | 条目 MUST 点名**两处**并同时给出**两个值**；只报一处或只报一个值不算命中 |
| `orphan-path` | 一处被引用的路径（`<spec-dir>` 相对 / 仓库相对 / 反引号包裹）在树上不可解析 | 条目 MUST 点名**引用处的 path:line** 与**缺失的目标路径** |
| `renumber-live-binding` | 活绑定的四形态之一：权威文件的特性编号、任务头部的编号、团队目录名与 slug、契约头部的特性编号、特性引用文件的绑定行、注册表行 | 条目 MUST 点名 file:line（团队目录形态点名该目录） |

### 四个状态类

| 类别 | 判据（程序可读的读物） | 证据义务 |
|------|----------------------|---------|
| `status-unreadable` | 见 § Status Readability：四个可读对象之一为红 | 条目 MUST 点名特性 id 与缺失 / 矛盾的字段名，而非只写"不可读" |
| `false-closed-set` | 一处被声明的封闭集恒等式（例如 `applicable + exempt == candidates`）两侧可复算而不相等 | 条目 MUST 同条给出**两侧读数**；"声明了闭集但从未有人复算"本身是一条发现 |
| `stale-constant` | 同一常量两处当前值不同，且其中一处不是值 owner（值 owner 在 `.specify/scripts/python/` 的模块常量或声明层） | 条目 MUST 点名两处、两个值与 owner |
| `deferral-marker` | 一处留存声明的字面（"暂时保留"／"留待下轮"／"以后再处理"及其英文对应），且该行没有任何到期字段 | 条目 MUST 点名 path:line 并引用该标记的原文 |

### `deferral-marker` 没有语料行，必须由构造证明（C-106）

A–H 语料从未专门查找留存措辞，因此**没有任何一条语料命中本类**（`.specify/specs/092-non-disposable/plan.md`
§ A–H Corpus Mapping 的 two-way check 已记录该缺口）。本类 MUST 由守卫自身的 fixture 证明：一个说
"保留到下一轮再处理"、无到期条件的正文 → 红；同一条加上 `expiry_kind: on-review` + `expiry_recheck` → 绿。
不得因为语料里没有它，就把本类从封闭集里读成"没这回事"。

### 每个类别一条变异腿（C-107 / C-106 的守卫义务）

对封闭集里的**每一个**类别，守卫 MUST 含一条变异腿：在副本树上造出该缺陷，断言引擎转红并点名期望的
path:line；再加一条反向腿（把副本树修好，断言转绿）。只有绿没有红的类别，不满足本节的义务——
**一个不会变红的绿不是证据**。

### 一个什么都没找到的类别要说出来（C-108）

引擎 MUST 能按类别报 `count: 0`，并**同时**给出它所搜索的根集合。沉默不等于零：一个类别在本树上的
"零"，是"在这十个根上、用这条判据、一条都没命中"这个可复核的结论，而不是"报告里没有这一节"。

## Detection Subject

**判定主体封闭两值**（FR-004）：`deterministic` / `semantic`。这两个词与 `sanitize-utils.py` 的 `DETECTIONS`
同名同义，按指针引用，本文档不另造词。

| 取值 | 断言对象 | 由谁判定 |
|------|---------|---------|
| `deterministic` | 文件 / 行 / 字段 / 字面量 / 计数 / 路径 / 可解析引用 | 只读检出引擎 |
| `semantic` | 一个只有在理解了自然语言断言的含义之后才成立的命题（谁在语义上取代了谁、两处独立陈述是否说同一件事） | subagent，且条目 MUST 携带**两处**路径 + 行号 |

分界只由**断言对象**决定，不由跑得快不快、由谁发现决定。MUST NOT 由语义判定产生一个自称 `deterministic`
的条目；MUST NOT 把一个本可程序复算的命题推给语义面。

## Review Surface

**回顾面恰为当前 `git HEAD` 工作树里 `.specify/` 下的十个历史根**（FR-036）：

```text
.specify/archive  .specify/derive  .specify/goal  .specify/history  .specify/memory
.specify/project  .specify/review  .specify/specs  .specify/state  .specify/teams
```

成员与次序由 `.specify/shared/declarations/facts/non-disposable-review-surface.yaml#/statement` 拥有
（`kind: closed-set`），引擎经 `.specify/scripts/python/declaration_reader.py` 读出；本节**不复述**那十个字符串作为
第二个定义点，只负责说明它们的语义与边界。

**边界一：回顾不读 git 历史。** 不看 commit、不 blame、不 diff 旧版本。只在 git 历史里存在的旧措辞 MUST
产生零条目（SC-002）。理由：本文档要管的是"树上现在有什么"，而不是"曾经有什么"；把 git 历史纳入回顾面，
会让回顾面对一棵永远在长大的输入，而结论永远无法在同一棵树上复现。

**边界二：回顾面是一个封闭集，不是一个前缀匹配。** 一个已声明却缺席的根 MUST 被逐根点名，并按原因排除出
候选集（MUST NOT 计为 `0`）；一个存在但未声明的兄弟目录 MUST 只产生一条提示，MUST NOT 扩大候选集。
判据是三次与声明集合 `S` 的比较（`contracts/detection-engine-cli.contract.md` C-605），MUST NOT 是
"名字看起来像不像某个根"——那会用被测物定义测试。

**边界三：候选是文件，不是结论。** 覆盖声明给出的候选计数 MUST 与一次独立枚举（逐目录 `rglob` 计数）一致；
该基线是**参照物，不是阈值**（SC-014）。

## Status Readability

**「状态不可读」不是"我没看懂"，而是一处被声明的状态与它据以成立的读物矛盾，或该读物缺一个必需字段**
（FR-025–FR-028）。本节拥有**矛盾表**这一件东西；状态值域、闭环裁决与 reason code、验证词表与 smoke 字段、
决定张力记录的形态，**不**由本节拥有，按下面的表以指针引用（宪法 XIV）。

| 读的是谁的域 | 所有者 |
|-------------|--------|
| 注册表状态值域（`Draft` / `Planned` / `Implemented` / `Blocked` / `Ready for Review` / `Sealed` / `Completed` / `Relocated`） | `.specify/shared/workflow/feature-integration.md` § Status State Machine；载体声明在 `.specify/templates/feature-details-template.md` § Canonical Status State Machine |
| 闭环裁决（`accept` / `block`）与 7 个 reason code | `.specify/shared/workflow/acceptance-hardening.md` § Closure Verdict；实现于 `.specify/scripts/python/closure-acceptance-check.py` 的 `ARC_VERDICTS` / `REASON_CODES` |
| 验证词表与 smoke 字段名（`SC-NNN_status=` / `smoke_command` / `smoke_exit_code` / `smoke_evidence_path`） | `.specify/shared/workflow/acceptance-hardening.md` § Verification Vocabulary |
| 决定张力记录的六字段形态 | `.specify/shared/guidelines/decision-tension.md`；判据于 `.specify/scripts/python/validate-decision-tensions.py` |
| `**Path**:` 标记的位置与取值域 | `.specify/shared/workflow/acceptance-hardening.md` § Measurement Sources；判据于 `.specify/scripts/python/validate-requirements.py` 的 `path-marker` |

### 四个可读对象（C-801）

| # | 对象 | 从哪读 | 什么让它红 |
|---|------|--------|-----------|
| O1 | 注册表行 | `.specify/features.md` | 该行的状态与闭环裁决矛盾（见下表） |
| O2 | 验证记录的机器可读块 | `<spec-dir>/verification.md` | 缺逐条判据的机器可读块，或缺任一 smoke 字段 |
| O3 | 任务结构与决定张力结构 | `<spec-dir>/tasks.md`、`<spec-dir>/plan.md` | 一个用户故事标签出现在非故事相位；或一条决定张力记录不携带 owner 的六字段形态 |
| O4 | （独立一条，C-804）`requirements.md` 的 `**Path**:` 标记 | `<spec-dir>/requirements.md` | 由 `validate-requirements.py` 的 `path-marker` 判，**不**由本类判 |

O3 之所以是一个对象两个面：两个面回答同一个问题——"这个特性自己记录的形状，是不是它的 owner 要求的形状"——
且都从该规格自己的文件读。任一面红都产出一条 `status-unreadable` 条目，点名文件、行号与**缺失或畸形的结构元素**。

O4 之所以单列：`requirements.md` 的 `**Path**:` 标记是**需求侧的度量义务**，已经有它自己的判据
（`validate-requirements.py` 的 `path-marker`）与语料行（A6，`080-humanize-run-output`）。把它折进本类的谓词，
会让本类变成一个"所有规格文件都管"的兜底类，也就毁掉了本节存在的意义——**一处缺陷，一个类别**。本类对
A6 的义务恰是**不作断言**：它会要求引擎把需求侧读数作为 `evidence_refs` 带上，而不把它记成自己的命中。

### 状态 × 裁决矛盾表（封闭，C-802）

引擎 MUST 从上面两位 owner 读出状态值域与裁决值域，并且 MUST 只在下列标 ✗ 的格子里报矛盾。表是**封闭**的：
未列出的组合不是矛盾，引擎 MUST NOT 发明第三读法（例如"状态看起来旧了"）。

| 注册表状态 ↓ / 闭环裁决 → | `accept` | `block` |
|---|---|---|
| `Draft` | **✗ 矛盾**——还在草案的特性不算闭环 | 一致 |
| `Planned` | **✗ 矛盾**（语料 A3：`090` 读 `Planned`，闭环为 `accept`） | 一致——计划中的特性被阻断是正当的 |
| `Implemented` | 一致 | **✗ 矛盾**——reason code `status-claims-implemented-but-blocked` |
| `Ready for Review` | 一致 | **✗ 矛盾**——reason code `status-claims-implemented-but-blocked` |
| `Sealed` | 一致 | **✗ 矛盾**——reason code `status-claims-implemented-but-blocked`（封装即声明全部 final 判据已过） |
| `Blocked` | **✗ 矛盾**——注册表记了一个检查器看不见的阻断 | 一致，且为绿 |
| `Completed` | 一致 | **✗ 矛盾**——闭环为 `block` 的已完成特性 |
| `Relocated` | **不是活行**——按名排除，报 `count: 0` 并记录理由 | 同左 |

**`Relocated` 按名排除**：一行搬迁走的记录没有自己的活规格目录，也就没有可比的闭环裁决。引擎 MUST 为该状态
报 `count: 0` **并**给出理由，MUST NOT 把它折进"一致"列当作默认值。它不是假设：`.specify/features.md`
今天恰有**一行**（`048`）携带该状态，因此这条排除需要规则，而不是一句顺带提及。

**reason code 的归属**：闭环引擎只有**一个**与状态相关的 code（`status-claims-implemented-but-blocked`），
且只对三个**完成声明**格（`Implemented` / `Ready for Review` / `Sealed`）发出。其余 ✗ 格（`Draft` / `Planned` / `Blocked` /
`Completed`）在闭环集合里没有 code，也 MUST NOT 得到一个发明出来的 code：引擎以**空** `reasons` 列表发出，
把两侧读数（注册表行、检查器调用身份）放进条目自己的 `evidence_refs`。为它们新造第二个 code 被 C-205 禁止——
一个需要新词汇词的状态读数，是一次 owner-page 问题，不是一个引擎字符串。

### 三条禁止

1. 引擎 MUST NOT 比较一个拼写不在 owner 值域里的状态。未知拼写是**输入错误**（退出码 `2`，点名该行），
   永不是静默的"一致"——一个因为没人认得它而一致的取值，正是语料 A1 所记录的失败。
2. 引擎 MUST NOT 把 `Completed` / `Relocated` 当成上面那一条按名排除之外的"不在范围内"。一条 `Completed` 行
   配上 `block` 裁决，正是本类要报的"关了两次"。
3. 引擎 MUST NOT 读第三个裁决值。`ARC_VERDICTS` 若增长，本表就不再可判，守卫 MUST 失败而不是猜，直到本节
   按 owner 修订。

### 每一格要么有语料行，要么有一条具名的构造腿（C-803）

现有语料覆盖 `Planned × accept`（A3）、`Implemented × block`（A1）与 `Ready for Review × block`（同一 A1 家族）；
其余格子（`Draft × accept`、`Blocked × accept`、`Completed × block`，以及各"一致"格）MUST 由守卫自己数据里的
**fixture 树**证明，让缺失的语料覆盖对下一位读者保持可见，而不是被读成"已齐"。

**语料落在表的哪一侧很重要。** 一棵**冲突 fixture**（正文说 `Planned` 而实情已闭环）MUST 在该格转红；
一棵**一致 fixture**（说 `Planned` 而实情也未开，或说 `Implemented` 而实情已闭环）MUST 转绿，报它红才是缺陷。
把一致的行逼红不是覆盖，是误报。

A3 是承重的那一行：`090-re-anchoring` 的注册表行读 `Planned`，而 `closure-acceptance-check.py --json` 返回
`accept`、4/4 `final` 路径判据通过。C-802 之前引擎对这一对没有读法，A3 只能被描述、不能被判定。守卫 MUST
含"A3 落**红**"的读数，而不只是"状态不一致"的描述。

### 一个状态读数的复现义务（C-206）

每条 `status-unreadable` 条目 MUST 在 `evidence_refs` 里带上检查器调用的不变量（检查器的路径 + 特性 id），
使读者能用一条命令复现该裁决；读数 MUST 与运行次序、与回顾的并发度无关。**消费而不是重算**（C-207）：
守卫 MUST 用一棵桩替换检查器，断言引擎报出的是**桩**的裁决；引擎若仍报树上真实裁决，说明它自己重算了一遍，
该腿 MUST 失败。

## Disposition Set

**处置集是封闭四值，只有一个 owner（本节）**（FR-008）：

| 处置 | 含义 | 落盘形态 |
|------|------|---------|
| `archive` | 移入目的地并留下指针；目的地是封闭二形：退休 → `.specify/archive/`；分片归档 → 所属父 spec 的 `slices/` | 一次移动（`git mv` 语义），见 § Disposal Pathways |
| `supersede` | 由新载体承担；旧载体被标记为被取代并指向新载体 | 旧文本保留 + 标记 + 指针，见 § Supersede Protocol |
| `correct` | 就地修正正文 | 正文编辑 + 前后读数 |
| `exempt` | 显式豁免：写下理由 + 到期条件/复核时点 | 见 § Exemption |

集合 MUST 只在本文档定义；引擎、命令模板、技能、契约 MUST 引用它，MUST NOT 内联第二份成员表。守卫 MUST
通过本文档读出四个成员拼写，MUST NOT 从引擎或契约里的一个字面表读。

**`archive` 的目的地是封闭二形**：退休 → `.specify/archive/`（归 `/speckit.sanitize` 的归档 lane）；
分片归档 → 所属父 spec 的 `slices/<原分片目录名>/`（归 `/speckit.seal` 的 `archive-apply`）。目的地 MUST
只取这两形，MUST NOT 出现第三个目的地；分片归档不是退休，MUST NOT 写入 `.specify/archive/`，退休归档也
MUST NOT 被读作分片归档。四值集合不变：本次只原地扩展 `archive` 的目的地形态，MUST NOT 新增第五个处置值
或第二份词表。

### 被拒绝的取值（C-302）

以下取值**全部是发现**，不是处置：`null`、空串 `""`、`keep`、`leave`、`none`、任何自由文本。引擎 MUST 把它们
作为 `state: open` 发出并以非零退出码报出。不存在 `kept-as-is` 成员，也不存在"已由人工看过"这种闭合。

**"什么都不做"不是一种处置**：它是一个尚未作出的决定，而本文档的全部意义就是让这个决定无处藏身。

## Exemption

`exempt` 是唯一一种"不修也能留"的形态，代价是它**必然到期**（FR-006 / FR-007 / D-4）。

### 四个必填字段（C-303）

| 字段 | 内容 | 拒绝形态 |
|------|------|---------|
| `reason` | 为什么现在不修 | 裸否定不是理由：`N/A` / `n/a` / `none` / `-` 被拒绝 |
| `expiry_kind` | 封闭三值：`on-date` / `on-condition` / `on-review` | 第四个值不存在，也没有 "permanent" |
| `expiry_value` | `on-date` / `on-review`：绝对日期 `YYYY-MM-DD`；`on-condition`：一个具名谓词 + 其判据指针 | 常量真条件（`condition: true` 及其同义形）被拒绝——它是**无效**的到期条件，不是"仍然有效" |
| `expiry_recheck` | 强制复查日期，绝对 `YYYY-MM-DD` | 相对日期被拒绝；上限由本节给出（见下） |

缺任一字段即该处置**不成立**：条目留在 `open`，报告点名缺失的字段名（SC-017）。

### 到期语义（C-304）

| `expiry_kind` | 何时重新打开该条目 | 读物 |
|---|---|---|
| `on-date` | 今天 ≥ `expiry_value` | 日期比较 |
| `on-review` | 今天 ≥ `expiry_recheck`，**即使条件仍然成立** | 日期比较——这是反同义反复的那条腿 |
| `on-condition` | 谓词求值为 `false`，**或谓词根本无法求值** | 引擎的一次求值；不可求值 → `unevaluated`，绝不是"仍然有效" |

`expiry_recheck` 的上限 = `expiry_value` 之后 **365 天**（`on-review` 时即 `expiry_value` 本身）。上限存在的
理由：一个复查日期远在其到期之后，等于把"到期"这件事再推迟一次。

到期后该条目 MUST 重新进入未处置集合，且报告 MUST NOT 自称闭合。**不存在静默续期**：给一条已到期的豁免
写一个新日期而不重新确认，是非法迁移（`data-model.md` § Entry State Machine），不是一次豁免。

## Disposition Bridge

Non-Disposable 的处置集（本节上面的四值）与材料卫生的处置集（`.specify/scripts/python/sanitize-utils.py` 的
`DISPOSITIONS`，五值：`delete` / `archive` / `repair` / `delegate` / `dismiss`）**是两个各自封闭、互不合并的
集合**（FR-012 / FR-013 / D-1 / OI-2）。它们之间只有三件东西：一张逐值映射表、一张不可映射项表、一条裁决
规则。

为什么不合并：`delete` 与 `exempt` 在本特性里分别是**禁止**与**必须带到期条件**；把"材料卫生可删除"与
"历史证据不可删除"塞进同一个词表，会让这两条相反的约束共用一个词。

### 表一：逐值映射（`maps-to`）

行 = ND 处置（4）× 列 = sanitize 处置（5），**每一对都 MUST 命中本表或表二中的恰好一行**（SC-015）。
`delete` 一列在 ND 侧没有任何映射目标：本特性**不允许**把任何载体删除（§ Disposal Pathways）。

| ND ＼ sanitize | `delete` | `archive` | `repair` | `delegate` | `dismiss` |
|---|---|---|---|---|---|
| `archive` | unmappable | maps-to | unmappable | unmappable | unmappable |
| `supersede` | unmappable | maps-to | maps-to | unmappable | unmappable |
| `correct` | unmappable | unmappable | maps-to | unmappable | unmappable |
| `exempt` | unmappable | unmappable | unmappable | maps-to | **prohibited** |

三格需要说明，其余由表二承接：

- `supersede × repair`：一次取代必然就地修一次旧正文（加标记与指针），所以 sanitize 的 `repair` 覆盖这一对的
  "就地修改"那一半；"旧文本保留 + 指针"那一半只有 ND 侧表达得出。映射不是等价，是两套词表下各自的最近表达。
- `exempt × delegate`：两者都是"交由另一面处理"，但 `delegate` 无到期条件、`exempt` 必然到期；理由同上。
- `exempt × dismiss`：**禁止**（见下面的第二条禁令）。

### 表二：不可映射项与承接面（`unmappable`）

上表每一格 `unmappable` / `prohibited` 都要在这里有一行，且 MUST 点名它的承接面：

| ND 处置 | sanitize 处置 | 承接面 | 为什么不可映射 |
|---|---|---|---|
| `archive` | `delete` | `disposal-pathways`（本节 § Disposal Pathways） | 归档是**移动**；删除不是处置，任何一门语言里都没有对应词 |
| `archive` | `repair` | `supersede-protocol` | 归档不修改内容，"就地修正"是另一个动作 |
| `archive` | `delegate` | `handoff-rows` | 移交改变的是负责人，不是位置 |
| `archive` | `dismiss` | `handoff-rows` | `dismiss` 的含义是"判定为无需处置"，与"移走"相反 |
| `supersede` | `delete` | `supersede-protocol` | 取代要求旧文本**保留**，删除使它消失 |
| `supersede` | `delegate` | `handoff-rows` | 移交不产生"新载体承担旧内容"这一关系 |
| `supersede` | `dismiss` | `handoff-rows` | 同上，且 `dismiss` 不建立指针 |
| `correct` | `delete` | `disposal-pathways` | 修正修改文本，不移动它 |
| `correct` | `archive` | `disposal-pathways` | 同上 |
| `correct` | `delegate` | `handoff-rows` | 同上 |
| `correct` | `dismiss` | `handoff-rows` | 同上 |
| `exempt` | `delete` | `exemption` | 豁免保留载体；删除消灭载体 |
| `exempt` | `archive` | `exemption` | 豁免保留在原位 |
| `exempt` | `repair` | `exemption` | 豁免的全部意义是现在不修 |
| `exempt` | `dismiss` | `exemption` | **禁止**：`dismiss` MUST NOT 被读作"延期"，见下 |

行数是两个集合长度的**笛卡尔积**（4 × 5 = 20），由构造决定；这个数字不写在这里——守卫在测试时从两个集合
的长度算出它，并断言两张表合计恰好那么多行、且没有重复对。

### 两条显式禁令（C-306）

1. **`exempt` 在材料卫生集里没有对应值**：一个卫生候选 MUST 被处置，MUST NOT 被豁免。卫生面处理的是
   "该不该留"，豁免处理的是"历史证据现在不修"，两者不可互换。
2. **`dismiss` MUST NOT 被读作"延期"**：它的含义是"判定为无需处置"，与"尚未处置"相反。因此它 MUST NOT
   被映射到 `exempt`。

### 唯一裁决规则（C-307）

> **同一个候选被两个引擎同时看见时，由检出它的那个引擎决定处置词汇。**

这条规则 MUST 只在本文档出现一次，两个引擎 MUST 各自引用它。它回答的是一个具体问题：一条既被材料卫生
引擎报为候选、又被本特性判为过期的载体，**只被处置一次**——处置它的那套词表就是报出它的那套。
"同一候选被处置两次" MUST 可被机械证伪（一条变异腿），而不只是被劝阻。

## Disposal Pathways

处置只有下面四条落盘通道（FR-034 / FR-052 / FR-058）：

| 处置 | 通道 | 可逆性 |
|------|------|--------|
| `archive` | 一次移动：源路径 → 归档路径，映射记入处置记录 | 单条 `git` 命令可逆 |
| `supersede` | 旧文本保留 + 被取代标记 + 指向新载体的指针，三处同批 | `git checkout -- <path>` 可逆 |
| `correct` | 就地编辑 + 前后读数 | `git checkout -- <path>` 可逆 |
| `exempt` | 无需落盘改写：豁免记录本身就是产物 | 无需逆转 |

**没有批量删除通道，没有批量改写通道。** 一次运行可以在组边界上按组写盘，但 MUST NOT 存在"一次操作改动
N 个互相无关的载体"的通道。

### 归档是一次移动（C-308 / C-507）

`archive` MUST 是一次**移动**（`git mv` 语义）：处置记录 MUST 携带 `moved = {from, to}`，被取代的文本 MUST
保留在归档位置，`git status --porcelain` MUST 显示一对重命名，MUST NEVER 显示一次删除。`irreversible` 只
在路由判定该移动无法仅凭记录逆转时取 `true`，其余一律 `false`。

**删除从来不是一种处置**（FR-034 iv）：本文档不提供删除通道；一个载体"不再有用"的结论，其正确出路是归档。

### 分片归档的处置记录

分片归档（目的地 = 所属父 spec 的 `slices/`，见 § Disposition Set）的处置记录是**所属父 spec 的
`archive-manifest.json` 的逐片 `{from, to}` 行**：每个被归档的分片一行，`from` 为归档前的分片目录路径，
`to` 为 `slices/` 内路径；清单每个父 spec 一份，与 `merge-manifest.json` 并列。MUST NOT 另建第二份处置
记录，MUST NOT 在 `seal.md` 或其他回执里复述移动对；清单的字段集、摘要与校验义务由
`100-seal-slice-archive` 的 `contracts/archive-manifest.contract.md` 拥有（按指针引用，本节不复述）。

## Supersede Protocol

当一条特性取代另一条特性的正文、守卫或证据路径时，取代方 MUST 回收**三个落地面**（FR-015 / C-501）：

| 落地面 | 回收内容 | 未回收的形态 |
|--------|---------|-------------|
| **正文** | 旧文本**保留**，加被取代标记，加指向新载体的指针 | 旧文本仍在以"当前有效"姿态陈述，或指针缺失 |
| **守卫** | 旧行为的断言被替换或移除 | 守卫仍按旧行为断言（"被取代的正文被活守卫断言"） |
| **证据路径** | 旧拼写保留一条指针，不保留第二份真相 | 同一证据路径出现第二种拼写，两者都当自己是对的 |

**两个落地面修好、三处只修两处**就是本节要检出的缺陷。

### 不完整回收是可机械检出的（C-502）

一处被标记为被取代的正文，若其守卫仍按旧行为断言、或缺少指针、或其证据路径存在第二种拼写，MUST 报红并
点名 path 与 line。守卫 MUST 为**每个落地面**各含一条变异腿（副本树上转红，同步回收后转绿）。

### 取代登记是一份可读记录，不是会话笔记（C-503）

一次取代 MUST 记录在本节的行形态里，可被引擎读出：

| 字段 | 内容 |
|------|------|
| `superseded` | 旧载体的 `{path, line}` |
| `superseded_by` | 新载体的 `{path, line}`——可解析，否则该行是一条悬空指针的发现 |
| `disposition` | 按定义恒为 `supersede` |
| `evidence` | 证明三个落地面都已回收的修复证据路径 |
| `guard_status` | `retired` / `replaced` / `unchanged-with-reason` |

只存在于一次 commit message 或一段会话记录里的取代，MUST NOT 满足本节；该情形下守卫 MUST 失败。

## Renumber-Face

**活绑定 MUST 跟随目录的实际编号**（FR-022 / C-504）。一节文件的"实际编号"是它所在 spec 目录名的前缀。

### 活绑定的四种形态

| 形态 | 位置 |
|------|------|
| 权威文件的特性编号 | `requirements.md` 头部的 `**Feature ID**` |
| 任务 / 契约头部的编号 | `tasks.md` 的 `**Requirement ID**` 与 `**Related Feature**`；契约文件头部的 `**Feature**:` |
| 团队目录名与 slug | `<spec-dir>/team/<NNN-slug>/` 的目录名与其 `name:` / `slug:` 行 |
| 特性引用文件的绑定行与注册表行 | `feature-ref.md` 的绑定行；`.specify/features.md` 的该特性行 |

不一致 MUST 报红并点名 file:line（团队目录形态点名该目录）。

### 历史记录 MUST NOT 被改写（FR-023 / C-505）

一条历史记录**记录的是当时发生的事**；把它改写成新编号，会让"当时"这件事消失。判据面分成两条**具名腿**，
因为它们的成员被两种不同的方式寻址：

**腿一 — 按路径寻址的记录。** 取自 `.specify/scripts/python/renumber-utils.py` 的既有谓词，MUST NOT 新造一个
"看起来像历史"的启发式：

- `EXCLUDED_PREFIXES` — `.specify/history/`、`.specify/archive/`、`.specify/specs/.archive/`
- `MACHINE_PREFIXES` — `.specify/memory/sanitize/`、`.specify/memory/retention/`、`.specify/memory/renumber/`
- `EVIDENCE_SEGMENTS` — `test-evidence`
- `DATED_RE` — 日期命名的文件

这四项只覆盖**路径**。

**腿二 — 按章节寻址的记录，任何路径谓词都覆盖不到。** `## Clarifications` 块是一段**活 spec 正文里的章节**，
而该正文本身正是重编号合法编辑的文件——所以腿一的路径谓词对它结构性失明，本节 MUST NOT 声称能覆盖它。
本腿的判据是**章节位置**：从 `## Clarifications` 这个标题起，到下一个同级 `##` 为止的全部内容；该章节文本
被移除、或其中一处编辑携带了一次重编号，即判红。这是本文档**唯一**拥有自己的谓词的一条腿，它的缺席会让
本节比它自己的措辞更弱。

### 一份判据实现，两侧引用（FR-024 / C-506）

引擎 MUST 从 `.specify/scripts/python/renumber-utils.py` 消费上面四个谓词（import 或记录在案的 subprocess），
MUST NOT 携带 `EXCLUDED_PREFIXES` / `MACHINE_PREFIXES` / `EVIDENCE_SEGMENTS` / `DATED_RE` 的第二份字面。
守卫 MUST 断言引擎模块内没有这四个字面的副本；一条变异腿改动判据模块，并期望引擎的分类随之移动。

## Report Entry

一条条目 = 一次回顾产出的、由一次处置关闭的单元。**字段集**由 `.specify/specs/092-non-disposable/data-model.md`
§ E-1 拥有；本节只固定**序列化义务**（`contracts/report-schema.contract.md` C-703）。

| 字段 | 序列化规则 |
|------|-----------|
| `entry_id` | **合并键**：`<category>/<normalised path>:<line>`；两条同 id 的条目 MUST 被引擎合并，MUST NEVER 发出两次 |
| `path` | 仓库相对，按 `declaration_reader.normalize_path` 归一（剥离一个可选的前导 `.specify/`） |
| `line` | 1 起始；`0` 保留给"整个文件"这一事实（缺机器可读块是文件级事实，不是行级事实） |
| `evidence_refs` | 至少一个元素；`detection: semantic` 的条目至少**两个** |
| `detection` | 本档 § Detection Subject 的两值之一 |
| `state` | `data-model.md` § Entry State Machine 的取值之一 |
| `disposition` | 仅当 `state: disposed` 时取本档 § Disposition Set 的成员；其余一律 `null` |

**`semantic` 条目的证据下限**：两处可解析引用（路径 + 行号），因为一个语义判断只有在一处被独立复核时才
是一个可复核的结论，否则只是一个说法。

## Report Envelope

报告是一个**单一内存运行**的两次投影（`contracts/report-schema.contract.md` C-701 / C-702）：`--json` 文档与
人读 stdout。人读形态 MUST NOT 引入 JSON 没有携带的字段、计数或结论。

### 覆盖声明是报告的第一块，永远

每份报告 MUST 以覆盖声明开头，无论是否存在候选：十个根**按声明次序**逐根给出存在性与计数；候选总数；
带原因的排除项；缺席的根；未登记的兄弟目录（提示）；声明文件的路径与状态。**有发现却没有覆盖声明的报告是
无效报告**；候选集为空时 MUST 明确说出这个结论，且 MUST NOT 说 `closed: true`。

### 四个读者问题（C-705 / C-706）

报告 MUST 让一个没有参与这次运行的人回答下面四个问题，而不必打开另一个工件：

1. **你看了什么？** —— 覆盖声明，按声明次序，缺席的根被点名。
2. **你发现了什么？** —— 每条：在哪（path:line）、哪一类、证据多强、由程序还是由阅读判定。
3. **你建议怎么做？** —— 每条：一个处置、它会触及哪些路径、能不能撤销。
4. **还有什么没做？** —— `open` / `unconfirmed` / `unevaluated` 的计数，写成**未闭合**，MUST NOT 折进一句
   "已完成"。

设计段的面向读者的四个回答**复用同一组答案**，MUST NOT 发明第五种形态。

### `closed` 是推导值（C-704）

`closed` MUST 是推导的：任一 `open` / `unevaluated` / `unconfirmed` 条目存在，或任一片 `unevaluated`，
`closed` 即为 `false`。报告 MUST NOT 携带"已被人工看过"或"原样保留"这类字段——它们不是状态，也不是处置。
`unevaluated` 条目与 `unevaluated` 片 MUST 以**计数且可见**的状态出现，并计入"未闭合"总数。

## Engine Contract

引擎是 `.specify/scripts/python/non-disposable-check.py`，`.specify/scripts/python/` 下一族只读引擎的兄弟
（`sanitize-utils.py`、`closure-acceptance-check.py`、`renumber-utils.py` 的形态）：单文件、stdlib、
`main(argv=None) -> int`。

### 根集合只从声明层读（C-605 / C-608）

引擎 MUST 经 `.specify/scripts/python/declaration_reader.py` 读出十个根、它们的次序与计数，MUST NOT 内联一份目录
字面表。声明缺失 → 退出 `2` 并点名缺失路径（绝不是"零候选因此全绿"）；声明的 `kind` 或必填键无效 → 退出 `2`
并点名冒犯的键；一次降级读取复用 `STR-014` 标签，MUST NOT 新造标签。

### 参数集（C-604）

参数恰为八行，多一个都没有；未识别的选项退出 `2`：

| 参数 | 含义 | 必填 |
|------|------|------|
| `--root PATH` | 仓库根（缺省：由引擎自身位置解析） | 否 |
| `--json` | 机器可读报告到 stdout | 否 |
| `--scope SHARD` | 只判落在该片里的候选（可重复；片号见下式；它划分的是**文件集**，永不是类别集） | 否 |
| `--roots` | 打印声明根集合（路径、存在性、计数）并以 `0` 退出，不判候选 | 否 |
| `--emit-categories` | 以 JSON 打印封闭类别集并以 `0` 退出，不判候选 | 否 |
| `--declaration PATH` | 覆盖事实文件（供 fixture 使用）——指向另一面的**唯一**方式 | 否 |
| `-h`, `--help` | 用法 | 否 |
| `--version` | 版本行 | 否 |

**动作与参数是两个计数，且都不是"三个"。** 动作 = 打印后停止、不判候选的选项，恰为两个
（`--roots`、`--emit-categories`）；参数 = 上表的八行（`-h`/`--help` 算一行，`--version` 算另一行）。
第三个动作不存在：`--version` 是脚本接口的回答，不是回顾动作。

### 退出码三值（C-603 / C-607）

| 退出码 | 含义 |
|--------|------|
| `0` | 在一个被声明的、非空的面上没有任何发现 |
| `1` | 存在发现（任何条目、任何类别，含 `unevaluated` 条目） |
| `2` | 参数或环境错误——含声明缺失 / 无效、根不可解析、未知选项 |

**空候选集只有一个退出码，本节是它唯一的陈述：`2`。** 读法是"你给我的这个面一个候选都没声明"，这是
环境 / 声明缺陷，不是一个裁决；引擎退出 `2`、点名声明路径、并打印 `candidates: 0` 的覆盖声明。`0` MUST NOT
在空面上可达（"空候选"与"全绿"是两个不同的结论），`1` MUST NOT 在空面上可达（零候选上的发现计数是算术，不是
证据）。

### 分片（C-606）

```text
shard_id = "s{index:03d}-of-{n:03d}"
index    = 该片在 sorted(range(n)) 中的序号
n        = 本次运行请求的片数
assignment: sorted_paths[i] -> index (i mod n) 的 shard_id
```

三个可直接判定的后果：

- 片数 `n` 是**运行**的属性，不是树的属性；同一棵树在两个 `n` 下得到两个不同的划分，两者都合法。MUST NOT
  改变的是按 `entry_id` 的条目集，只有它的分布变了。
- 片号**命名划分**，从不命名内容；不同 `n` 会给同一路径不同的片号，消费者 MUST NOT 仅凭片号缓存任何东西。
- 一个空片是运行错误（退出 `2` 并点名请求的 `n`），永不是一份空报告。

分片 MUST 把每个候选恰好分到一个片；各片之并 MUST 等于候选集。

### 确定性（C-607）

同一棵树的两次运行 MUST 产生逐字节相同的 `--json`（移除运行标识之后）：条目按 `entry_id` 排序、根按声明
次序、映射按 key 排序。

### 零写盘与投射（C-602 / C-608）

引擎在任何模式下 MUST NOT 在仓库内写盘——含 `--json`、`--scope`、`--help` 与每条错误路径。唯一允许的写入
位置（若将来某个模式需要暂存）是 `.specify/.tmp/`（已 git-ignored）并在退出时清除；今天没有任何模式需要它。
经 `.specify/scripts/python/` 镜像调用时，引擎 MUST 把仓库根解析为 `.specify` 的父目录，永不是 `.specify` 本身。
`.specify/scripts/python/non-disposable-check.py` 由 `.specify/scripts/python/sync-mirrors.py` 生成、MUST NOT 手改。

## Capture Rule

**任何一次「与改动前对比」的断言，MUST 先有一次改动前的读数。** 没有前置读数的"改好了"是自述，不是证据
（宪法 IV / C-401）。执行段（或任何要改树的动作）在动第一个字节之前 MUST 取下面四项读数，并原样记下**命令
与原始输出**：

| # | 读数 | 命令 | 它挡住什么 |
|---|------|------|-----------|
| 1 | 镜像基线 | `python3 .specify/scripts/python/sync-mirrors.py --check` | 改动后若把镜像漂移报成"新发现"，其实是改动前就有 |
| 2 | 指令面字节数 | `wc -c .specify/instructions.md` | 预算读数必须在改动前后同一把尺子下比较 |
| 3 | 两处宪法计数 pin | `grep -c '^### ' .specify/constitution.md` 与 `.specify/templates/constitution-template.md` | 本次不新增原则；两个数若不等于改动前，说明洞开了未授权范围 |
| 4 | 工作树形态 | `git status --porcelain` | 既有脏文件不算本特性的产出，MUST NOT 被提交或还原 |

四项读数 MUST 落在 `test-evidence/` 的**当次运行证据文件**里（C-408 的第 (i) 段），与改动后的同四项读数并排；
"前后一致"与"前后变化且变化被解释"都是合法结论，"无从比较"不是。

**基线是参照物，不是阈值**：失败测试的基线是一份**node-id 名单**（不是计数），门 GATE-1 比对的是名单里
每一个 id 在改动后是否仍然失败；一个计数不变而名单换了，是回归，不是稳定。

## Handoff Rows

**档 II 移交是一件交付物，不是一次延期**（FR-056）。它是一行标记，落在承接正文里缺陷所在的位置：

```text
<!-- 092 handoff: <语料编号> → <承接特性> -->
```

本节拥有**行**（哪个语料编号去哪个承接正文），标记的字面形态、守卫载体与它被计在哪个数下由
`.specify/specs/092-non-disposable/plan.md` § Shift List 拥有（C-805），本节只给指针、不复述第二个字面副本。

### 义务（每条可判定）

- **形态**：每个承接正文**恰一行**。语料编号 MUST 属于档 II 集合；承接特性 MUST 是 Shift List 点名的那一个。
  零标记、一个正文上两行、编号在档 II 集合之外、承接特性与 Shift List 不一致——都是发现。
- **落点**：承接正文都在本特性目录**之外**。标记由本特性 P7 落到承接正文（一次跨行写，其许可由团队
  `write_carve_outs` 按标记行收窄记录），或在那个正文自己的行里记录落地——这一选择在 Shift List 撰写时作出、
  记在 `team/092-non-disposable/team.md` § Handoff boundary，MUST NOT 留到实现期临时决定。
- **不改正文**：本特性 MUST NOT 改写任何档 II 正文。标记之外一个字都不动；修复本身留在那条特性线（FR-056）。
- **计数**：标记数 = 承接正文数 = Shift List 行数。三个数一起走，且 MUST 相等。

### 三个数，以及它们为什么不同

| 数 | 数的是什么 | 出处 |
|---|---|---|
| **19** | 档 I 语料的**条目**（A1–A6、B1–B5、C1–C4、G1–G3） | 本特性就地闭合，**一行标记都不落**（DoD-4 点名） |
| **15** | 档 II 语料的**条目**（D1–D6、E1–E6、F1–F5、H1–H2） | 每一条都必须抵达一条承接行 |
| **12** | **Shift List 行数** = 不同**承接正文**数 = 落下的标记数 | 映射在行上多对一：`081` 承载 D1+D2、`084` 承载 D3+E5、`090` 承载 D5+F2、`083` 承载 E1+E2+E3+F5、dated-bodies 行承载 F1+F3 |

所以交付数是 **12 行标记**；落 15 行就是落了三行重复——**一个承接正文一行**，不是一条语料一行。
要拒绝的算术是"15 条语料，所以 15 行标记"。一个数在没有自身理由的情况下变动，是一条发现，不是一次整理。

## Boundary with Sanitize and History

**两个同类引擎、两套处置词汇、一条裁决规则。** 本节只说边界，不改任何一方的词汇表。

| | 材料卫生（sanitize，`045-sanitize-command`） | 本特性（non-disposable） |
|---|---|---|
| 类别集 owner | `.specify/scripts/python/sanitize-utils.py` 的 `CATEGORIES`（6 值） | 本节所属文档 § Detection Categories（8 值 + `unknown-class` 报告形） |
| 处置集 owner | 同文件的 `DISPOSITIONS`（`delete` / `archive` / `repair` / `delegate` / `dismiss`，5 值） | 本节所属文档 § Disposition Set（4 值） |
| 状态集 | 同文件的 `STATES` | `data-model.md` E-1 的条目状态机 |
| 判定主体 | 同文件的 `DETECTIONS` | 本节所属文档 § Detection Subject（同名同义，按指针引用） |
| 回顾面 | 调用方给定的路径 | 声明层 `non-disposable-review-surface` 的十个根 |
| 写盘 | 按处置执行 | **零写盘**：只产出报告与建议处置 |

**唯一裁决规则**：同一个候选被两个引擎同时看见时，由**检出它的那个引擎**决定处置词汇。本特性 MUST NOT
把 sanitize 的 `delete` / `dismiss` 读成自己的处置，也 MUST NOT 让 sanitize 读本特性的 `supersede` / `correct` /
`exempt`。两套词汇之间的桥只在本节所属文档 § Disposition Bridge 存在，且是一张**封闭**映射表，不是一次翻译。

**与 history 的边界**：本特性把 `/speckit.history` 从"把会话蒸馏成主题文档"升级为四段
「回顾 → 设计（方案）→ 用户确认 → 执行」，但**四段的形态**由 `contracts/four-stage-command.contract.md` 与
`.specify/skills/internal/manage-history/SKILL.md` 拥有，本节不复述；执行段落下的产物仍是那份历史蒸馏，本特性不新建
第二个历史存储、第二个 `/speckit.history` 入口、第二套并发机制（FR-046 / FR-050 / FR-051 为 process-grade，
见 `contracts/acceptance-readability.contract.md` C-806）。

## Seam Bypass

**执行段触及的每一条路径 MUST 被一条 confirmed design row 点名**；未被点名的路径是红读数，不是一次顺手修复。
这条规则与 `contracts/four-stage-command.contract.md` C-407 的执行段规则是**同一条读数**（该契约 C-410 已如此
声明），本节不复述第二份判据：判据的固定权在该契约，读数的守卫载体是
`tests/contract/test_non_disposable_seam_bypass.py`。

- **named 与 confirmed 是两件事**：一条被点名但未确认的行不授权任何写入；守卫 MUST 分别翻转这两侧并各自转红。
- **既有 spec 正文、owner 文档或守卫的改动是一次 confirmed design item**，并 MUST 携带改动前后的读数——读数
  的取法归 § Capture Rule，本节只指向它，不复述四项。
- **路径的同一性按规范化后的拼写**：`./x`、`x//y` 与 `x` 是同一条路径；一个目录名只覆盖它自己，不构成子树授权。

## Relation to the Constitution

**本次未新增宪法原则，也 MUST NOT 新增**（clarify D-2）。理由：状态脊 `direction_contract.goal_verbatim` 的逐字
内容是理念陈述——「在 speckit 框架中引入『Non-Disposable』理念……需要时常回顾和修正……杜绝……将问题推到将来的
行为」——它不含"MUST 成为一条原则"或任何"宪法 / 模板 / 指令面"的规范性形态。宪法的修订是用户的显式判定权
（OI-4 保留该权），MUST NOT 从一个理念陈述里推定一个原话未记载的范围扩展（宪法 XVIII 的取名次序、宪法 VIII 的
权威次序都在同一方向上）。

因此本特性的落点是**七面**（FR-063）：本文档（owner，新）、声明层（新）、术语表四条、特性注册表行与详情、
既有守卫（`bash .specify/scripts/bash/run-tests.sh -m contract`）、三份历史面的**指针行**（只加一行，MUST NOT 新增常驻顶级 `##` 章节，否则
宪法模板 35 / 现网 36 的计数 pin 抖动）、`register.md` 决定条目。两条宪法计数 pin **保持原值**。

本特性与既有原则是**承接**关系，不是新原则：

| 既有原则 | 本节所属文档如何承接它 |
|---|---|
| XIV One Source of Truth | 本文档是 Non-Disposable 各封闭集的唯一 owner；其他位置只以"摘要 + 路径"引用（宪法 XIV 的 reference-not-copy）。 |
| VIII Code as the Single Source of Truth | 权威次序：引擎常量 > 生成物 > 撰写物；两者冲突时修订本文档。 |
| XI Dogfooding | A–H 首轮修复正是本机制在本仓的第一次真实使用，而不是一份清理清单。 |
| XVI Fast Fail | 不可判定降级为 `unevaluated` 而非"干净"；"我看过了，没有"与"我没能看" MUST 分开报。 |
| XIX Self-Explanatory Structure | 类别的三件套（可观察定义 + 判定主体 + 降级形态）让每个类别名本身说明它要什么。 |
| 目录治理（XVII） | 新文件 MUST 在 `.specify/shared/definitions/framework-map.md` 的登记表可见；不新建目录。规则真源为 `.specify/shared/guidelines/directory-governance.md`（见下表首行）。 |

**四条相邻纪律的边界（本节只说边界，规则按指针引用）**：这四条纪律各自已有 owner，本节 MUST NOT 复述其规则，
也 MUST NOT 被读成它们的第二定义点。下表的「分界」一列是本节的唯一新增内容：它回答「同一件事被两条纪律同时
看见时，归谁」。

| 纪律 | 规则 owner（指针） | 分界（本文档管哪一半） |
|---|---|---|
| One Source of Truth（宪法 XIV） | `.specify/shared/guidelines/one-source-of-truth.md` | owner 纪律管**每一件事实**的唯一定义点；本文档只拥有 Non-Disposable 的那几件事实（表格前 16 行），并因此是 `multi-owner` / `stale-constant` 两类的**检出者**——检出别人违反 owner 纪律，不使本文档成为该纪律的 owner。 |
| Fast Fail（宪法 XVI） | `.specify/shared/guidelines/fast-fail.md` | Fast Fail 管**一次运行中**的异常分流（纠正 vs 裁定）；本文档管**运行之间留在树上的**残留载体。二者的共面只有一处：不可判定 MUST 降级为 `unevaluated` 而不是「干净」——判据归本文档，披露义务归 Fast Fail。 |
| Directory Governance（宪法 XVII） | `.specify/shared/guidelines/directory-governance.md` | 目录治理管**目录**能否存在（命名、登记、临时目录的忽略规则）；本文档管**文件与正文**是否过期、无用或延期，且不拥有「新文件要登记」这条规则——它只承接该规则的后果（`orphan-path` 类点名一处指向不存在路径的引用）。 |
| Re-Anchoring（宪法 XXII） | `.specify/shared/definitions/re-anchoring-definitions.md`（执行步骤 owner 为 `sdd-loop-driver/references/checkpoint-protocol.md` § Direction audit） | Re-Anchoring 管 agent **在本轮内**是否仍忠于初始任务与规则；本文档管**本轮结束后**留在树上的载体。分界的判别：一个载体若只需重新读一遍就能被正确对待，那是 Re-Anchoring；若它需要一次**处置**（四个封闭值之一）才能不再误导下一位读者，那是本文档。 |

**这四条都不构成新原则**：上表四行全部是宪法**既有**条目的承接关系，本特性没有新增一条，也不因此改动任何
条目的正文或计数 pin（D-2 / OI-4）。

**连带的四条义务（FR-064）**：(i) 新增文件在既有登记处可见；(ii) 被守物损坏时契约测试 MUST 变红（至少一条
变异腿）；(iii) `AGENTS.md` 的指针只经 `/speckit.instructions` 生成，MUST NOT 手改；(iv) 本节存在本身——写明
本次**未**新增原则及其理由，并给出与四条相邻纪律的分界（本节上面的分界表），否则下一位读者会把"理念没有原则"
读成遗漏，或把本理念读成某条既有纪律的重复。

**若用户日后裁定补一条原则（OI-4）**：届时按宪法既有五处落点 + 三计数 pin + Sync Impact Report 的完整流程，
作为一次独立的 MINOR 修订执行（FR-065）。本特性的 FR/SC MUST NOT 预写其条号或 pin 数值。
