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
skinparam defaultFontSize 14
skinparam defaultFontName "Arial, Helvetica, sans-serif"
skinparam padding 8
skinparam ArrowThickness 2
skinparam BorderThickness 2

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
| `skinparam defaultFontSize 14` | 默认字体 14pt，配合 scale 4 保证文字可读性 | 所有图表 |
| `skinparam defaultFontName "Arial, ..."` | 使用无衬线字体，渲染清晰抗锯齿 | 所有图表 |
| `skinparam padding 8` | 元素内边距 8px，避免内容拥挤贴边 | 所有图表 |
| `skinparam ArrowThickness 2` | 箭头线条加粗为 2px，配合放大后保持视觉清晰 | 所有图表 |
| `skinparam BorderThickness 2` | 边框线条加粗为 2px，避免放大后边框过细 | 所有图表 |
| `skinparam svgDimensionStyle false` | SVG 不内联 width/height，使用 viewBox 实现无损缩放 | 所有图表（SVG） |
| `skinparam svgLinkTarget _blank` | SVG 中的超链接在新窗口打开 | 所有图表（SVG） |
| `skinparam actorStyle awesome` | Actor 使用 FontAwesome 风格图标 | 仅用例图/含 actor 的图 |

## 七、样式校验要点

在完成 PlantUML 代码后，逐项检查：

1. **布局方向**：确认 `top to bottom direction` 仅在类图/组件图/部署图中使用（其他图类型不应出现此指令）
2. **通用 skinparam**：确认通用 skinparam（shadowing、roundCorner）全部存在且值正确；确认色彩模式选择正确（单色图加 `monochrome true`，彩色图省略）
3. **高质量渲染 skinparam**：确认 `dpi 300`、`scale 4`、`defaultFontSize 14`、`defaultFontName`、`padding 8`、`ArrowThickness 2`、`BorderThickness 2` 全部存在
4. **SVG 优化 skinparam**：确认 `svgDimensionStyle false` 和 `svgLinkTarget _blank` 存在
5. **条件 skinparam**：如图表含 actor 或为用例图，确认 `actorStyle awesome` 已添加
6. **位置**：所有样式配置必须在 `@startuml` 之后、图表元素定义之前
7. **无冲突**：确认图表内容中没有覆盖上述 skinparam 的重复声明
8. **PNG 安全**：确认渲染脚本输出无 WARNING（表示 PNG 未触发 4096 硬上限）

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

## 扩展阅读

- **布局优化技巧**：参见 [layout.md](./layout.md)
- **内容组织与标签规则**：参见 [content.md](./content.md)
- **间距调整**：`skinparam nodesep` / `skinparam ranksep` 参数说明见 [layout.md](./layout.md) §二.4
