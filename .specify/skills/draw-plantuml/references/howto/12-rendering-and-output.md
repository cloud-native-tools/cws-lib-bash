# 渲染、匹配验证与输出指南

> 将 PlantUML 代码渲染为 SVG/PNG 图片，读取生成的图片与用户需求进行匹配比对，微调后组装为最终 HTML 文档。本指南是 [SKILL.md Step 8](../../SKILL.md) 的详细参考。

---

## 一、渲染 PlantUML 为 SVG/PNG

### 1.0 渲染后端与环境准备（首次使用必读）

渲染脚本 `render-plantuml.sh` 支持两种后端，通过 `PLANTUML_BACKEND` 选择（默认 `auto`）：

| 后端 | 触发条件 | 依赖 | 说明 |
|------|---------|------|------|
| **server** | `PLANTUML_SERVER` 可达 | 一个 PlantUML 服务器 + `python3` | 首选；脚本将源码做 Deflate+Base64 编码后 GET `/svg/{enc}`、`/png/{enc}`（官方 PlantUML server 协议） |
| **local** | 服务器不可达且找到本地 jar | `java` + PlantUML jar（+ CJK 字体） | 完全离线；专项图（WBS/甘特/思维导图/JSON/YAML）无需 Graphviz |

`auto` 会先探测服务器，不可达时自动回退到本地 jar。

**默认远程服务器**——脚本默认使用自建的 PlantUML server 渲染表图：

```
http://xuanji-plantuml.aliyun-inc.com:9696/plantuml
```

如需指向其他服务器，设置 `PLANTUML_SERVER=<url>`（URL 以上下文路径结尾，不含 `/svg` 等后缀）。

**自建远程服务器（Docker）**——上述默认服务器由以下 Docker 镜像在主机 `xuanji-plantuml.aliyun-inc.com` 上运行；如需自行部署，可复用相同命令：

```bash
img="reg.docker.alibaba-inc.com/xuanji-images/observability-plantuml:deploy-2026-07-13"
docker pull ${img} && \
docker run -d --name plantuml --restart unless-stopped \
  -p 9696:9696 \
  -p 8080:8080 \
  ${img}
```

> 容器内 PlantUML server 监听 `9696`、上下文路径为 `/plantuml`，故渲染地址为 `http://<host>:9696/plantuml`。该镜像为官方 PlantUML server（1.2026.1），仅支持编码后 GET 渲染，不接受原始文本 POST——渲染脚本已按此协议实现。

**离线（本地 jar）环境准备**——要复现本技能内「推荐测试图」的同等质量成图，需一次性准备：

```bash
# 1) PlantUML jar（放到脚本会自动搜索的任一路径）
#    搜索顺序：$PLANTUML_JAR → ${HOME}/.local/share/plantuml/plantuml.jar
#             → /usr/local/share/plantuml/plantuml.jar → /opt/plantuml/plantuml.jar → /tmp/plantuml.jar
mkdir -p ${HOME}/.local/share/plantuml
curl -sL "https://repo1.maven.org/maven2/net/sourceforge/plantuml/plantuml/1.2026.6/plantuml-1.2026.6.jar" \
  -o ${HOME}/.local/share/plantuml/plantuml.jar      # Maven Central 比 GitHub CDN 稳定

# 2) 中文（CJK）字体——否则中文渲染成豆腐块 □□□
mkdir -p ${HOME}/.local/share/fonts
curl -sL "https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf" \
  -o ${HOME}/.local/share/fonts/NotoSansSC-Regular.otf   # jsdelivr 能正确解析 LFS，github raw 会截断
fc-cache -f ${HOME}/.local/share/fonts

# 3) UML 类图（类/组件/时序/状态等）本地渲染还需 Graphviz：
#    sudo dnf install -y graphviz   （专项 5 图不需要）
```

> 可用 `PLANTUML_BACKEND=local` 强制本地渲染，`PLANTUML_JAR=/path/to.jar` 指定 jar，`PLANTUML_LIMIT_SIZE=16384` 调整像素上限。

### 1.1 渲染脚本

使用渲染脚本将每张图渲染为 PNG（首选）和 SVG：

```bash
bash ${SKILL_HOME}/scripts/render-plantuml.sh diagram-01.puml output_dir 01-system-overview
```

**渲染脚本**：[scripts/render-plantuml.sh](../../scripts/render-plantuml.sh)

### 1.2 SVG/PNG 双策略渲染

该脚本实现双策略渲染：

| 格式 | 策略 | 参数 | 输出尺寸 | 适用场景 |
|------|------|------|----------|----------|
| **PNG** | 自适应 | 脚本计算 | ≤ 4095×4095 | **所有图表（默认首选格式）**——最美观，且在 Preview / Markdown 预览中可直接查看 |
| **SVG** | 最大质量 | `scale 4 + dpi 300` | viewBox ≥ 3840×2160 (4K UHD) | 超宽/超大图（PNG 触及 4096px 上限时）或需任意无损缩放 |

**PNG 自适应算法**：
1. 先渲染 SVG，获取 viewBox 尺寸
2. 从 viewBox 推算图表 base size（= viewBox / SVG_SCALE）
3. 计算最大 scale 使 `base_size × scale ≤ 4095`
4. 若 scale < 1，则固定 scale=1 并降低 DPI：`dpi = 4095 × 300 / base_size`
5. 渲染后验证：若 PNG = 4096×4096 且文件 < 100KB → 判定空白，降级重试

**PlantUML Server PNG 硬上限**：4096×4096。当图表元素过多（>15）时，PNG 质量可能受限，此时应强制使用 SVG。

### 1.3 输出文件

在 `output_dir` 中生成：
- `01-system-overview.puml` — 应用了 SVG 样式块的 PlantUML 源文件（scale 4）
- `01-system-overview.png` — PNG（**首选**，自适应分辨率，≤ 4095×4095，最美观、Preview 可直接查看）
- `01-system-overview.svg` — SVG（矢量、无限缩放；超宽/超大图或需无损缩放时备选）

文件命名：`{nn}-{short-title}`（如 `01-system-overview`）

### 1.4 CJK 渲染

包含 CJK（中文/日文/韩文）文字的图表，还需运行 CJK 渲染配套脚本：

```bash
node ${SKILL_HOME}/scripts/svg-to-png-cjk.cjs <input.svg> <output-cjk.png> 2
```

该脚本在浏览器中使用系统 CJK 字体渲染，确保文字正确显示。详见 [layout.md §六](../guide/layout.md) 中的 CJK 渲染问题详解。

---

## 二、渲染验证

渲染完成后，逐项验证：

1. **SVG 有效性**：`file diagram-01.svg` 应显示 "SVG document"
2. **SVG viewBox**：中等图表的 SVG viewBox 应至少在一个轴上 ≥ 3840（确认 `scale 4 + dpi 300` 已生效）
3. **SVG 无固定尺寸**：确认使用 `viewBox` 而无固定 width/height（确认 `svgDimensionStyle false` 已生效）
4. **PNG 有效性**：`file diagram-01.png` 应显示 "PNG image data" 且两个轴尺寸 ≤ 4095
5. **PNG 非空白**：4000+ 像素图片的文件大小应 > 100KB（空白的 4096×4096 ≈ 60KB）
6. **脚本输出**：应输出 "Rendering Complete" 且无 WARNING

---

## 三、匹配与微调

### 3.1 读取渲染图片

使用 `Read` 工具读取生成的 SVG 或 PNG 图片文件，获取渲染后的视觉效果进行理解。

### 3.2 与用户需求匹配比对

将渲染图片与最初用户输入的要求进行比对，检查：

- [ ] 所有用户要求的元素是否都已包含
- [ ] 元素间的关系是否正确表达
- [ ] 图表类型是否合适
- [ ] 布局是否清晰可读（无交叉、无重叠）
- [ ] 标签是否清晰可辨（≤10 字符，长描述有 note 补充）
- [ ] 样式是否统一（skinparam 一致）
- [ ] 图片复刻场景：源图所有元素和注释是否完整还原
- [ ] 无孤立元素（每个元素至少有一条关系）

### 3.3 微调与重新渲染

发现差异时：
1. 修改 PlantUML 代码（调整元素、关系、布局或样式）
2. 重新渲染
3. 再次读取图片验证
4. 重复直到匹配用户需求

---

## 四、组装最终 HTML 文档

将所有渲染的图表和文字组合为**单个 HTML 文档**，展示架构图并嵌入渲染图片（**默认优先 PNG**，而非原始 PlantUML 代码）。

### 4.1 HTML 模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>[System Name] Architecture</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 960px; margin: 0 auto; padding: 2rem; line-height: 1.6; color: #333; }
    h1 { border-bottom: 2px solid #eee; padding-bottom: 0.5rem; }
    h2 { margin-top: 2rem; color: #2c3e50; }
    h3 { color: #34495e; }
    .diagram { text-align: center; margin: 1.5rem 0; }
    .diagram img { max-width: 100%; height: auto; border: 1px solid #eee; border-radius: 4px; }
    .explanation { background: #f8f9fa; padding: 1rem; border-radius: 4px; margin: 1rem 0; }
  </style>
</head>
<body>
  <h1>[System Name] Architecture</h1>
  <section>
    <h2>Overview</h2>
    <p>[High-level system description]</p>
  </section>
  <section>
    <h2>Architecture Diagrams</h2>
    <h3>[Diagram 1 Title]</h3>
    <p>[Context]</p>
    <div class="diagram">
      <img src="01-diagram-name.png" alt="[Diagram 1 Title]" />
    </div>
    <div class="explanation">
      [Explanation + Rationale]
    </div>
    <h3>[Diagram 2 Title]</h3>
    ...
  </section>
  <section>
    <h2>Summary</h2>
    <p>[Key architectural decisions and trade-offs]</p>
  </section>
</body>
</html>
```

### 4.2 HTML 组装规则

- 使用**相对路径**引用图片文件（图表和 HTML 在同一输出目录中）
- **默认优先引用 PNG**（`<img src="….png" />`）——最美观，且在各类 Preview / Markdown 预览中可直接查看
- 仅当图表过宽/过大（PNG 触及 4096px 上限）或需任意无损缩放时，改用 SVG；单图也可内联嵌入 `<svg>...</svg>`
- 确保所有图片有有意义的 `alt` 属性
- HTML 应自包含，可直接在浏览器中打开 `.html` 文件查看

### 4.3 Markdown 嵌入场景（最佳实践：PNG 内嵌 + SVG 新标签链接）

当图表要**嵌入 Markdown 文档**（README / 设计文档 / Wiki 等）而非独立 HTML 时，目标是「**默认看 PNG，细节不够可开 SVG 无损放大**」，同时 SVG/PNG 双格式必须产出（`render-plantuml.sh` 默认双出）、与文档同目录。

> ⚠️ **路径识别不一致陷阱（关键）**：Markdown 图片 `![](x.png)` 走 **Markdown 路径识别管线**，而内联 HTML `<a href="x.svg">` 走 **浏览器 HTML 路径识别**。二者是**不同的解析管线**——在会**代理/改写** Markdown 图片 URL（如 GitHub 的 camo 代理、静态站生成器的 base 前缀/扩展名改写）但**原样透传** raw HTML `href` 的渲染器上，同一个相对路径经两条管线会**指向不同位置**。**因此绝不要「Markdown 嵌 PNG + 原始 HTML 链 SVG」并假设两者路径写法相同。** 用下面**同一机制**的写法规避：

- **推荐（路径一致·首选）——全用内联 HTML，一条 `<a>` 包住 `<img>`**：`src`（PNG）与 `href`（SVG）都走 HTML 解析，**同一套相对路径基准、不跨管线**；且点图即开 SVG 新标签，天然满足「放大看细节」：

  ```markdown
  <p align="center">
    <a href="diagrams/01-overview.svg" target="_blank" rel="noopener">
      <img src="diagrams/01-overview.png" alt="图1 · 系统全景">
    </a>
    <br><sub>🔍 点击图片在新标签页打开 SVG 矢量大图，可无损放大</sub>
  </p>
  ```

- **回退（渲染器会剥离原始 HTML 时）——全用纯 Markdown**：`![alt](x.png)` + `[🔍 SVG 大图](x.svg)`，**两者都走 Markdown 管线、路径一致**；代价是纯 Markdown 链接**无法强制新标签**（同标签打开）。

  ```markdown
  ![图1 · 系统全景](diagrams/01-overview.png)

  🔍 细节不够？[打开 SVG 矢量大图](diagrams/01-overview.svg)（无损放大）
  ```

- **原则**：PNG 与 SVG 引用**用同一种机制**（要么全 HTML、要么全 Markdown），保证两条路径经**同一解析管线**、写法一致；`rel="noopener"` 保证 `target="_blank"` 安全。若确需混用，**必须在目标渲染器里分别验证两条路径**并各自调整。

---

## 五、输出要求

- 输出为**单个 HTML 文档**（`.html` 文件），包含渲染的 SVG/PNG 图表
- 图表**必须**通过 [render-plantuml.sh](../../scripts/render-plantuml.sh) 脚本渲染——最终输出中**不要**嵌入原始 PlantUML 文本
- SVG/PNG 图片文件与 HTML 保存在同一输出目录中
- HTML 通过相对路径引用图片，**默认优先 PNG**（如 `<img src="01-overview.png" />`）；超宽/超大图或需无损缩放时改用 SVG
- 单图输出时，内联 SVG 嵌入可作为替代方案
- **嵌入 Markdown 文档时**（非独立 HTML）：默认看 PNG、细节不够可开 SVG 无损放大，SVG/PNG 双格式必须同时产出；**PNG 与 SVG 引用须用同一路径解析机制**（首选全内联 HTML「`<a target=_blank>` 包 `<img>`」，回退全纯 Markdown）——切勿 Markdown 嵌图 + HTML 链接混用而假设路径一致（见 §4.3 路径识别不一致陷阱）
- PlantUML 源文件（`.puml`）也应保存以供未来编辑/重新生成
- HTML 语义元素中的文字描述（标题、段落、列表）
- 默认语言：遵循用户首选语言（本项目默认中文）
- 每张图至少包含：标题、渲染图片和简要说明

---

## 六、交付前质量检查清单

交付最终文档前，逐项验证：

### 渲染与文件
- [ ] 所有 PlantUML 源文件（`.puml`）有匹配的 `@startuml` / `@enduml`
- [ ] 每张图已通过 `render-plantuml.sh` 成功渲染为 SVG/PNG
- [ ] SVG 文件是有效的 XML（通过 `file` 命令验证）
- [ ] SVG 文件使用 `viewBox` 而无固定 width/height
- [ ] SVG viewBox 至少在一个轴上 ≥ 3840
- [ ] PNG 文件尺寸 ≤ 4095×4095
- [ ] PNG 文件非空白（大图片 > 100KB）
- [ ] 脚本输出 "Rendering Complete" 且无 WARNING
- [ ] `.puml` 源文件包含 `scale 4 + dpi 300`

### 内容与质量
- [ ] 用户绘制意图已完全理解（通过 Step 1 的分析或交互式问答）
- [ ] 所有图片引用内容已提取并映射到 UML 元素（如适用）
- [ ] 每张图使用了正确的 UML 类型
- [ ] 没有图表超过 7 个核心元素（可接受 ≤12；硬上限 15）；过大则拆分
- [ ] 所有元素名称和关系标签 ≤10 字符；更长的描述使用 `note` 元素
- [ ] 别名和标签是人类可读的（非代码标识符）
- [ ] 关系标签描述了交互方式（如 "uses via HTTP" 而非仅 "uses"）
- [ ] 无孤立元素（每个元素至少有一条关系）
- [ ] `skinparam` 在所有图表中提供一致的视觉样式（标准文档用单色；需要彩色时省略）

### 嵌入 Markdown（如适用）
- [ ] PNG 与 SVG 引用**用同一机制**（全内联 HTML `<a target=_blank rel=noopener>` 包 `<img>`，或全纯 Markdown）——未把 Markdown 嵌图与 HTML 链接混用
- [ ] 默认展示 PNG，可点击/链接打开 SVG 无损放大
- [ ] SVG 与 PNG 双格式齐备、与文档同目录，两条路径经同一解析管线、写法一致

### HTML 输出
- [ ] HTML 用正确的相对路径引用所有图表图片
- [ ] 文字说明引用了图表中的具体元素
- [ ] 文档有从总览到细节的清晰叙事流
- [ ] HTML 文件在浏览器中正确打开并显示所有图表
