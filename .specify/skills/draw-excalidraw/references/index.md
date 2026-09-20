# draw-excalidraw 参考文档索引

## 操作指南（howto/，按工作流步骤）

| 文档 | 对应步骤 | 内容 |
|------|---------|------|
| [00-semantic-analysis.md](howto/00-semantic-analysis.md) | Step 1 | 意图解析、上下文摘要、确认提问 |
| [01-path-selection.md](howto/01-path-selection.md) | Step 2 | 图表类型 → 生成路径（Mermaid 桥接 vs 场景 JSON 直出） |
| [sds-realization.md](sds-realization.md) | Step 3 | SDS 几何实现：坐标映射、文本宽度校验、连线路由、强弱映射、复刻覆盖、无 SDS 网格兜底 |
| [03-scene-json-generation.md](howto/03-scene-json-generation.md) | Step 4 | 场景 JSON 编写规范（容器/文本绑定/箭头/分组） |
| [04-rendering-and-output.md](howto/04-rendering-and-output.md) | Step 5/7 | 渲染脚本用法、渲染服务不可达处置、HTML 组装 |

## 参考资料（guide/ 与本目录）

| 文档 | 内容 |
|------|------|
| [sds-realization.md](sds-realization.md) | SDS 实现参考（语法层交接：输入契约落实、tier→strokeWidth、场景 JSON 约定、复刻覆盖规则） |
| [cycle3-reproduction-lessons.md](cycle3-reproduction-lessons.md) | Cycle 3 复刻实测教训（历史记录，规范内容已并入 sds-realization.md §2/§4） |
| [scene-schema-reference.md](guide/scene-schema-reference.md) | `.excalidraw` 元素字段全参考 + 标准色板 + 最小元素模板 |
| [server-deployment.md](guide/server-deployment.md) | 渲染服务部署（本机 Node / Docker / 远端）与排障 |

## 脚本

| 脚本 | 用途 |
|------|------|
| [../scripts/render-excalidraw.sh](../scripts/render-excalidraw.sh) | 客户端渲染脚本（远端优先 + local 兜底审批门） |
| [../scripts/server/](../scripts/server/) | 自部署渲染服务（Node + headless Chromium + 官方导出管线），含 Dockerfile/compose |

## 实战沉淀（best-practices/）

| 文档 | 内容 |
|------|------|
| [best-practices.md](../best-practices/best-practices.md) | 最佳实践（布局策略、文本处理、路径选型经验） |
| [pitfalls.md](../best-practices/pitfalls.md) | 陷阱清单（实测踩坑：Mermaid 文本丢失、进程清理、端口占用等） |
