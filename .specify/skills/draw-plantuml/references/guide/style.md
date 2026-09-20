# PlantUML 样式指南

本文件定义 draw-plantuml 技能生成的所有 PlantUML 图表必须遵循的统一样式规范。在 Step 7 应用标准样式时，**必须**按照本配置对样式进行校验和调整。

**渲染方式**：使用 [render-plantuml.sh](../../scripts/render-plantuml.sh) 脚本渲染。脚本实现 SVG/PNG 双策略：
- **SVG**：注入 `scale 4 + dpi 300`（矢量无损，viewBox ≥ 3840×2160）
- **PNG**：自适应计算 scale/dpi，确保输出 ≤ 4095×4095（低于 Server 硬上限 4096）

## 一、基础样式模板（所有图表类型通用）

以下配置项必须插入在 `@startuml` 之后、图表内容之前：

> **注意**：`top to bottom direction` 仅适用于类图/组件图/部署图。时序图、活动图、状态机图、用例图请使用各自默认方向或 `left to right direction`（用例图），不要强行添加方向指令。渲染脚本 `render-plantuml.sh` 不会注入方向指令，由作者根据图表类型自行决定。

```plantuml
@startuml
' === 布局方向（仅类图/组件图/部署图适用，其他图类型请省略） ===
' top to bottom direction

' === 通用样式 ===
skinparam shadowing false
skinparam roundCorner 20

' === 高质量渲染（面向 SVG；PNG 由脚本自适应调整） ===
skinparam dpi 300
scale 4
skinparam defaultFontSize 16
skinparam defaultFontName "Arial, Helvetica, sans-serif"
skinparam padding 8
skinparam ArrowThickness 1
skinparam BorderThickness 1
' 以上 1px 为视觉强弱最轻基线（流线/叶元素档）；结构档由 <style> 提升，见 §十一

' === SVG 输出优化 ===
skinparam svgDimensionStyle false
skinparam svgLinkTarget _blank

' ... 图表内容 ...
@enduml
```

## 二、色彩模式选择（Monochrome vs Color）

在基础样式模板之后，根据图表需求选择色彩模式：

### 单色模式（默认，适合大多数技术文档）

在通用样式之后追加：

```plantuml
' === 单色模式（默认） ===
skinparam monochrome true
```

适用场景：标准技术文档、打印输出、不需要颜色强调的架构图。

### 彩色模式（需要颜色强调时使用）

**不添加** `skinparam monochrome true`，保持 PlantUML 默认彩色渲染。

适用场景：
- 需要使用 `<color:red>文字</color>` 或 `<font color=red>文字</font>` 进行颜色强调
- 区域（zone）需要不同颜色的边框或背景
- 品牌色彩或视觉重点需要保留

**重要警告**：`skinparam monochrome true` 会将**所有**颜色转换为灰度，包括通过 `<color:red>` 或 `<font color=red>` 设置的内联颜色。如果图表需要任何彩色元素，**必须省略**该设置。

## 三、关键路径着色

用颜色区分核心流程与异常分支（在需要彩色输出时使用，与 monochrome 模式互斥）：

```plantuml
' 正常流程保持默认色
client -> server : 正常请求

' 异常/关键路径用颜色突出
client -[#FF0000]-> server : 超时重试
client -[#FF8C00]-> fallback : 降级处理
```

> **注意**：本技能默认使用 `skinparam monochrome true`（黑白模式）。如需彩色高亮，需移除 monochrome 设置或改为 `skinparam monochrome false`，并在 SKILL.md 步骤中说明选择理由。

## 四、条件样式（按图表类型启用）

当图表包含 `actor` 或属于用例图（Use Case Diagram）时，在通用样式之后额外追加：

```plantuml
' === Actor 样式（仅含 actor/usecase 时启用） ===
skinparam actorStyle awesome
```

## 五、SVG/PNG 双策略说明

| 格式 | 策略 | 参数 | 输出尺寸 | 适用场景 |
|------|------|------|----------|----------|
| **PNG** | 自适应 | 脚本计算 | ≤ 4095×4095 | **所有图表（默认首选格式）**——最美观，Preview / Markdown 预览可直接查看 |
| **SVG** | 最大质量 | `scale 4 + dpi 300` | viewBox ≥ 3840×2160 (4K UHD) | 超宽/超大图（PNG 触及 4096px 上限时）或需任意无损缩放 |

**PNG 自适应算法：**
1. 先渲染 SVG，获取 viewBox 尺寸
2. 从 viewBox 推算图表 base size（= viewBox / SVG_SCALE）
3. 计算最大 scale 使 `base_size × scale ≤ 4095`
4. 若 scale < 1，则固定 scale=1 并降低 DPI：`dpi = 4095 × 300 / base_size`
5. 渲染后验证：若 PNG = 4096×4096 且文件 < 100KB → 判定空白，降级重试

**PlantUML Server PNG 硬上限：**
- 输出尺寸硬上限：4096×4096（任何参数都无法超越）
- 当 `scale × dpi × 图表尺寸` 导致内部渲染缓冲区溢出时，Server **静默返回空白 PNG**
- 本技能使用 4095 作为目标上限，确保安全距离

## 六、配置项说明

| 配置项 | 作用 | 适用范围 |
|--------|------|----------|
| `top to bottom direction` | 图的方向从上到下，保持阅读顺序一致。**仅类图/组件图/部署图适用**，时序图/活动图/状态机/用例图不要添加 | 类图、组件图、部署图 |
| `skinparam monochrome true` | 黑白单色输出，适合文档和打印。**可选**：需要彩色元素时省略此项（见"色彩模式选择"） | 按需启用 |
| `skinparam shadowing false` | 去除阴影效果，保持视觉简洁 | 所有图表 |
| `skinparam roundCorner 20` | 统一圆角半径为 20px | 所有图表 |
| `skinparam dpi 300` | SVG 高密度渲染；PNG 由脚本按需调整 | 所有图表（.puml 源文件） |
| `scale 4` | SVG viewBox 放大 4 倍（≥ 3840×2160）；PNG 由脚本按需缩减 | 所有图表（.puml 源文件） |
| `skinparam defaultFontSize 16` | 统一字体 16px，配合 scale 4 保证文字可读性；所有图表（含专项图）必须一致，避免跨图字号不统一 | 所有图表 |
| `skinparam defaultFontName "Arial, ..."` | 使用无衬线字体，渲染清晰抗锯齿 | 所有图表 |
| `skinparam padding 8` | 元素内边距 8px，避免内容拥挤贴边 | 所有图表 |
| `skinparam ArrowThickness 1` | 流线最轻基线 1px；关键路径用色相抬升、`[thickness=2]` 封顶（≤ 子模块边框档），见 §十一 | 所有图表 |
| `skinparam BorderThickness 1` | 叶元素边框最轻基线 1px；大区/子模块边框档由源内 `<style>` 提升，见 §十一 | 所有图表 |
| `skinparam svgDimensionStyle false` | SVG 不内联 width/height，使用 viewBox 实现无损缩放 | 所有图表（SVG） |
| `skinparam svgLinkTarget _blank` | SVG 中的超链接在新窗口打开 | 所有图表（SVG） |
| `skinparam actorStyle awesome` | Actor 使用 FontAwesome 风格图标 | 仅用例图/含 actor 的图 |

## 七、样式校验要点

在完成 PlantUML 代码后，逐项检查：

1. **布局方向**：确认 `top to bottom direction` 仅在类图/组件图/部署图中使用（其他图类型不应出现此指令）
2. **通用 skinparam**：确认通用 skinparam（shadowing、roundCorner）全部存在且值正确；确认色彩模式选择正确（单色图加 `monochrome true`，彩色图省略）
3. **高质量渲染 skinparam**：确认 `dpi 300`、`scale 4`、`defaultFontSize 16`、`defaultFontName`、`padding 8`、`ArrowThickness 1`、`BorderThickness 1` 全部存在；含多层结构的图另按 §十一 确认 `<style>` 强弱档已声明且渲染后 `stroke-width` ≥3 档可辨
4. **SVG 优化 skinparam**：确认 `svgDimensionStyle false` 和 `svgLinkTarget _blank` 存在
5. **条件 skinparam**：如图表含 actor 或为用例图，确认 `actorStyle awesome` 已添加
6. **位置**：所有样式配置必须在 `@startuml` 之后、图表元素定义之前
7. **无冲突**：确认图表内容中没有覆盖上述 skinparam 的重复声明
8. **PNG 安全**：确认渲染脚本输出无 WARNING（表示 PNG 未触发 4096 硬上限）
9. **语义编码**：若图用颜色/符号承载状态，逐条走一遍第九节（颜色 + 符号冗余、符号字形白名单）与第十节（图例契约 + 自检脚本）

## 八、专项图表的样式（非 UML）

WBS、甘特图、思维导图、JSON、YAML、Salt 这 6 种专项图**不是** UML 图，**不适用**本文前七节的单色 `skinparam` 规范：它们不接受 `skinparam monochrome true`、`skinparam dpi/scale` 等通用配置，而是使用**原生配色** + 各自的 `<style>` 块 + 内联着色指令。

> **例外：ER 图走 UML 规范。** ER 实体关系图虽被官方归为非 UML，但用 `@startuml` + `entity` 语法、走 Graphviz 布局，**适用**本文前七节的单色 skinparam 规范（可叠加 `hide circle`、`skinparam entity { ... }`），见 [howto/18-er-diagram.md](../howto/18-er-diagram.md)。

- **不要注入单色 skinparam**：这些图靠颜色传达状态/分类/高亮，强制单色会丢失信息。渲染脚本 [render-plantuml.sh](../../scripts/render-plantuml.sh) 已对 `@startwbs` / `@startgantt` / `@startmindmap` / `@startjson` / `@startyaml` / `@startsalt` **自动跳过单色处理**，保留原生配色，无需手动干预。
- **各图的样式载体**：
  - **WBS** → `<style> wbsDiagram { ... }` + 内联 `[#色]` + `<<类名>>`
  - **思维导图** → `<style> mindmapDiagram { ... }` + 内联 `[#色]` + `<<类名>>`
  - **甘特图** → 内联 `is colored in 前景/边框`、`today ... is colored in #色`、`YYYY-MM-DD is colored in 色`（甘特图**无** `<style>` 作用域）
  - **JSON** → `<style> jsonDiagram { node / arrow / highlight }` + `#highlight ... <<类名>>`
  - **YAML** → `<style> yamlDiagram { node / arrow / highlight }` + `# highlight ... <<类名>>`
  - **Salt** → 无 `<style>` 作用域，保持原生线框外观（渲染脚本仅注入字体与缩放参数），见 [howto/19-salt-diagram.md](../howto/19-salt-diagram.md)
- **配色原则同 UML**：颜色服务于信息（状态/分类/重点），全图控制在 3~4 种以内，浅背景 + 深文字保证对比度，中文务必设 `FontName "Noto Sans SC"`（JSON/YAML）避免方块字。

### WBS `<style>` 示例

```plantuml
<style>
wbsDiagram {
  LineColor #4A90A4
  RoundCorner 8
  .phase { BackgroundColor #DDEEFF }
  .risk  { BackgroundColor #FFDDDD }
  boxless { FontColor #555555 }
}
</style>
```

### 思维导图 `<style>` 示例

```plantuml
<style>
mindmapDiagram {
  node { RoundCorner 12; Padding 8 }
  rootNode { BackgroundColor #2C3E50; FontColor white; FontStyle bold }
  .arch { BackgroundColor #D5F5E3; LineColor #27AE60 }
}
</style>
```

### JSON `<style>` 示例

```plantuml
<style>
jsonDiagram {
  node { BackGroundColor #FDFDFD; LineColor #6B7A8F; FontName "Noto Sans SC"; FontColor #2E3B4E; RoundCorner 8 }
  arrow { LineColor #6B7A8F }
  highlight { BackGroundColor #FFE082; FontColor #7A4F01; FontStyle bold }
  .warn { BackGroundColor #EF5350  FontColor white }
}
</style>
```

### YAML `<style>` 示例

```plantuml
<style>
yamlDiagram {
  node { BackGroundColor #F8FAFC; LineColor #94A3B8; FontColor #1E293B; RoundCorner 8 }
  arrow { LineColor #94A3B8 }
  highlight { BackGroundColor #FDE68A; FontColor #7C2D12; FontStyle bold }
}
</style>
```

> 完整语法与逐项说明见 [syntax-reference.md](./syntax-reference.md) §8 及 [howto/](../howto/) 13~19。

## 九、状态编码：颜色 + 符号冗余（跨图通用）

颜色单独承载状态是脆弱的：灰度打印、色弱读者、以及样式被剥离的渲染环境（只保留结构、丢掉填充色）都会让整条信息一次性丢失。规则：**同一状态必须由「颜色」与「符号」两条通道冗余编码**，任一通道失效时另一条仍可读。

- **典型三态编码**：`✓` 已达成 / 已完成、`◇` 待达成 / 未开始、`⚠` 有风险，配同语义的三档底色（绿 / 灰 / 红）。符号写进元素标签（节点文字、任务名、里程碑标签），颜色由 `<style>` 或内联着色承担；图例里把**符号与色块写在同一行**，读者一次即可建立两条通道的对应。可直接抄的甘特示例见 [howto/14-gantt-diagram.md](../howto/14-gantt-diagram.md) §「里程碑标签必须逐字同串；状态着色要逐条覆盖」。
- **字形必须先实测，不要凭直觉挑符号**。在本技能的渲染路径（PlantUML Server + 渲染脚本注入的 `Noto Sans CJK SC`）上把两组符号放进同一张图实测，结果泾渭分明：

  | 判定 | 符号 | 说明 |
  |------|------|------|
  | ✅ 有字形，可用 | `✓`(U+2713) `◆`(U+25C6) `◇`(U+25C7) `●`(U+25CF) `○`(U+25CB) `▲`(U+25B2) `■`(U+25A0) `★`(U+2605) `☆`(U+2606) `⚠`(U+26A0) | 几何符号族 + U+2713 稳定渲染 |
  | ❌ 渲染成豆腐块 `⊠` | `✔`(U+2714) `✗`(U+2717) `✘`(U+2718) `⚑`(U+2691) `⬤`(U+2B24) | 与 `✓` 只差一个码位的 `✔` 同样无字形 |
  | ❌ 一律禁用 | 所有 emoji：`🟢` `🔴` `✅` `❌` `⏰` `⌛` … | 实测同为豆腐块；且即使某环境有字形，彩色 emoji 内联进 SVG 后的字体依赖不可控 |

  推论：**"打勾"只能用 `✓`**（[howto/13-wbs-diagram.md](../howto/13-wbs-diagram.md) §「带状态色 · 责任人 · 里程碑锚点的交付 WBS」已就 `✓` vs `✔` 给出同一结论，此处做跨图归纳）；**"打叉"不要用 `✗`/`✘`**，未完成 / 失败改用 `○`、`◇`、`■` 或 `⚠` 表达。换一套符号就重渲一次确认字形，别照抄未验证的符号表。

## 十、图例契约：零实例退化 + 双向完备（跨图通用）

图例不是"配色备忘录"，而是图例与图内编码之间的一份**契约**。凡是用颜色/符号承载语义的图（WBS、甘特、思维导图、JSON/YAML 高亮等）都适用下面五条：

1. **只列图内实际出现的编码（零实例不列）**：某编码在本图零实例（例如全图没有"进行中"的条目）→ 图例不写该行，`<style>` 里也不必定义该类。**列出图里不存在的元素是硬缺陷**——读者会拿着图例去图中找一个不存在的东西，并据此怀疑自己漏看了。
2. **图内出现的每种编码都必须有图例行（无遗漏方向）**：契约是双向的，缺行与多行同样是缺陷。
3. **单编码退化为 caption**：按第 1 条裁剪后图例只剩 1 行、已不承载"区分"作用时，把整个 `legend` 换成一句 `caption`，不要留一个单行图例框（框比信息量重）。`caption` 用法见 [howto/13-wbs-diagram.md](../howto/13-wbs-diagram.md) §「用 `caption` 声明"图内为什么缺某类信息"」。
4. **色块与图内声明用同一字面量**：推荐两边都写 6 位十六进制（任务 `is colored in #ADFF2F`、图例 `|<#ADFF2F>|`）。即便 `GreenYellow` 与 `#ADFF2F` 数值相等，"一边色名、一边十六进制"也会被评审读成不一致——原始结论与色名映射表见 [howto/14-gantt-diagram.md](../howto/14-gantt-diagram.md) §「布局与美观技巧」中的"同一个 token"一条，此处并入契约。
5. **改完跑一次确定性自检**（比人眼逐行比对可靠得多）：

```bash
python3 - <图.puml> <<'EOF'
import re, sys, pathlib
src = pathlib.Path(sys.argv[1]).read_text()
m = re.search(r"^legend\b[\s\S]*?^(?:endlegend|end legend)", src, re.M)
legend, body = (m.group(0), src.replace(m.group(0), "")) if m else ("", src)
body = "\n".join(l for l in body.splitlines() if not l.startswith("today"))
up = lambda s: {h.upper() for h in s}
used = up(re.findall(r"is colored in\s+#([0-9A-Fa-f]{6})", body)) | \
       up(re.findall(r"\.\w+\s*\{[^}]*?BackgroundColor\s+#([0-9A-Fa-f]{6})", body, re.S))
shown = up(re.findall(r"<back:#([0-9A-Fa-f]{6})>", legend)) | up(re.findall(r"\|\s*<#([0-9A-Fa-f]{6})>", legend))
print("图内使用但图例缺失:", sorted(used - shown))
print("图例列出但图内零实例:", sorted(shown - used))
EOF
```

**判读规则：**

- **第一行必须是空列表** `[]`。有残留就是第 2 条被违反（图里用了某色却没进图例），直接补图例行。
- **第二行的残留需逐个人工确认来源**，只有两类是合法的：① 该色是 `<style>` 的**默认底色**而非 `.类名` 底色（脚本只识别 `.类名 { BackgroundColor #… }`，识别不到 `milestone { BackGroundColor #… }` 这类元素级默认值）；② 该色来自被脚本按行剔除的 `today` 竖线。**除这两类之外的残留一律是第 1 条被违反，必须删掉该图例行。**
- **描边色不参与比对**：图例色块只呈现填充色，`is colored in 填充/描边` 的斜线后半段与 `LineColor` 都不进 `used` 集合，不必强求出现在图例里。
- 实测样例：对 [howto/14-gantt-diagram.md](../howto/14-gantt-diagram.md) 的「带责任人的交付甘特图」跑该脚本，输出 `图内使用但图例缺失: []` / `图例列出但图内零实例: ['1565C0', 'FFD54F']`——两个残留恰好分别是 `today` 线与 `milestone { BackGroundColor }` 默认底色，属合法；而在同一份源码里人为多写一行零实例图例、删掉一行已用色后，脚本立刻两个方向都报出问题。

> **渲染服务依赖（换后端必复验）**：`<back:#…>` 色块是 HTML/Creole 语法，其渲染支持程度取决于**具体渲染服务**（服务器版本、不同镜像、本地 jar 的实现可能有差异）。更换渲染服务器/后端（如远端 server → 本地 jar，或换一台自建服务器）后，**必须重渲并肉眼复验图例色块与 CJK 字体**——色块渲染成空白、中文变豆腐块都是换后端的高发问题（见 [howto/12-rendering-and-output.md §1.4](../howto/12-rendering-and-output.md)）。

## 十一、语义视觉强弱分层（visual weight）

**权重 = 注意力吸引**：线越粗、色越深，用户越先看它。语义优先级决定权重优先级：**大模块划分 > 小模块划分 > 模块间数据流**——读者先看懂「有哪些大块」，再看「块里有什么」，最后才沿流线读交互；若三者同粗细同深浅（典型病征：全图统一 2px 边框 + 2px 彩色箭头），注意力无落点，图显杂乱。

**两个正交维度**：**粗细+深浅编码权重档**（本节）；**色相编码语义路径**（[large-diagram-playbook.md §2](./large-diagram-playbook.md) 的弱化管线/关键路径着色）。关键路径在流线档内靠色相抬升，**不靠加粗越过结构档**。

默认四档（可增减，但档间须可辨）：

| 档 | 语义对象 | 元素关键字 | LineThickness | LineColor（深浅） |
|----|----------|-----------|---------------|-------------------|
| T1 | 大区/顶层分区边框 | `rectangle`（带标题的 zone 框） | 3 | 最深 `#37474F` |
| T2 | 子模块边框（区内仓库/子系统容器） | `package` | 2 | 中 `#607D8B` |
| T3 | 叶元素边框 | `component`/`cloud`/`database`/`actor` | 1 | 浅 `#90A4AE` |
| T4 | 流线 | 箭头 | 1（默认）/ 关键路径 `[thickness=2]` 封顶 | 最浅 `#A3B1BA` / 关键路径用语义色相 |

**写法（经 PlantUML server 实测：两种紧凑写法都不可靠——嵌套 `<style>` 选择器（`package { package { … } }`）不生效；单行冒号连接属性（`LineThickness 3 : LineColor #…`）在真实大图上解析爆炸、stroke-width 出天文数字。须用扁平选择器 + 多行属性）**——zone 用 `rectangle`、子模块用 `package` 正是为了拿到两个独立选择器：

```plantuml
<style>
rectangle {
  LineThickness 3
  LineColor #37474F
}
package {
  LineThickness 2
  LineColor #607D8B
}
component, cloud, database, actor {
  LineThickness 1
  LineColor #90A4AE
}
arrow {
  LineThickness 1
  LineColor #A3B1BA
}
</style>
```

渲染脚本注入的 `ArrowThickness 1 / BorderThickness 1` 只是 T3/T4 基线；源中全局 `ArrowThickness`/`BorderThickness` 行**不再被剥离**（位于注入块之后，可整体覆盖基线），per-元素档一律走上表 `<style>`。

**自检**：渲染后 `grep -oE 'stroke-width:[0-9.]+' <out>.svg | sort -u` 应见 ≥3 档（实测 T1/T2/T3 = 37.5/25/12.5 @scale4）；肉眼确认大区框明显压得住子模块框、子模块框压得住流线。**反例（07 号组件图 v2 初版）**：zone 与子模块同为 `package` 且全图统一 2px 边框、关键路径 2px 彩线——边框与流线强弱同档，用户纠正「强弱模糊、线框无区分看起来很杂乱」；按本节重映射关键字 + 分档后三档可辨。

## 扩展阅读

- **布局优化技巧**：参见 [layout.md](./layout.md)
- **内容组织与标签规则**：参见 [content.md](./content.md)
- **间距调整**：`skinparam nodesep` / `skinparam ranksep` 参数说明见 [layout.md](./layout.md) §二.4

> **draw-diagram 委派对接**：经前门委派、输入为 SDS 时，`weight_plan` 档位 → 本引擎语法的映射（含复刻类源图实测权重覆盖、几何逼近与偏离声明）以 **[../sds-realization.md](../sds-realization.md)** 为准；本节档位表是**无 SDS 输入**（直接调用本技能）时的默认档。
