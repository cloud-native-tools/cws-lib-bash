# Step 5/7: 渲染与 HTML 输出

## 渲染脚本

```bash
"${SKILL_HOME}/scripts/render-excalidraw.sh" <名称>.excalidraw [输出目录] [输出前缀]
# 产出：<输出目录>/<前缀>.svg + <前缀>.png（同时产出，勿只取其一）
```

环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| `EXCALIDRAW_SERVER` | `http://127.0.0.1:8383` | 渲染服务地址 |
| `EXCALIDRAW_BACKEND` | `server` | `server`=远端；`local`=本机临时起服务（须用户确认） |
| `EXCALIDRAW_SCALE` | `2` | PNG 缩放倍数 |
| `EXCALIDRAW_PADDING` | `16` | 导出内边距 px |
| `EXCALIDRAW_BG` | 场景自带 | 覆盖背景色 |

## 后端策略（与 draw-plantuml 一致的远端优先）

- **默认 server 模式**：直连 `EXCALIDRAW_SERVER`。
- **服务不可达（exit 2）**：脚本输出指引。此时**必须先询问用户**：
  1. 已有部署 → 确认/修正 `EXCALIDRAW_SERVER` 后重试；
  2. 未部署 → 按 [server-deployment.md](../guide/server-deployment.md) 部署，或经用户同意后以 `EXCALIDRAW_BACKEND=local` 临时本机起服务（自动 npm install/build，需 Node ≥18 与 Chrome/Chromium）。
  - **未经用户确认不得静默切 local。**
- **local 模式**：脚本自起自收（临时端口 8393，退出即清理），适合一次性出图。

## Step 6 回看（渲染后必做）

用 Read 工具读取 PNG，对照 SDS 几何清单（无 SDS 时为 Step 3 兜底规划表）逐项检查：

- [ ] 元素齐全，无遗漏
- [ ] 文本未溢出容器、未被截断
- [ ] 箭头未穿元素、指向正确
- [ ] 布局均衡，无大面积空洞或拥挤
- [ ] weight_plan 层级可辨：边框粗细按 T1>T2 递减、流线细浅（见 [../sds-realization.md §3](../sds-realization.md)）
- [ ] 中文渲染正常（无豆腐块）

不合格 → 改 `.excalidraw` 重渲；合格 → 进 HTML 组装。

## HTML 组装

单文件 HTML，结构：

```html
<!doctype html>
<html lang="zh">
<head><meta charset="utf-8"><title>图标题</title></head>
<body>
  <h1>图标题</h1>
  <p>一句话说明（这张图讲什么、为什么这么画）。</p>
  <a href="名称.svg" target="_blank" rel="noopener"><img src="名称.png" style="max-width:100%"></a>
  <details>
    <summary>复现性附录：场景源码与渲染命令</summary>
    <p>渲染命令：<code>render-excalidraw.sh 名称.excalidraw ./ 名称</code>（EXCALIDRAW_SERVER=...）</p>
    <pre>（粘贴与磁盘 .excalidraw 逐字节一致的场景 JSON）</pre>
  </details>
</body>
</html>
```

- PNG/SVG/HTML 同目录，相对路径引用。
- 附录源码必须与磁盘文件逐字节一致（直接复制，不手敲）。
- 图集（多图）时每图一节，共享页头说明与编号。

## 嵌入 Markdown 文档时

PNG 与 SVG 引用必须同一机制（混用会因渲染器路径管线不同而断链）：

- 首选全内联 HTML：`<a href="x.svg" target="_blank" rel="noopener"><img src="x.png"></a>`
- 渲染器剥 HTML 时回退全纯 Markdown：`![标题](x.png)`（放弃 SVG 放大）
