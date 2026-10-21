# TODO-in-Context (上下文内嵌 TODO) — 待办与代码位置绑定的纪律

本文件是 **TODO-in-Context 纪律**的唯一真源(single source of truth):SPECKIT TODO 标记的两种形态归属、上下文补全判读规则、其他工作流的提前感知(perception)处置义务、标记生命周期(insert → perceive → collect → execute → remove)、以及与 Park 寄存库的边界,都只在此定义。检测语义(哪种行算一个块、上下文字段如何提取)归扫描器 CLI 契约所有(框架仓库 spec 020 的 `search-todo-cli.md`,规则 D-1..D-12 与 C-1..C-6)——本文件引用它,MUST NOT 复述其规则。命令侧流程(`/speckit.todo` 四模式)归该命令的模板 `.specify/templates/commands/todo.md` 所有。导览面见 `docs/concepts/todo-in-context.md`。

**本纪律防的失效是「待办与它的位置分离」**:todo 记在别处(清单、issue、会话),代码里却无迹可查——读代码的流程不知道这里有计划中的改动,清单里的描述又缺乏代码上下文而读不准。TODO-in-Context 把待办以标记形式嵌在它所指的代码/文档元素处,同时闭合两个失效:

1. **上下文补全(context completion)**:块内容只写简短意图即可,周边代码、相邻注释、标题与段落(prologue/epilogue/context_heading,字段形态归契约所有)完成与校正它的解读——描述简短或存在误读可能时,判读者 MUST 先从上下文消解,仍有两种读法才升级问用户(Ask 纪律:`.specify/shared/guidelines/ask-record-repeat.md`)。
2. **提前感知(early perception)**:标记是「已声明的未来变更」信号。任何工作流(实现、评审、重构、分析、文档)读到标记时,都知道此处将来可能有改动,从而把标记纳入考量而不是被它惊吓。

## 两种形态(归属,非检测规则)

| 形态 | 适用文件 | 载体 |
|------|---------|------|
| 围栏(fence) | Markdown 族文件 | 开栏行含 `SPECKIT TODO` 的围栏块 |
| 注释(comment) | 源代码等非 Markdown 文件 | 同 token 的连续行注释,首行 payload 以 `SPECKIT TODO` 起头 |

选择规则由 FR-015 约束:Markdown 文件用围栏;源代码文件用该语言行注释 token 的注释块——**在源代码文件里插围栏块是语法错误,属形态误用**。精确的开块/续行/终止判定归契约 D-9..D-12。

## 其他工作流的处置义务(封闭集,三选一按情形)

任何命令、技能或代理在其正常工作中读到 SPECKIT TODO 标记时:

1. **不删不改(不得静默清除)**:除非本工作流正在执行该标记的任务并按生命周期移除它,否则 MUST NOT 删除、改写或绕过该标记。用户的未落地意图不是编辑路径上的杂物。
2. **纳入考量**:改动标记附近代码时, MUST 把标记内容当作该区域的既定意图之一——与现有行为冲突时,以标记为准调整方案或在报告中指出冲突,而不是无视标记后让将来返工。
3. **报告所遇**:会话收尾时,把遇到但未处理的标记(文件:行 + 一行内容)列入执行报告——读者由此知道哪些已声明的变更还悬而未决。

三条都是可判定义务:复核者重读同一文件即可验证标记是否仍在、是否被报告。

## 生命周期

```
insert(就位插入) → perceive(其他流程感知) → collect(/speckit.todo 收集) → execute(有界执行) → remove(移除已完成块)
```

- **insert 就位原则**:块 MUST 插在它所指的确切代码/文档元素处(函数上方、语句旁、小节内),MUST NOT 堆放在文件头尾;内容写简短意图即可,上下文完成它。
- **remove 与 retire 对称**:块的任务执行并验证后,同一步内把该块从源文件移除——落地的变更 + git 历史就是记录,留下过期标记等于让下轮 collect 重复规划已完成的工作。此规则与 Park Mode 的 retire-after-merge 对称(寄存记录合并落地后可删,合并点即真源)。
- **执行与移除的边界**:只移除**本次执行并验证通过**的块;未执行、被否决(veto)的块留在原地,由报告与 memory 记录否决原因,下轮 collect 经 memory-recall 不再重复规划(该规则归 `.specify/templates/commands/todo.md` Collection Mode)。

## 与 Park 寄存库的边界

Park(`.specify/memory/todo/`)收纳**没有代码触点的想法**;TODO-in-Context 标记收纳**有明确代码/文档触点的待办**。同一事项从想法走向落地时,路径是 park → promote → insert(寄存记录标 `promoted` 并指向目的地)。两个机制不互相替代:想法无位置可嵌,待办有位置不该寄存。

## 与相邻纪律的关系

- 上下文补全的「先消解、后问用户」与 Ask 纪律同构(`.specify/shared/guidelines/ask-record-repeat.md`),不复述其 batching 与推荐规则。
- 移除已完成块是「就地修复并披露」型纠错,不是裁定——二值判据归 `.specify/shared/guidelines/fast-fail.md`,本文件不复述。
- 本文件 OWN 上述纪律定义;`.specify/instructions.md` 的 Documentation Map 行、`docs/concepts/todo-in-context.md` 叙事、命令模板 Philosophy 节均为指针面,不携带规则细节。
