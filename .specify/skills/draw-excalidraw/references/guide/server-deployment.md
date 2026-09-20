# 渲染服务部署指南（excalidraw-render-server）

渲染服务源码在技能目录 `scripts/server/`。它是 draw-excalidraw 的渲染后端：
headless Chromium 承载官方 @excalidraw/excalidraw 导出管线，POST 场景 JSON → SVG/PNG。

## 部署形态选择

| 形态 | 适用 | 命令 |
|------|------|------|
| 本机 Node 直跑 | 个人 Mac，随用随起 | 方式 A |
| Docker | 服务器/团队共享/常驻 | 方式 B |
| 不部署 | 一次性出图 | `EXCALIDRAW_BACKEND=local`（渲染脚本临时自起自收，须用户确认） |

## 方式 A：本机 Node 直跑

前置：Node.js ≥ 18；Chrome/Chromium 任一（macOS Google Chrome 即可，自动探测）。

```bash
cd <技能目录>/scripts/server
npm install          # 首次
npm run build        # 首次（打包浏览器端渲染入口）
npm start            # 监听 http://127.0.0.1:8383
```

验证：`curl http://127.0.0.1:8383/health` → `{"ok":true,...}`

常驻（macOS launchd 或简单 nohup 均可）：

```bash
nohup node server.mjs > /tmp/excalidraw-render.log 2>&1 &
```

## 方式 B：Docker（服务器部署）

```bash
cd <技能目录>/scripts/server
docker compose up -d --build
# 或
docker build -t excalidraw-render .
docker run -d --name excalidraw-render -p 8383:8383 --restart unless-stopped excalidraw-render
```

镜像基于 node:22-slim + Debian chromium + Noto CJK 字体（中文渲染开箱可用）。
验证：`curl http://<host>:8383/health`。

## 客户端指向

```bash
export EXCALIDRAW_SERVER=http://<host>:8383   # 渲染脚本读取此变量
```

## API 速查

| 端点 | 输入 | 输出 |
|------|------|------|
| `GET /health` | — | 健康检查 |
| `POST /render` | `{scene, format: svg\|png, scale?, padding?, viewBackgroundColor?, darkMode?}` | 图片字节流 |
| `POST /render-mermaid` | `{mermaid, format}` | 图片字节流 |
| `POST /mermaid-to-scene` | `{mermaid}` | 完整 `.excalidraw` 场景 JSON |

场景经官方 `restore(refreshDimensions)` 规范化：缺省字段自动补齐、文本按真实字体重度量、容器文本自动居中。

## 排障

| 症状 | 原因与处置 |
|------|-----------|
| 脚本 exit 2「unreachable」 | 服务未启动或地址错：`curl ${EXCALIDRAW_SERVER}/health` 验证；端口冲突换 `EXCALIDRAW_PORT` |
| local 模式「exited early」 | 看脚本打印的日志尾部：多为端口被占（换 `EXCALIDRAW_LOCAL_PORT`）或缺 Chromium（装 Chrome 或设 `EXCALIDRAW_CHROMIUM_PATH`） |
| 中文变豆腐块 | 容器缺 CJK 字体：Docker 内确认装了 fonts-noto-cjk（默认镜像已含） |
| PNG 模糊 | 提高 `EXCALIDRAW_SCALE`（默认 2，可用 3） |
| 首次渲染慢 | 浏览器懒启动属正常（数秒），后续请求快 |
| 关停后端口残留 | 服务已支持 SIGTERM 优雅关停；仍残留时 `lsof -ti :8383 \| xargs kill -9` |

## 与 Excalidraw 白板应用的关系

本服务只做**渲染**。若还需要给人用的可编辑白板（协作/分享），另行部署官方镜像栈：
`excalidraw/excalidraw`（前端）+ `excalidraw-room`（协作中继）+ `excalidraw-storage-backend`（场景存取 API）——详见 08_工具开发 `artifacts/external/excalidraw/install.md`。渲染服务与白板互相独立，可只部署其一。
