# Dogfooding Definitions(Dogfooding 概念权威)

> **Single source of truth** for the Dogfooding concept system defined under
> Constitution Principle XI (v1.10.0): §0 Dogfooding 本体定义(含 §0.1 语义三层)、§1 问题/机制与
> 两种修复、§2 客户项目/框架项目与三副本拓扑。Canonical at
> `shared/definitions/dogfooding-definitions.md`, mirrored to
> `.specify/shared/definitions/`. Normative language follows RFC 2119.
> **引用约定**: 后续任何文档、流程或对话提及 "Dogfooding" 时,均按本文件定义
> 赋予其完整含义,无需在各处重述。References: `.specify/memory/constitution.md`
> § XI; glossary entries (Dogfooding / 问题修复 / 机制修复 / 框架项目 / 客户项目).

## 0. Dogfooding(本体定义)

**Dogfooding**(直译"吃自己的狗粮";说法流行于 1980 年代末美国软件业,常被
追溯到宠物食品广告典故与微软内部用语)特指
**使用自身来开发自身**的工程实践场景——一个提供开发辅助能力的项目,把该能力
用作自己日常的开发工具。最常见于**开发工具或框架类**程序开发项目(编译器、
构建系统、CLI 工具、SDK、SDD 框架)。

### 0.1 语义三层(由浅入深)

"Dogfooding" 的含义 MUST 按以下三层完整理解,不得停留在浅层字面:

| 层 | 俗语表述 | 含义 |
|----|----------|------|
| **L1 字面层(浅)** | "自己的狗粮自己吃" | 词源直译:做出的产品自己先用。仅声明"自用"这一事实,是最浅显的表层——只回答"用不用",不回答"为什么有用"。 |
| **L2 契合层(深)** | "木匠最顺手的工具都是自己造的" | 制造者即使用者:工具在日复一日的自用中与使用者的手反复磨合,因而最顺手、最贴合真实工作方式;顺手的依据是亲手使用,而非假想需求。 |
| **L3 目的层(本义)** | 第一手反馈 → 持续改进 | Dogfooding 的**目的**:通过自己使用自己开发的软件,不经二手转述、不靠纸上推演地获取**第一手反馈信息**,再以反馈驱动**持续不断的改进**。 |

三层关系:L1 是手段的起点,L2 是手段的形态,**L3 才是目的**。只"自用"
而不形成反馈回路与改进动作的 Dogfooding 是形式主义;Spec Kit 的
use → feedback → iterate 双环(Loop A / Loop B,宪法 XI)正是 L3 的
机制化实现。

**类比:编译器自举 (self-hosting)** —— 用编译器编译其自身的源代码。只有完成
自举的编译器,才证明其表达力与正确性达到了实用水平;同理,只有在自身工程中
表现良好的开发工具,才赢得辅助其它项目的可信度。

在 **Spec Kit 语境**下:spec-kit 仓库既是框架源(作者帽,`skills/` 等),又是
自己的客户项目(用户帽,本仓 `.specify/`),即**用 /speckit.* 工作流开发
/speckit.* 工作流本身**。

该词一经提及即承载以下语义束(详见对应章节,不另行重述):

| 语义束 | 章节 |
|--------|------|
| 语义三层:吃狗粮(字面)→ 木匠自造工具最顺手(契合)→ 第一手反馈驱动持续改进(目的) | §0.1 |
| 真实场景替代假想设计(用自身工程验证能力,而非纸上推演) | 宪法 XI Rationale |
| 自举证明(自身工程表现 = 能力可信度的必要条件) | §0 |
| 一人两顶帽子:框架作者 vs 框架用户(三副本拓扑) | §2 |
| 两个反馈环:Loop A(客户→框架上送)/ Loop B(客户自用) | 宪法 XI |
| 修复落机制侧(问题修复 vs 机制修复判定法则) | §1 |

## 1. 问题与机制 (Problem vs Mechanism)

- **问题 (Problem)**: 一次执行中观察到的**具体缺陷实例**——某文件缺某节、某次
  输出错、某条测试红。有具体位置,可一次性修补。
- **机制 (Mechanism)**: **稳定产生/维护该类工件或行为的流程载体**——模板、
  生成/再生成命令、reconcile 流程、契约测试、镜像同步引擎。问题实例是机制
  运行的输出;同类问题在机制的所有下游实例上同构存在。

### 1.1 两种修复

| | 问题修复 (Problem Fix) | 机制修复 (Mechanism Fix) |
|---|---|---|
| 修补对象 | 实例(这份文件、这次输出、这条测试) | 产生实例的源头(模板/命令/流程/契约) |
| 传播性 | **不传播**——同机制下次运行复现同类问题;其它项目实例原样带病 | **自然传播**——下次执行对应命令时,修复随流程到达本仓活动文件与所有下游项目 init 出来的实例 |
| 适用场景 | 一次性工件的缺陷;或机制修复落地前的**临时止血** | 一切由机制反复产生的工件(默认情形) |

### 1.2 修复判定法则(宪法 XI,规范性)

修复任何非一次性工件时,执行者 MUST 先回答:**"这个实例是哪个机制产生的?"**

1. 修复 MUST 落在机制侧(模板、生成命令的注入规则、reconcile 流程、守护契约)。
2. 问题侧修补**仅允许**作为机制修复落地前的临时止血,且 MUST 留痕(何处止血、
   机制侧待办),止血不留痕视为未修复。
3. 机制修复交付的验收口径:下一次执行对应命令,修复在**未经手工干预**的活动
   工件上自然出现(或由守护契约证明不再可能复发)。

**标定案例(2026-08-14 Dogfooding 节缺口)**:活动 `instructions.md` 缺
`## Dogfooding Practice` 节。机制诊断 = ① `/speckit.instructions` reconcile
流程不传播模板新增节;② 无契约守护活动文件节集。问题修复 = 手工插节(不传播,
其它项目同样缺);机制修复 = 修 reconcile 注入规则 + 补契约(活动文件托管节集
⊇ 模板节集),下次刷新自然带上、全下游免疫。

## 2. 客户项目与框架项目 (Client Project vs Framework Project)

Spec Kit 仓库的 Dogfooding 本质是**一人分饰两角**:既是框架的作者,又是框架
的用户。物理上存在三个副本:

| 副本 | 路径(本仓语境) | 角色 |
|------|----------------|------|
| **框架源** (Framework Sources) | `skills/`、`templates/`、`scripts/`、`shared/`、`agents/`、`src/specify_cli/` | 框架作者帽:开发与发布(git push / 打包) |
| **自用运行时** (Self-Dogfood Runtime) | 本仓 `.specify/` | 框架用户帽:以客户身份由 init/刷新装出来的运行副本 |
| **已安装发行版** (Installed Distribution) | `.../site-packages/specify_cli/` | 发布产物:下游用户安装;`specify init` 由此把框架装进各客户项目的 `.specify/` |

**流转链**: `skills/` 等框架源开发 → 发布 → 用户安装到 site-packages →
`specify init` 装进客户项目 `.specify/`。

### 2.1 两顶帽子规则(宪法 XI,规范性)

1. 对本仓 `.specify/`(自用运行时)的任何**直接**修改都只是**客户侧问题修复**:
   对框架源无效,其它客户项目永远得不到,且可能被下次刷新覆盖。
2. 意在影响**所有**客户项目的修复 MUST 落在框架源侧并沿流转链重新发布;
   活动工件(本仓 `.specify/` 文件)只应作为机制运行的输出存在。
3. 任一时刻的修改动作 MUST 先自答:**"我现在戴的是框架作者帽(改 `skills/`
   等源)还是框架用户帽(消费 `.specify/`)?"** 修复落在与目标受众匹配的一侧。
4. **三副本拓扑对路径解析的陷阱(规范性)**:自用仓同时含有框架源(`scripts/`、
   `templates/`、`shared/`)与 `.specify/` 运行时,故任何"向上找最近的、含
   `.specify/` 的祖先目录"式根解析启发式都会**在本仓自匹配**——把每次调用都解析到
   框架仓,而不是调用方自己的工作区。守卫:引擎自定位 MUST 只在**自身已解析路径上
   存在字面 `.specify` 路径分量**时触发(即"我是被从镜像副本调用的"),MUST NOT
   以"某个祖先恰好含有 `.specify`"为据。该判据 MUST 有**反向断言**(从框架源副本
   调用时不得自解析),因为只从一侧运行的测试看不见这个缺陷:它表现为工作区状态被
   写进框架仓,而不是表现为一次失败。
   同族另两个变体(均已实际产出 `.specify/.specify/` 残留投影):(a) **镜像位置根
   算术**——以 `Path(__file__).resolve().parents[2]` 取根的引擎,从镜像副本
   `.specify/scripts/python/` 调用时根解析为 `.specify`,镜像目标全部深嵌一层;
   (b) **cwd 即根**——`specify init --here`(及任何以 cwd 为项目根的流转)在 cwd 位于
   `.specify/` 内时把框架树装进运行时目录。统一守卫(反向断言):**名为 `.specify` 的
   目录永远不是仓/项目根**——根推导后若 `root.name == ".specify"` 则向上纠正或直接
   拒绝(携带守卫的引擎:`scripts/python/sync-mirrors.py`、`gate-check.py`(walk-up
   跳过名为 `.specify` 的祖先)、`tools-utils.py`;CLI 侧 `render_agents_for_tool` 与
   `specify init` 两分支直接拒绝)。漂移守护:
   `tests/contract/test_mirror_root_guard.py`(镜像位置调用不产嵌套 + canonical/镜像
   等价 + render/init 拒绝)。

### 2.2 与既有机制的同构映射

这对概念并非新发明,而是既有机制在概念层的命名:

- **Mirror 体系**(`sync-mirrors.py`,canonical → `.specify/` 镜像)= 框架源到
  自用运行时的受控投影,防止两顶帽子直接混写;
- **AGENTS.md / CLAUDE.md 符号链接** = 活动工件单源化,消灭客户侧双写;
- **Feedback Probe 内外类别** = 同一对概念在反馈流向维度的实例化:
  Loop A(内部 → 框架上送)与 Loop B(外部 → 宿主项目自留)。

## 3. 术语登记(词汇表)

以下术语已登记于 `.specify/memory/glossary.md`(origin=user, status=confirmed):
**Dogfooding**(§0 本体)、问题修复 (Problem Fix)、机制修复 (Mechanism Fix)、
框架项目 (Framework Project)、客户项目 (Client Project)。本文件为它们的
**概念权威**;词汇表条目为检索锚点。
