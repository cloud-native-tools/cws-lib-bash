# Script Interface Definitions — 脚本接口契约的唯一 owner

**本文档是「脚本接口契约」(Script Interface Contract) 的唯一真源 (owner)。** 它拥有,并且只拥有以下五件事:

1. **判定对象**:候选面如何派生、适用集与豁免集如何划分(`## 1. 判定对象与分类`)。
2. **必备标志及其必备内容**:`-h` / `--help` / `--version` 各自必须回答什么(`## 2. 必备标志与必备内容`)。
3. **零副作用边界**:标志在场时什么允许、什么禁止,取证在何处进行(`## 3. 零副作用边界`)。
4. **未知选项的拒绝要求**:未声明的 `-*` token 如何被拒绝、`--` 边界如何生效(`## 4. 未知选项的拒绝`)。
5. **豁免判据与已声明例外登记**:一个文件凭什么豁免,例外如何登记与复算(`## Declared Exceptions`)。

其他任何位置——宪法模板、本仓宪法、指令模板与 `instructions.md`、生成器的 MUST include 清单、检查器、测试——
MUST 以「摘要 + 路径」引用本文档,MUST NOT 复制本文档的必备内容标签清单或分类步骤清单。检查器
`.specify/scripts/python/script-interface-check.py` 的 `--emit-rule` 输出与本文档 MUST 在标签集与类别词汇上双向一致;
不一致是缺陷,不是可选配法。

**适用范围**:本规则适用于框架自身脚本、下游项目脚本与第三方脚本三者,不因脚本由谁分发而失效。下游项目在自己的
`.specify/shared/definitions/script-interface-definitions.md` 中拥有同一份文档的投影(逐字节相同)。

**不在本文件**(只给指针,不复述):

| 主题 | 所有者 |
|------|--------|
| 一条条款的语法、正文边界与引用组 | `.specify/shared/definitions/contract-clause-definitions.md` |
| 确认门分类与「存疑从严」判据 | `.specify/shared/guidelines/confirmation-gates.md` |
| 临时目录的可用根与清理 | `.specify/shared/guidelines/temp-directory-discipline.md` |
| 镜像投影机制与 `MIRROR_PAIRS` | `.specify/scripts/python/sync-mirrors.py`(其声明表) |
| 一次执行的全量捕获纪律 | `.specify/shared/guidelines/single-run-evidence.md` |

---

## 1. 判定对象与分类

### 1.0 适用范围（2026-11-08 裁定）

必备集只包含**功能性、非只读**脚本：它在被直接运行时执行自己的功能性动作，且该动作可能写盘。以下按运行语义
**豁免**或**可选**，且每条都必须带机械判据与证据，不得用目录级静默排除：

- **pytest 模块**：导入 `pytest` 或定义 `test_*` 函数、其动作属于 pytest 而非文件自身入口的 `.py` → 豁免，
  basis `pytest-module`；`tests/**` 是规范案例。
- **只读脚本**：没有声明写触发选项、且 flag 运行零写入 → `--help` / `--version` 为**推荐**，缺失不构成违规，
  basis `optional-read-only`。
- **范围外路径**：`src/specify_cli/**`（归 requirements 的 Out of Scope）→ 豁免，basis `out-of-scope`。
- **历史记录**：`.specify/specs/*/notes/**`（A9 明令不改写）→ 豁免，basis `historical-record`。

### 1.1 候选面由两个机器可读来源派生

候选集 = 版本控制枚举出的全部 `*.sh` / `*.py`,减去 `.gitignore` 判为忽略者。MUST NOT 由手写目录名单派生,
也 MUST NOT 由任何目录级排除跳过:被忽略者之所以不在集合内,是项目自己在 `.gitignore` 里说了那句话,而不是
检查器替它说的。

### 1.2 覆盖断言与候选面同权

候选面 MUST 同时被覆盖断言校验:检查 MUST 遍历工作树全部 `*.sh` / `*.py`,任一文件既不在候选集中、也不在
忽略集中时,MUST 以非零退出码报错并点名该文件(判为「遗漏的候选」)。版本控制缺席时,工作树遍历的集合
**就是**候选集,且报告 MUST 写明这一降级来源;MUST NOT 把「什么都没扫到」当作通过。

### 1.3 分类只回答一个问题,且必须由运行回答

分类只回答「该文件是否具备独立执行入口」。这个问题 MUST 以运行语义回答:把文件按脚本方式执行,观察其入口之后的
代码是否真的执行。以下三项 MUST NOT 作为判据,它们在两侧都会误判:

- 顶层是否存在 `exit` / 执行语句或依赖检查;
- 文件头声明的是 `bash` 还是 `sh`;
- 作者在文件里怎么自我描述(注释、docstring、文件名)。

`.py` 侧同理:「有没有 `__main__` 块」不是判据——带块而被 import 的模块并不执行它;而在 import 时就做事的模块
不因没有块而豁免。

### 1.4 分类步骤

对每个候选,按以下顺序执行;每一步的观察都必须落进报告的证据字段,而不是留在检查者的记忆里。

1. **定语言**:按扩展名判 `bash` 或 `python`,并记录该文件是否被 source / import 过。
2. **判镜像来源**:`.specify/**` 下的副本若存在同路径的源,继承源的分类,只判它按投射规则携带的标志面;
   无同路径源的副本(`mirror-unpaired`)按自身运行语义判。
3. **施加一次变异**:在受测树的副本上,把入口之后的第一个写型副作用替换为一条「已执行」标记(`.sh`),或在
   解释器 import 机制之外留下一个可观测效应(`.py`)。
4. **运行并观察**:带一个**已声明**的选项运行该副本;标记/效应出现即判适用,不出现即判豁免。
5. **双向判定**:文件同时被 source / import 且能按脚本运行时,MUST 判为适用;「它也是库」MUST NOT 作为豁免依据。
6. **记证据**:每个结论都带一条可复核的证据串(哪次观察决定了它),并落进报告的 `basis` 与 `evidence`。
7. **静默排除禁止**:一个候选既不合规也不豁免时,MUST 作为违规点名缺失项,MUST NOT 存在「未判定」状态被
   计入合规。

### 1.5 第三方来源判据(两顶帽子)

一个候选判为「第三方/上游脚本」,当且仅当两条机械条件**同时**成立:它位于该技能的分发源之下
(`skills/external/<name>/`),且该技能的 `SKILL.md` 声明 `classification: external`。后者是唯一机器标记,
MUST NOT 增设「目录里有上游许可文件」这类第二分支。凡 `SKILL.md` 声明 `classification: internal` 的技能,
无论落在 `skills/internal/` 还是 `skills/external/` 目录下,都判为框架源并就地补齐,不得走已声明例外。

---

## 2. 必备标志与必备内容

每个适用脚本 MUST 同时支持 `-h`、`--help` 与 `--version`。三个标志各自必须回答的内容如下;`-h` 与 `--help`
MUST 行为等价、输出同一份正文。

| 标志 | 必备内容 | 判据形态 |
|------|----------|----------|
| `-h` / `--help` | 调用形态、可识别的选项及其含义、是否产生副作用及写在哪些路径、退出码含义 | 四条**分别**断言,不可由一句「usage」蒙混 |
| `--version` | 一行 `<script-name> <framework-version>` | 单行、可解析、退出 0 |

`--version` 的版本值 MUST 在运行时从 `pyproject.toml` 读取,MUST NOT 由脚本正文携带字面版本号:全仓范围内
脚本正文中的版本形字面量扫描 MUST 为零命中。版本源按「从脚本自身目录向上、到包含 `.git` 的最近祖先为止」的
**有界**搜索定位,不得越出该根;找不到根或找不到 `pyproject.toml` 时,该行 MUST 为 `<script-name> unknown`,
退出码 MUST 仍为 0 —— 这是一个观测,不是违规。

必备内容标签的闭集是:调用形态 (`usage`)、可识别选项 (`options`)、副作用声明 (`side-effects`)、
退出码含义 (`exit-codes`)。检查器的 `--emit-rule` 输出的 `labels` 键 MUST 与这四条逐项相等;本文档是该闭集的
唯一书写处,其他落点 MUST 只写摘要加路径。

**复述的匹配单位是完整标签,不是单词**。判定某个落点是否复述了本文档,只看它是否写出了完整的标签形态
`` `{0}` 标签 ``(四个标签各填一次,如 `` `usage` 标签 ``),MUST NOT 以裸普通单词命中判定:这些词在别处承载
别的 事实(「不完整或错误的选项」讲的是决策质量,「token 使用效率」讲的是效率纪律),拿单词去判会把无关散文判成复述。
本文档是这条匹配单位的唯一书写处;守护测试从本节读回该形态,不自行另写一份。

---

## 3. 零副作用边界

任一标志在场时,脚本 MUST NOT 执行主动作、MUST NOT 写文件、MUST NOT 调用写入型外部命令、MUST NOT 创建备份;
判定 MUST 先于任何副作用,也先于任何可能要求用户确认的前置检查。脚本声明了写触发选项时,该选项与标志同时在场
时标志 MUST 胜出,在两种参数顺序下都在主动作之前退出——「先打印 usage 再继续执行」不是拒绝。未声明任何写触发
选项的脚本没有可判定的顺序,该探针 MUST 记为 `not applicable`(basis `no-write-option`),不计违规。

取证 MUST 在受测仓库之外的一个副本树上进行:副本树自身可被写入,受测树的取证不受其运行时临时文件污染。
快照对为三件:受测树的 `git status --porcelain` 输出、受测树内全部 `*.sh` / `*.py` 的 `sha256`、
`.specify/` 下的文件清单与哈希。四次调用(`-h`、`--help`、`--version`、一次未知选项)之后,快照对 MUST
逐字节相同。在受测仓库内直接执行这些调用 MUST NOT 被采信为证据。

实证副本树 MUST 是一个真实的 git 工作树(克隆而来),且 MUST NOT 落在 `noexec` 挂载的临时根下。

---

## 4. 未知选项的拒绝

未声明的、以 `-` 开头的 token MUST 以非零退出码结束,并在标准错误输出可识别的错误信息与用法提示;它 MUST NOT
到达主动作,其输出 MUST 在任何写入之前产生。同一次调用中已存在合法选项 MUST NOT 使未识别选项被放过。

`--` 之后的参数按脚本声明的约定处理,不被视为未知选项。该拒绝 MUST 在脚本否则接受自由文本位置参数时同样生效。

bash 侧的可实施形态是唯一的一种:在 source 任何共享库之前、在任何 `mkdir` / `git` 写入 / manifest 生成之前,
设一个扫描 `"$@"` 并把内部 `--` 当终止符的 `case` 循环;脚本已知的、形似标志的选项是其上方的分支,因此合法选项
永不被拒、未识别选项永不落到主动作。MUST NOT 用 `getopts`(它遇 `--` 即停,且不拒未知长选项)。MUST NOT 放在
`source` 之后(共享库自身有顶层依赖检查,会把 `--help` 变成一次非零退出)。

### 4.1 守卫块的插入位置(正式规则)

上文「MUST NOT 放在 `source` 之后」是这条规则的一个特例,此处把它写全。**守卫块 MUST 是消费脚本的第一个可执行
块**,且 MUST 同时位于下列每一件之前:

1. 任何 `source` / `.` 调用(共享库的顶层检查会先于回答发生);
2. 任何 `mkdir` / `rm` / `mv` / `cp` 等目录与文件写入;
3. 任何 `git` 写操作(`add` / `commit` / `checkout` / `archive` 落盘等);
4. 任何 manifest / 清单 / 模板的生成或重写;
5. 脚本自身的参数解析与主动作。

「第一个可执行块」的判定按**文本位置**:块之外、块之前只允许 shebang、注释与空行。允许的写法是在块内先
定位脚本目录、再 source 共享库——那一步属于块本身,不构成「块之前的 `source`」。

独立的 `.specify/` 副本(下游项目、投射镜像)可能找不到共享库。此时块 MUST 仍能回答:`bash-version-guard`
投射形态把版本行函数的**函数体**经 `__SCRIPT_INTERFACE_VERSION_BODY__` 哨兵内联进块内,因此镜像不 `source`
任何东西也能给出 `--version`;`-h` / `--help` 的正文由块自身按第 2 节的四个内容标签给出。哨兵只有两处提及:
本节与产出它的 `.specify/scripts/python/sync-mirrors.py`;手写脚本 MUST NOT 携带哨兵,块由投射规则生成,不由人手抄。

检查入口:`.specify/scripts/python/script-interface-check.py` 的逐候选探针(第 3 节的执行体)在受测树副本上执行四个
标志,任一次出现写入即判该候选零副作用不成立;插入位置由同一批探针与 `tests/contract/test_script_interface_contract.py`
的 `T073` 断言共同判定。

python 侧:版本标志 MUST 在**每条子命令上**可解析(顶层 `action="version"` 在带必填 subparsers 的命令上于
「首选项即 `--version`」位置以退出码 2 被拒),或在解析 `argv` 之前以显式 `print` + `sys.exit(0)` 实现。

声明了 `passthrough` 的包装脚本(把未知 token 交给下游解析器)是该行为的声明,不是「静默忽略后照常执行」,
故 C-9 的第二肢按 basis `passthrough` 判为合规;未作此声明、仅因偶然在未知 token 上退出 0 的脚本仍判红。

---

## Declared Exceptions

无法在不改上游结构的前提下满足本契约的第三方脚本在此登记,**一行一个脚本**。登记表为空时,本表正文 MUST 只写
字面 `none`(此时表格仍保留表头,便于后续插入)。

| path | skill | unsatisfied clause | handling |
|------|-------|--------------------|----------|
| .specify/skills/document-utils/scripts/office/validate.py | document-utils | probe-inconclusive: the optional third-party modules (defusedxml / pypdf / python-docx) are not installed on the probe host | install the optional extras and re-probe; the script's entry layer already answers its flags |
| .specify/skills/document-utils/scripts/pdf/create_validation_image.py | document-utils | probe-inconclusive: the optional third-party modules (pypdf / Pillow) are not installed on the probe host | install the optional extras and re-probe; the script's entry layer already answers its flags |

**复算判据**(检查器逐条复算,不成立即报 `exception-unverifiable` 并以退出码 1 结束,不是默认放行):

- `path` 指向的文件存在;
- `path` 位于 `skills/external/<skill>/` 之下;
- 该技能的 `SKILL.md` 声明 `classification: external`;
- 四列齐备,任一列为空即复算不成立。

**处置列取值**:保留在入口层 · 停止分发该脚本 · 待上游修复。三者之外 MUST NOT 自造第四种。

**读取者**:唯一读取器是 `.specify/scripts/python/script-interface-check.py`。不在本表中的第三方候选 MUST 按普通候选判红,
MUST NOT 自动豁免。**维护者**:人与 `/speckit.implement` 都能改;本表是据以放行的凭据,由引入该例外的特性维护。
**下游投影**:下游项目把同一章节放在其 `.specify/shared/definitions/` 的同名文件里。

---

## 投影声明形态与消费方

本契约的镜像侧不被手改:`.specify/scripts/` 与 `.specify/skills/` 下的副本由 `.specify/scripts/python/sync-mirrors.py`
唯一产出。当源与镜像不能逐字节相同时,差异 MUST 是一个**已声明**的投射,且只声明一次。本特性消费两种投射形态,
形态名与锚点在此固定,新增第三种 MUST 先修订本节:

| 形态 | 效果 | 锚点 |
|------|------|------|
| `python-version-bridge` | 镜像是源,外加一段桥接块,插在源的 `if __name__ == "__main__":` 行**之前** | 该行必须存在,缺失即退出 1 并点名该对 |
| `bash-version-guard` | 镜像是源,外加一段守卫块,插在 shebang 行**之后**、其余一切之前 | shebang 必须存在,缺失即退出 1 并点名该对 |

投射 MUST 幂等:对已带投射的文件再施加一次不改变任何字节。MUST NOT 在文件尾部静默追加。每个被投射的镜像携带
**恰好一行**标记,使投射在文件原地可见;该标记 MUST NOT 声称镜像与源逐字节相同,源侧也 MUST NOT 声称自己是镜像
表面的全部真相——权威陈述在本节与 `contracts/mirror-projection.contract.md`,不在任何一侧的注释里。

镜像侧 MUST 自足:投射块不依赖只存在于源树里的东西,它按与源规则相同的有界向上搜索重新推导自己的版本行,
无 `pyproject.toml` 时照常打印 `unknown`。因此下游项目的 `.specify/` 副本自身就能回答 `--help` 与 `--version`。

`--check` 对被投射文件断言「镜像 == 源 + 已声明投射」,对其余文件保持逐字节相等;两类的输出 MUST 分开记录,
MUST NOT 合并成一句「镜像一致」。逐对严格性旗标(`strict_extras`)不因投射而改变。

---

## 检查入口与消费方

| 消费方 | 消费什么 |
|--------|----------|
| `.specify/scripts/python/script-interface-check.py` | 全部五节;`--emit-rule` 输出本节第 2 节所列八键,`--check-projection` 输出末节的投射判定 |
| `.specify/scripts/python/script_interface_cli.py` | 第 2 节的版本行形态与版本源,以及第 4 节的拒绝退出码 |
| `.specify/scripts/bash/script-interface.sh` | 第 3 节与第 4 节的 bash 可实施形态 |
| `tests/contract/test_script_interface_contract.py` | 本页与 `--emit-rule` 的双向一致性、以及五处落点的指针纪律 |
| 宪法模板 / 本仓宪法 / 指令模板 / `instructions.md` / 生成器 MUST include 清单 | 摘要一句话 + 本页路径;不复制本页内容 |

## 本文档不拥有什么

- **条款语法**:一条条款怎么写、正文到哪、引用组在哪,归 `.specify/shared/definitions/contract-clause-definitions.md`。
- **确认门与临时目录**:归各自 owner;本文档只按路径引用。
- **逐脚本判定结果**:适用集与豁免集的成员是检查器一次运行的产物,不是本文档的一份名单。本文档给判据,不给结论。
- **投射的实现**:投射表与 `--check-projection` 的实现在 `.specify/scripts/python/sync-mirrors.py` 与检查器;本文档只固定
  形态名与锚点这两件被声明的契约。
