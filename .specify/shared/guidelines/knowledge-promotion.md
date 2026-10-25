# Knowledge Promotion(知识记录与升格)

知识记录义务的触发面与用户重复强调的升格阈值的唯一真源。规范:**每次框架命令或技能驱动的运行若产生不可推导的要点,MUST 在收尾前写入持久载体;同一要点被用户强调两次以上时,MUST 升格进主流程,而不是只留在记忆里。**

本文件由指令文件的 `## Knowledge Recording & Promotion` 章节以指针引用;该章节只承载摘要,细则归此处。

边界(引用,不复述):

- 记录落点(哪类答案去哪)归 `.specify/shared/guidelines/ask-record-repeat.md` § 2。
- 记忆层的存储/检索机制归 `docs/reference/skills/memory.md` 与 `memory-record` / `memory-recall`。
- 事实归属归 `.specify/shared/guidelines/one-source-of-truth.md`。

## 1. 记录义务

### 1.1 什么算"新获取的知识"

不可从项目状态推导的要点:

- 用户偏好、约定、纠正及其理由;
- 决策与被否方案、取舍理由;
- 环境怪癖、工具行为、踩过的非显然坑;
- 应影响后续工作的评审发现;
- 非显然但有效、值得复用的做法。

可推导事实——代码结构、文件布局、git 历史、注册表已有内容——MUST NOT 写入 memory;它们已有 owner,发现过时就直接修 owner,而不是复制一份。

### 1.2 何时记、记到哪

- 每次框架命令或技能驱动的运行结束后,若产生上述要点,MUST 在收尾前记录。
- 落点按 `ask-record-repeat.md` § 2 的表选择;该表是唯一真源,本文件不复述。
- 一次性/工作态用 memory `session`;跨会话的偏好、约定、决策用 memory `knowledge`。
- memory 写入 MUST 经 `memory-record`,且 `--source` MUST 是 `/speckit.<command>` 或 `skill:<name>`;MUST NOT 伪造 source。
- 超出框架命令/技能驱动边界(任意对话)时,写入项目文档或用户指定的笔记;不要为满足本义务而伪造 memory source。

### 1.3 检索义务

重新向用户提问、或重新推导同一事实之前,MUST 先用 `memory-recall` 检索既有记录。检索不到不等于没记过;先查,再决定是否提问。

## 2. 强调升级:2+ → 主流程

### 2.1 什么算"用户强调"

同一要点出现下列情形之一:

- 用户在后续回合再次提出同一要求;
- 用户再次纠正同一行为;
- 用户否决同一方案/再次表达同一偏好;
- 用户明确说"记住""总是""不要再""我已经说过"。

单次澄清、引用、复述不算强调。

### 2.2 证据约定

每次强调 MUST 写一条 memory `session` 条目:

- tags 含 `user-emphasis` 与稳定键 `key:<ascii-slug>`;
- `<ascii-slug>` MUST 是 ASCII 稳定短名(如 `temp-dirs`、`no-bare-tmp`);
- 计数用 `memory-recall --tags key:<ascii-slug>`。引擎的 tag 过滤是 any-of,故一次只查一个 key 标签;查询分词仅 ASCII,中文 key 无法可靠检索。

例:

```bash
python3 .specify/scripts/python/memory-utils.py --action record \
  --scope session --source "/speckit.requirements" \
  --title "User emphasis: temp dirs" \
  --tags "user-emphasis,key:temp-dirs" \
  --content "User restated: do not use bare system temp; use the sanctioned roots."
```

### 2.3 阈值与升格动作

同一个 `key:` 的第 2 次强调(含本次)MUST 触发升格。升格 MUST 全部完成:

1. 更新 owner 文档:把规则写进它所属的 `.specify/shared/guidelines/` 真源(或对应 owner)。
2. 更新常驻指令章节:摘要 + 指向 owner 的路径,保持指针形态。
3. 增加守卫:契约测试、扫描器或既有确定性检查;没有守卫的新表面是未来漂移点。
4. 接入执行面:在命令模板、技能、脚本或门控中加入显式步骤/检查,使执行者实际会经过它。
5. 记录升格:写一条 memory 条目,附证据条目路径与升格落点。

**只写文档、只写 memory 不算升格。**"主流程"指执行者实际会经过的可执行表面,不是被动文档。

### 2.4 与相邻纪律的边界

- `.specify/shared/guidelines/fast-fail.md`:一次用户直接纠正已足够驱动异常类清单移动;本条不削弱它,而是增加"2+ 强调必须结构升格"的额外触发。
- `.specify/shared/guidelines/self-improvement.md`:直接用户纠正是有效辅助证据,不需要重复出现;本条同样是额外触发,不替代其证据资格。
- `.specify/skills/improve-skills/SKILL.md`:把重复用户纠正转成显式决策分支,是技能层实现;本条是框架层义务,二者引用而不互相替换。
- `.specify/skills/internal/code-review/SKILL.md`:"同一问题超过 2 次 → linter/checklist"是评审清单的局部规则;本条不重定义它。

## 3. 反模式

- 只记录,不升格:第 2 次强调后仍然只写一条 memory。
- 把规则复制到多处却不加守卫:重复变成漂移。
- 用中文 key 做检索:引擎分词仅 ASCII,检索不到。
- 为凑够次数把单次澄清记成两次强调。
