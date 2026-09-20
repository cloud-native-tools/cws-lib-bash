# mxGraph Format — 产物格式与必备 XML 结构

本文件只回答一件事：**把已定的语义与几何写成 draw.io / mxGraph 能读的 XML，其语法是什么**。任何关于「画成什么结构、用什么颜色、选哪个引擎」的问题由 owner 文件回答（见文末指针），本文件不得复写。

**证据来源（本文所有结构性结论的出处，均为官方文档，2026-09 核对）**：

- `mxfile.xsd` — draw.io 官方 XML Schema，明确「intended for use by AI systems to validate generated diagram files」：https://github.com/jgraph/drawio-mcp/blob/main/shared/mxfile.xsd
- `style-reference.md` — 官方样式与形状完整参考，声明「All data was extracted from the draw.io source code」：https://github.com/jgraph/drawio-mcp/blob/main/shared/style-reference.md
- `xml-reference.md` — 官方规范 XML 生成参考，是 draw.io MCP 各 prompt 的唯一真源：https://github.com/jgraph/drawio-mcp/blob/main/shared/xml-reference.md
- 生成与校验总纲：https://www.drawio.com/docs/reference/diagram-generation/

> **本文件不复制官方样式目录。** 形状库、样式 key 全集、配色板、HTML 标签白名单、perimeter 取值全表的 owner 是上述 `style-reference.md`；此处只登记**合成一份有效文件所必需**的结构事实与硬性规则。凡官方文档未给出的取值，一律记入 §9 未决项，**不按「合理长相」推断**。

## 1. 产物格式与两种可接受形态

产物是 **mxGraph XML**，落地为 `.drawio` 文件。draw.io 接受两种形态：

| 形态 | 结构 | 何时用 |
|------|------|--------|
| **完整形** | `mxfile > diagram > mxGraphModel > root > mxCell…` | 需要多页（`mxfile` 下可挂多个 `diagram`）、需要文件级变量 `vars`、**或需要 XSD 校验**（见 §8 注） |
| **简化形** | 只给 `mxGraphModel > root > mxCell…` | 单页场景。draw.io 打开裸 `mxGraphModel` 时**自动补齐** `mxfile` / `diagram` 外层。官方**推荐 AI 生成用此形**（嵌套层少、无需页元数据） |

**一律未压缩。** 压缩态是 `<diagram>` 内承载 deflate + Base64 负载（顺序：`encodeURIComponent` → raw DEFLATE，无 zlib 头 → Base64）。**生成器绝不产出压缩内容**，也不设 `compressed="true"`：压缩态更耗 token、不可读、无法在不解压的情况下校验或调试。读入既有压缩文件才涉及解压，那不属本文档的生成路径。

## 2. 必备结构

### 2.1 两根结构 cell（不可省）与 cell 的四种角色

| 根 cell | 作用 |
|---------|------|
| `<mxCell id="0"/>` | 根容器；**唯一可以没有 `parent` 的 cell** |
| `<mxCell id="1" parent="0"/>` | 默认图层；所有可见 cell 挂在其下 |

`mxCell` 是**万能元素**，角色由属性决定，四种互不相同：

| 角色 | 判定属性 | `parent` | `vertex`/`edge` |
|------|---------|----------|-----------------|
| 根容器 | `id="0"` | **无** | 都无 |
| 图层 | `parent="0"` | `"0"` | **都无**（`value` = 图层名） |
| 内容 cell（形状） | `vertex="1"` | `"1"` 或 group/layer id | 只有 `vertex` |
| 内容 cell（连线） | `edge="1"` | `"1"` 或 group/layer id | 只有 `edge` |

追加图层 = 再写一个 `parent="0"` 且**不带** `vertex`/`edge` 的 `mxCell`。

> **术语约定（§8 自检清单据此判定）**：**「内容 cell」= 带 `vertex="1"` 或 `edge="1"` 的 cell**；根容器与图层**不是**内容 cell，故「恰有 vertex 或 edge 之一」这条只约束内容 cell。

### 2.2 `parent` 规则（**vertex 与 edge 同样适用**）

**所有内容 cell——形状与连线都要——必须带 `parent`**，取值为 `"1"`（默认图层）或所属 group/layer 的 id。官方校验清单第 6 条：「Every cell (except `id="0"`) has a valid `parent` referencing an existing cell」。

> 这是对本技能 S1f 草稿的**更正之一**：草稿的最小骨架给了 vertex 的 `parent="1"` 却漏了 edge 的 `parent`，并把「edge 是否需要 `parent`」列为高优先未决项。XSD 与官方校验清单一致确证：**需要**。

### 2.3 Vertex（节点）

- `vertex="1"`
- `parent="1"`（或 group id）
- `value="<标签文本>"`
- 子元素 `<mxGeometry x= y= width= height= as="geometry"/>`

### 2.4 Edge（连线）

- `edge="1"`，与 `vertex="1"` **互斥**
- `parent="1"`（同上）
- `source=` / `target=` 指向两端 vertex 的 `id`，必须引用同图内已存在的 vertex
- 子元素 `<mxGeometry relative="1" as="geometry"/>`
- **不需要手写路径点**：只给两端端点，走线由引擎计算（走线质量与可选的避障/重布 pass 见 `./render-and-export.md` §3）
- 无端点的浮空连线才需要显式点：`<mxPoint x= y= as="sourcePoint"/>` / `as="targetPoint"`
- 需要固定折线时才用 `<Array as="points">` 装 waypoint（官方建议**不要**加：「Do NOT add `<Array as="points">` waypoints. Edges are routed automatically.」）

### 2.5 `id`

**每个顶层 cell 必须有图内唯一、可被引用的 `id`**（`source`/`target`/`parent` 都以 id 引用）。任意字符串都合法（`"2"`、`"node-1"`、`"abc123"` 皆可）。

**唯一例外**：被 `UserObject` / `object` 包装的 `mxCell` **不带自己的 id**——id 由包装元素承载（见 §3.2）。故 §8 清单第 5、6 项对这类文件的判定对象是**包装元素的 id**，不是内嵌 `mxCell`。

### 2.6 `mxGeometry` 的 `as="geometry"`（必需标记）

`mxGeometry` 作为子元素**必须带 `as="geometry"`** 才被识别为该 cell 的几何——XSD 把该属性声明为 `fixed="geometry"`。

> 这是对本技能 S1f 草稿的**更正之二**：草稿骨架写作 `<mxGeometry x="0" y="0" width="120" height="60"/>`，漏了 `as="geometry"`，并把「是否需要额外标记属性」列为未决项。现已确证：**必需**。

同类固定标记还有：`<Array as="points">`（waypoint 列表）、`<mxRectangle as="alternateBounds">`（可折叠容器的备用边界）、`<mxPoint as="offset">`（标签像素偏移）。

### 2.7 几何取值语义

| 场景 | 取值 |
|------|------|
| vertex | `x`/`y` = 左上角绝对坐标（相对父容器）；`width`/`height` = 像素尺寸，**vertex 必需** |
| edge（`relative="1"`） | `x` = 沿连线的位置，`-1.0`（近 source）到 `1.0`（近 target），`0` = 中点；`y` = 垂直方向像素偏移 |
| group 的子元素 | 坐标**相对父容器**，不是相对画布 |
| 坐标系 | 原点 `(0,0)` 在**左上角**，x 向右增、y 向下增；不得出现负尺寸 |

## 3. 标签与元数据载体

### 3.1 标签走 `value`

- `value` 承载 cell 的可见文字，可以是纯文本，也可以在 `style` 含 `html=1` 时承载 HTML。
- `value` 里的 HTML **必须 XML 转义**：`&lt;` `&gt;` `&amp;` `&quot;`。
- HTML 标签支持面（`b` `i` `u` `br` `p` `div` `table` `hr` `font` `span` 及内联 style）owner 是官方 `style-reference.md` §9，本文件不复制。
- edge 的标签同样写在 edge cell 的 `value` 上，位置由其 `mxGeometry` 的 `x`/`y`（见 §2.7）控制。

### 3.2 自定义元数据走 `UserObject` / `object`

需要携带自定义键值（供「Edit Data」对话框、数据驱动图、链接、tooltip 使用）时，用包装元素：

```xml
<UserObject id="srv1" label="Web Server" tooltip="Production web server" ip="10.0.1.10">
  <mxCell style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">
    <mxGeometry x="100" y="100" width="140" height="70" as="geometry"/>
  </mxCell>
</UserObject>
```

- `object` 与 `UserObject` 等价可互换；`id` 由**包装元素**承载，**嵌套的 `mxCell` 不带自己的 id**（见 §2.5 例外条款）。
- 显示文字用包装元素的 `label`（**替代** `mxCell` 的 `value`）。
- 其它标准属性：`link`（超链接）、`tags`（空格分隔）、`tooltip`、`placeholders`。
- 允许任意额外属性（XSD 以 `anyAttribute` 放行）。
- **占位符替换需显式开启**：`placeholders="1"`（包装元素上，或普通 `mxCell` 的 style 属性）。未开启时 `%name%` 按字面文本渲染。
- 文件级变量走 `mxfile` 的 `vars` 属性（JSON 对象），**仅完整形可用**，简化形无此能力。

## 4. 样式串语法

样式是 cell 上的**字符串属性** `style`，不是嵌套元素：

```
[形状名;]key1=value1;key2=value2;
```

- 开头可放**裸 token**（无 `=`）：形状名或样式类名，例如 `ellipse;whiteSpace=wrap;html=1;`。可放多个裸 token 以继承样式类。
- key 与 value **区分大小写**；`=` 与 `;` 两侧**不留空格**。
- 布尔值用 `0` / `1`（**不是** true/false）。
- 颜色用 `#RRGGBB`（带 `#`）、`#RRGGBBAA`、`none`、`default`。
- 结尾 `;` 是惯例，非强制。
- **未知 key 被静默忽略**——写错 key 不会报错，只会没效果。
- 已确证的常用 key（示例形态）：`rounded`、`whiteSpace=wrap`、`html=1`、`fillColor`、`strokeColor`、`endArrow=classic`、`edgeStyle=orthogonalEdgeStyle`、`swimlane`、`startSize`。
- **key 全集与取值 owner = 官方 `style-reference.md` §4–§7**（填充/描边、形状几何、文本标签、连线属性、箭头标记、连接点、容器泳道、图片、手绘风、行为属性、edge 路由算法、perimeter 类型、预定义样式类、配色板）。本文件不复制该目录。
- **`fillColor` / `strokeColor` 的取值**是配色决策，owner 是前门的样式指引（尚未落盘，见文末指针）；本文件只声明这两个 key 存在于样式串上，**全文不出现任何颜色字面量**。

## 5. 容器与分组（§7 规则 6、§8 清单第 14 项的构造依据）

分组靠 **`parent` 引用**表达，不需要额外的包装元素：

- **容器/分组本身是一个 vertex**：`vertex="1"`，样式里带 `swimlane`（或 `container=1`），照常携带自己的 `mxGeometry`。
- **子元素把 `parent` 指向该容器的 id**（不再是 `"1"`），且**坐标相对父容器**，不是相对画布。
- 容器可嵌套：内层容器的 `parent` 指向外层容器 id，坐标同样逐层相对。
- 已确证的容器相关样式 key：`swimlane`（裸 token）、`startSize`（标题栏高度，默认 `23`）、`container`、`collapsible`、`recursiveResize`、`childLayout`。完整目录 owner 是官方 `style-reference.md` §4.7 与 §11。
- **不需要生成 `<mxRectangle as="alternateBounds">`**：官方明说 AI 生成器一般无需产出它，用户折叠容器时 draw.io 自行添加。

下例是**可直接解析的 `<root>` 片段**（省略了外层 `mxfile`/`diagram`/`mxGraphModel`，补齐方式见 §6），且**不含任何注释**——真实产物同样不得有注释（§7 第 1 条）：

```xml
<root>
  <mxCell id="0"/>
  <mxCell id="1" parent="0"/>
  <mxCell id="zoneA" value="Zone A" style="swimlane;startSize=25;html=1;" vertex="1" parent="1">
    <mxGeometry x="50" y="50" width="300" height="200" as="geometry"/>
  </mxCell>
  <mxCell id="nodeInA" value="Node" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="zoneA">
    <mxGeometry x="100" y="60" width="120" height="60" as="geometry"/>
  </mxCell>
</root>
```

上例中 `nodeInA` 的 `x=100 y=60` 是**相对 `zoneA` 左上角**的偏移。跨容器的连线仍写在 `parent="1"` 上，`source`/`target` 指向两个子节点 id。

> **§3.2 的 `UserObject` 示例同理是片段**（只给包装元素本身，未含 `<root>` 与两根结构 cell）；拼接进完整文档时，包装元素**直接作为 `<root>` 的子元素**，与 `mxCell` 平级。

## 6. 最小骨架（可直接作为生成起点）

简化形，单页，两个 vertex + 一条 edge，**不含任何注释**（§7 第 1 条：真实产物中不得出现 XML 注释）。此形态已实测：包进 `<mxfile><diagram>…</diagram></mxfile>` 后**通过官方 `mxfile.xsd` 校验**（§8 注、§9 第 1 项）。

```xml
<mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100" math="0" shadow="0">
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <mxCell id="2" value="A" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="40" y="40" width="140" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="3" value="B" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">
      <mxGeometry x="220" y="160" width="140" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="e1" value="" style="endArrow=classic;html=1;" edge="1" parent="1" source="2" target="3">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>
```

`mxGraphModel` 上的画布属性**全部可选**，缺省值：`pageWidth=850`、`pageHeight=1100`、`pageScale=1`、`grid=1`、`gridSize=10`、`guides/tooltips/connect/arrows/fold/page=1`、`math=0`、`shadow=0`。`mxfile` 上的 `host`/`modified`/`agent`/`version`/`etag`/`type`/`pages` 亦全部可选；`diagram` 的 `id` 建议给（多页时必须唯一），`name` 省略时默认 `Page-N`。

### 6.1 坐标从哪来（**兜底公式，不是版面规划**）

官方给 AI 的指引是**用固定网格公式粗放坐标、不要在推理里做版面算术**：

- 列 `x = col_index * 180 + 40`（col 0 = 40，col 1 = 220，col 2 = 400…）
- 行 `y = row_index * 120 + 40`（row 0 = 40，row 1 = 160，row 2 = 280…）
- 常用尺寸：矩形 `140×60`、菱形 `140×80`、圆形 `60×60`、文档 `120×80`、圆柱 `100×70`

**这组数值是引擎侧的兜底默认，不是版面决策。** 优先级明确：

1. **前门给出了计算好的几何** → **一律以前门为准**，本公式不适用。
2. 前门只给了逻辑结构、未给几何 → 用本公式粗放铺点，需要规范层级版面或避障走线时交给布局/走线 pass（`./render-and-export.md` §3–§4），**不要自己解算坐标**。

版面**规划**决策（该不该自由版面、该多密、该分几组、谁在谁旁边）始终归前门（指针见 §10）；本文件只提供「没有几何时怎么给出一组能用的坐标」这一引擎侧兜底。

## 7. 生成硬性规则（well-formedness）

1. **绝不输出任何 XML 注释 `<!-- -->`**：官方明令禁止——浪费 token、可能引发解析错误、对图形无语义。
2. **属性值中的特殊字符必须转义**：`&amp;` `&lt;` `&gt;` `&quot;`。
3. **`id` 图内唯一**（`UserObject` 包装场景见 §2.5 例外）。
4. **`vertex="1"` 与 `edge="1"` 互斥**，二者只能有其一；根容器与图层**两者都不带**。
5. **非矩形形状必须配匹配的 `perimeter=`**（例：`ellipse` 需 `perimeter=ellipsePerimeter`），否则连接点计算错位。已确证的取值只有 `rectanglePerimeter`（默认）与 `ellipsePerimeter`；**其余取值查官方 `style-reference.md` §6，不按命名长相推断**。
6. **group 子元素坐标相对父容器**（构造见 §5）。
7. **一律未压缩、绝不加 `compressed="true"`**。

## 8. 交付前自检清单

生成后逐项核。第 1–14 项是官方 14 项校验清单的**可机械核对子集**，第 15–16 项是本技能**另加**的两条（分别来自官方 `xml-reference.md` 的禁注释规则与 §1 的未压缩要求）——共 16 行，不是官方清单的子集而是「官方 14 项 + 2 条追加」。

> **XSD 校验的适用范围（实测结论）**：官方 `mxfile.xsd` **只把 `mxfile` 声明为全局元素**，故 `xmllint --schema mxfile.xsd` **只能校验完整形**。对简化形（裸 `mxGraphModel`）直接校验会报 `No matching global declaration available for the validation root` —— 这**不是**产物有错，而是该形态无对应的全局声明。要 XSD 校验简化形，先把它包进 `<mxfile><diagram>…</diagram></mxfile>` 再校验；或对简化形只做良构性 + 本清单校验。「官方推荐生成用简化形」（§1）与「官方 XSD 可校验」两条**不能直接组合**，须按本条换算。

| # | 检查项 | 来源 |
|---|--------|------|
| 1 | XML 良构，特殊字符已转义 | 官方 |
| 2 | 根是 `<mxfile>`（完整形）或 `<mxGraphModel>`（简化形）；完整形下至少一个 `<diagram>` | 官方 |
| 3 | 每个 `diagram` 的 `id` 唯一 | 官方 |
| 4 | 含 `<mxCell id="0"/>` 与 `<mxCell id="1" parent="0"/>` | 官方 |
| 5 | 所有顶层 cell `id` 图内唯一（`UserObject` 场景取包装元素的 id） | 官方 + §2.5 |
| 6 | 除 `id="0"` 外，每个 cell 的 `parent` 都指向已存在的 cell | 官方 |
| 7 | 每个**内容 cell**（= 带 `vertex`/`edge` 者）恰有 `vertex="1"` 或 `edge="1"` 之一；根容器与图层两者都不带 | 官方 + §2.1 术语 |
| 8 | edge 的 `source` / `target` 指向已存在的 vertex id | 官方 |
| 9 | vertex 的 `mxGeometry` 带 `x`/`y`/`width`/`height`；edge 的带 `relative="1"`；**两者都带 `as="geometry"`** | 官方 + §2.6 |
| 10 | style 串为 `key=value;` 形，key/value 合法 | 官方 |
| 11 | 非矩形形状的 `perimeter` 与形状匹配 | 官方 |
| 12 | `value` 中的 HTML 已 XML 转义 | 官方 |
| 13 | 坐标 x 右增、y 下增，无负尺寸 | 官方 |
| 14 | group 子元素坐标相对 group | 官方 |
| 15 | **文件内无任何 `<!--` 注释** | 追加（官方 `xml-reference.md`） |
| 16 | **无 `compressed="true"`，`<diagram>` 内无 Base64 负载** | 追加（§1） |

## 9. 未决项（拒绝臆造；官方文档未能确证的细节）

原 S1f 草稿的 **7 项** XML 未决项处置如下 —— **5 项确证消解**（外层容器元素、edge 的 `parent`、文本载体、`mxGeometry` 标记、文件级属性），**1 项转为「指向 owner」而非本地登记**（完整样式 key 目录 → 官方 `style-reference.md`），**1 项部分消解后仍开放**（连线样式 key：`edgeStyle`/`endArrow` 已确证存在，取值全表仍归 owner）。合计 5 + 1 + 1 = 7。另**新增 1 项**实测缺口：

1. **真实渲染/导出验证未做**：本机无 draw.io Desktop / CLI，也无既有 `.drawio` 样本。已完成的验证是**结构与 schema 层**——按本文件生成的一份完整形产物**通过官方 `mxfile.xsd` 校验**（`xmllint` exit 0，报 `validates`），且 §8 清单 16 项中适用的全部通过；简化形良构但**不可 XSD 校验**（§8 注）。**未完成**的是一次真实导出（`.drawio` → SVG/PNG/PDF）与各渲染路径的实际接受面。首次实际出图时应把 §8 清单跑一遍并核对导出结果；若与文档不符，**以实测为准**并经 `improve-skills` 修订本文件。
2. **连线与形状的样式取值全表**不在本文件登记（`edgeStyle` 路由算法枚举、箭头标记枚举、连接点 key、`perimeter` 取值全表、形状库）—— owner 是官方 `style-reference.md` §3、§4.4–§4.6、§5、§6；本技能按需查阅，不复制。

## 10. 语义层与引擎选择指针（本文件不承载）

- 语义模型（实体、层级、结构、关联；SDS/LDM schema）→ `skills/draw-diagram/references/semantic-model.md`（**现存**）
- **引擎选择**（何时由前门选到本引擎、`drawio` ↔ `excalidraw` 优先序）→ `skills/draw-diagram/references/routing-matrix.md`（**现存**）
- 语义分析、图类选择、版面规划与自由度判据、样式配色取值、内容措辞、类专属约定 → 前门 `skills/draw-diagram/SKILL.md`（**现存**）。其**专章参考文件**（`references/howto/*`、`references/guide/*`、`references/document/*`）由 stage S1d 规划、**尚未落盘**，故此处不预建具体路径；落盘前一律回前门 `SKILL.md`
- 渲染路径、CLI 导出、布局与走线 pass → `./render-and-export.md`（同技能内）
