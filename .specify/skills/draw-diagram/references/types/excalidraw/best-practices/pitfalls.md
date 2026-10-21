# 陷阱清单（实测踩坑，只收"不报错但反直觉"的真陷阱）

## P1: Mermaid 转换结果必须经 convertToExcalidrawElements 规范化

`parseMermaidToExcalidraw` 返回的是**中间格式**：文本藏在容器元素的 `label` 子对象里，不是独立 text 元素——直接渲染会得到**结构正确但全无文字**的图（不报错！）。必须经 `@excalidraw/excalidraw` 的 `convertToExcalidrawElements()` 转成正式元素。本技能渲染服务的 `/render-mermaid` 与 `/mermaid-to-scene` 已内置该步骤；但如果你在其他环境直接用 mermaid-to-excalidraw 库，务必自己做这步。

## P2: playwright 启动浏览器后 node 对 SIGTERM 免疫

渲染服务一旦渲染过（浏览器已启动），直接 `kill <pid>` 发 SIGTERM **进程不退出**、端口不放——必须走服务内置的优雅关停 handler（收到 SIGTERM 先 `browser.close()` 再 exit）。清理残留用 `kill -9`。`render-excalidraw.sh` 的 local 模式已内置"TERM → 等待 → KILL"升级逻辑。

## P3: 后台起服务别用子 shell 包裹

`(cd dir && node server.mjs) &` 的 `$!` 是**子 shell 的 PID**，kill 它杀不掉 node 孙进程，且孙进程持有输出管道会让调用方一直挂起。直接 `node /abs/path/server.mjs >logfile 2>&1 &`（ESM 依赖按文件位置解析，无需 cd），日志落文件不继承管道。

## P4: 官方 Excalidraw 镜像没有绘图 API

`excalidraw/excalidraw` Docker 镜像是纯前端静态应用——部署它**得不到任何渲染/画图 HTTP API**。要 API 出图必须部署本技能的渲染服务（或 Excalidraw+ 官方云服务）。白板镜像只解决"人用浏览器画图"。

## P5: 多端口 lsof 清理要逐端口来

`lsof -ti :8383,:8393` 这种多端口写法在部分环境静默失败返回空——清理残留进程时逐端口 `lsof -ti :<port>` 循环，否则旧进程占着端口，新服务 EADDRINUSE 崩溃而表面"健康检查通过"（打到旧进程上了）。

## P6: PNG 导出尺寸 = viewBox × scale

`exportToBlob` 的 `getDimensions` 返回 width/height 是最终像素；scale=2 时 652×122 的场景出 1304×244 PNG。要更清晰提 `EXCALIDRAW_SCALE`，不要指望事后插值。

## P7: 独立文本不会自动居中

`containerId: null` 的独立 text 元素按你给的 x/y 原样渲染（verticalAlign 只影响多行内部对齐）——容器内文字要居中必须走容器绑定（containerId），别手算。

## P8: restore() 补字段但不补布局

渲染服务的 `restore(refreshDimensions)` 会补齐 seed/version/默认样式、重算文本度量，但**不会替你调整容器大小**——文本比容器宽时容器不会自动变宽，溢出照旧。容器宽度必须在生成时留够（见 best-practices #5）。
