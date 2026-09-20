# 渲染、匹配验证与输出（12）

## 1. 渲染

```bash
skills/draw-mermaid/scripts/render-mermaid.sh figure-01-order-flow.mmd figures/ figure-01-order-flow
```

- 同时产出 `figure-01-order-flow.svg` 与 `.png`（源 `.mmd` 一并保存）；
- **远端渲染优先（默认）**：后端默认 `MERMAID_BACKEND=server`（mermaid.ink）——无需下载/配置任何本地渲染工具；
- 本地渲染（mermaid-cli）**必须先在用户确认后**以 `MERMAID_BACKEND=local` 显式启用；远端不可用时脚本会询问（TTY）或打印指引退出（非 TTY）——agent 必须先询问用户，获确认后再以 `MERMAID_BACKEND=local` 重试，**绝不静默下载/安装本地工具链**；
- 服务器地址可用 `MERMAID_SERVER=...` 指定（兼容 mermaid.ink 协议的内网服务）；
- **内网自建渲染服务器**：仿照 plantuml-server 容器模式，技能内自带完整部署包 `../server/`（Dockerfile + server.js + docker-run.sh + README）——构建镜像、`-p 9696:9696` 运行、`export MERMAID_SERVER=http://<内网主机>:9696` 即接入；协议为 mermaid.ink 兼容的 `pako:` state（`/svg/pako:{b64}`、`/img/pako:{b64}?type=png`）；详见 `../server/README.md`；
- 本地后端需 Chrome（puppeteer）：`PUPPETEER_EXECUTABLE_PATH=...` 指定；
- PNG 失败时用 `svg-to-png-cjk.cjs` 从 SVG 转：`node svg-to-png-cjk.cjs x.svg x.png 2`；
- **已知服务端限制**：sequence 图的子配置（`actorFontSize` / `messageFontSize` / `noteFontSize` 等）会被 mermaid.ink 服务器忽略，统一按默认值（约 16px）渲染——不要在远端后端上反复调试这些字号；需要精确控制时经用户同意切本地后端，或在 HTML 层缩放显示。

## 2. 匹配与微调

1. 渲染后 **Read 图片**（PNG/SVG）与用户要求比对；
2. 检查：元素齐全？方向/层级对？标签是否截断/溢出？配色符合样式规范？
3. 差异 → 微调 `.mmd` 重渲（文件已保存，直接改）；
4. 图集逐图检查：自足性、交叉引用、跨图一致（配色/字号/编号）；
5. **密集图的有效字号量测**：看脚本报告的 SVG viewBox 宽与 PNG 宽——PNG 较窄（<1200px）且边框/文字密集时，**放大 zoom 无效**（画布同比放大，有效字号不变），改两招：① 上调 `themeVariables.fontSize`（时序图用 sequence 的 `actorFontSize`/`messageFontSize`/`noteFontSize`）重渲；② HTML 内改引 SVG 并给足显示宽度（`<img src="x.svg" width="1400">`）。任何密集图（组件/部署/时序）都可用 `measure-svg-layout.py <x.svg> --display-width <目标显示宽>` 量有效字号（默认阈值 12px），低于阈值即按上处理——该脚本不只服务于 WBS/甘特。

## 3. 质量检查清单

- [ ] 每图：标题 + 渲染图 + 简要说明；
- [ ] 引用与源文件同目录、相对路径；
- [ ] PNG 与 SVG 同时产出；
- [ ] 图集交叉引用一致（`▶ 见图N` 指向存在）；
- [ ] WBS/甘特过了量测三判据（measure-svg-layout.py）；
- [ ] 密集图（组件/部署/时序）有效字号 ≥12px（measure-svg-layout.py --display-width 与 HTML 实际显示宽一致）？
- [ ] HTML 内嵌每图 .mmd 源码与渲染命令（离线可复现）？
- [ ] 大图只用 SVG 交付（PNG 超限时）且预览可用。

## 4. HTML 输出

### 4.1 单个 HTML 文档

```html
<h3>图 1：订单流程</h3>
<a href="figure-01-order-flow.svg" target="_blank" rel="noopener">
  <img src="figure-01-order-flow.png" alt="订单流程">
</a>
<p>说明：……</p>
```

### 4.2 PNG 与 SVG 双引用（同一机制）

⚠️ **PNG 与 SVG 引用必须用同一机制**：Markdown 图片 `![]()` 与内联 HTML `<a>` 走不同路径解析管线（有的渲染器代理 Markdown 图片 URL 却透传 HTML href），混用会导致两条路径不一致。

- **首选：全内联 HTML**：`<a href=x.svg target=_blank rel=noopener><img src=x.png></a>`（点图开 SVG 新标签，可无损放大）；
- **回退：全纯 Markdown**：`[![alt](x.png)](x.svg)`（渲染器剥 HTML 时同标签打开）；
- 不要混用两种机制。

### 4.3 嵌入 Markdown 文档（最佳实践）

- 默认引用 PNG（预览友好），SVG 同时产出供放大；
- 同一文档内所有图统一用同一种引用机制。

### 4.4 可复现信息（HTML 内嵌 .mmd 与渲染命令）

HTML 不依赖外部渲染服务在线即可复现：每图在图片下方加一个折叠块，内嵌 `.mmd` 源码与所用渲染命令（`render-mermaid.sh <图>.mmd <输出目录> <前缀>`，注明 `MERMAID_BACKEND` 后端）：

```html
<h3>图 1：订单流程</h3>
<a href="figure-01-order-flow.svg" target="_blank" rel="noopener">
  <img src="figure-01-order-flow.png" alt="订单流程">
</a>
<p>说明：……</p>
<details>
  <summary>图 1 源文件（.mmd）与渲染命令</summary>
  <pre><code>flowchart TD
  A --> B</code></pre>
  <p>渲染：<code>render-mermaid.sh figure-01-order-flow.mmd figures/ figure-01-order-flow</code>（MERMAID_BACKEND=server）</p>
</details>
```

- 源码用 `<pre><code>` 原样呈现（保留缩进），不要用图片替代；
- 渲染命令写完整：文件、输出目录、前缀、后端选择（本地后端时写 `MERMAID_BACKEND=local`）；
- 图集在 HTML 末尾补一段「渲染环境」：所用 Mermaid 版本/服务器地址，整包可复现。

## 5. 交付物

- 渲染图（PNG+SVG）+ `.mmd` 源文件 + HTML 文档，同一目录；
- HTML 通过相对路径引用图片（可整体移动）；
- HTML 内嵌每图 .mmd 源码与渲染命令（离线可复现，见 §4.4）。
