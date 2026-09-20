# Step 4: 生成场景 JSON / Mermaid 代码

## 场景 JSON 直出

### 文件骨架

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "draw-excalidraw",
  "elements": [ ... ],
  "appState": { "viewBackgroundColor": "#ffffff", "gridSize": null },
  "files": {}
}
```

- 保存为 `<名称>.excalidraw`（UTF-8，中文不转义）。
- 元素书写顺序：**分组背景 → 容器 → 文本 → 箭头**（同层按出现顺序渲染，先写的垫底）。
- 字段细节与最小模板见 [scene-schema-reference.md](../guide/scene-schema-reference.md)。

### 三条生成纪律

1. **容器文本用绑定，不用手摆**：文本元素设 `"containerId": "<容器id>"`，容器 `boundElements` 加 `{"id":"<文本id>","type":"text"}`，`textAlign: "center"` + `verticalAlign: "middle"`。文本 x/y 粗略给（容器中心附近即可）——渲染服务会按真实字体度量重算尺寸并自动居中。
2. **箭头写全绑定**：`startBinding`/`endBinding` 填 `{"elementId":"<容器id>","focus":0,"gap":4}`，同时把箭头登记进两端容器的 `boundElements`（`{"id":"<箭头id>","type":"arrow"}`）。`points` 第一个点恒为 `[0,0]`，其余为相对折点。
3. **每个元素必有 id/seed/version**：id 用语义化字符串（`box-gateway`、`arrow-req`）；seed 任意整数（手绘随机性）；version 给 1。其余样式字段缺省时渲染服务的 `restore()` 会补默认值，但颜色/尺寸/文本必须显式给。

### 箭头标签

箭头标签用**独立 text 元素**放在箭头中点上方 20–30px 处，颜色与箭头同色。（不用 containerId——箭头不是容器。）

### 图片元素（少用）

`type: "image"` 需在 `files` 里提供 `{ "<fileId>": {"mimeType":"image/png","dataURL":"data:...","created":1} }` 且元素带 `fileId`/`status":"saved"`。除非用户明确要贴图，否则不用图片元素。

## Mermaid 桥接

1. 写 Mermaid 源码（存 `<名称>.mmd` 备查）。
2. 调渲染服务转换为场景并保存（bash 片段，`${EXCALIDRAW_SERVER:-...}` 为 shell 变量展开）：

```bash
curl -s -X POST "${EXCALIDRAW_SERVER:-http://127.0.0.1:8383}/mermaid-to-scene" \
  -H 'Content-Type: application/json' \
  -d "$(python3 -c 'import json,sys; print(json.dumps({"mermaid": open(sys.argv[1]).read()}))' 名称.mmd)" \
  > 名称.excalidraw
```

3. 得到的 `.excalidraw` 即标准场景，走 Step 5 渲染；版面不满意可直接改 JSON 微调。

### Mermaid 语法要点（实测）

- `flowchart TD`（上下）/ `flowchart LR`（左右）；节点 `A[矩形文本]`、`B{菱形文本}`、`C(圆角)`
- 边：`A --> B`、带标签 `A -->|标签| B`
- 中文文本可直接写；避免在节点文本里用未转义的 `[]{}|` 等特殊字符
- sequence/class/er/state/mindmap 各用其原生关键字
