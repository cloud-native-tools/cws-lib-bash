# excalidraw-render-server

自部署的 Excalidraw 渲染服务：接收 Excalidraw 场景 JSON（或 Mermaid 文本），
在 headless Chromium 里用**官方 @excalidraw/excalidraw 导出管线**渲染为
SVG/PNG。是 `draw-excalidraw` 技能的渲染后端，与 draw-plantuml 的
PlantUML Server 同构（客户端脚本 + 远端渲染服务）。

## 为什么需要它

Excalidraw 官方 Docker 镜像是纯前端应用，**没有任何绘图/渲染 HTTP API**；
官方导出函数（`exportToSvg`/`exportToBlob`）又依赖浏览器环境。本服务用
headless Chromium 承载官方导出管线，把它变成可调用的 HTTP 渲染 API。

## 快速开始（本机 Node，无需 Docker）

要求：Node.js ≥ 18；一个可用的 Chrome/Chromium（macOS 的 Google Chrome、
Playwright 缓存的 Chromium 均可，自动探测；也可 `EXCALIDRAW_CHROMIUM_PATH` 指定）。

```bash
npm install        # 安装依赖（@excalidraw/excalidraw、playwright-core 等）
npm run build      # 打包浏览器端渲染入口 -> static/dist/render.js
npm start          # 默认监听 http://127.0.0.1:8383
```

## 快速开始（Docker，服务器部署）

```bash
docker compose up -d --build
# 或
docker build -t excalidraw-render . && docker run -d -p 8383:8383 excalidraw-render
```

镜像内含 Chromium 与 Noto CJK 字体（中文文本渲染）。

## HTTP API

| 端点 | 方法 | 输入 | 输出 |
|------|------|------|------|
| `/health` | GET | — | `{"ok":true}` |
| `/render` | POST | 场景 JSON（见下） | SVG 或 PNG 字节流 |
| `/render-mermaid` | POST | `{"mermaid":"...","format":"png\|svg"}` | SVG 或 PNG 字节流 |
| `/mermaid-to-scene` | POST | `{"mermaid":"..."}` | 完整 `.excalidraw` 场景 JSON |

`/render` 请求体（除场景外均可选）：

```json
{
  "scene": { "elements": [...], "appState": {...}, "files": {...} },
  "format": "svg | png",
  "scale": 2,
  "padding": 16,
  "viewBackgroundColor": "#ffffff",
  "darkMode": false,
  "exportBackground": true
}
```

- `scene` 经官方 `restore()` 规范化——**Agent 生成的部分字段 JSON 可直接提交**，
  缺失的 seed/version/默认样式会自动补齐。
- Mermaid 路径内部用官方 `parseMermaidToExcalidraw` + `convertToExcalidrawElements`，
  布局与文本绑定全自动。

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `EXCALIDRAW_PORT` | `8383` | 监听端口 |
| `EXCALIDRAW_HOST` | `127.0.0.1` | 监听地址（容器内设 `0.0.0.0`） |
| `EXCALIDRAW_CHROMIUM_PATH` | 自动探测 | 浏览器二进制路径 |

浏览器探测顺序：`EXCALIDRAW_CHROMIUM_PATH` → macOS Google Chrome →
Playwright 缓存 Chromium → PATH 中的 chromium/google-chrome（Linux）。

## 运维要点

- 浏览器懒启动（首次渲染时拉起）并常驻复用；渲染请求串行执行，内存平稳。
- SIGTERM/SIGINT 优雅关停（先关浏览器再退出）；`render-excalidraw.sh` 的
  local 模式随脚本退出自动清理临时服务。
- 场景体上限 64MB（内嵌图片资源时注意）。
