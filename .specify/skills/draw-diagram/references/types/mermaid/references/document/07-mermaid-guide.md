# Mermaid 使用指南（07）

## 1. 基础语法

- 文件首行：图类型声明（`flowchart TD` / `classDiagram` / `sequenceDiagram` / `stateDiagram-v2` / `erDiagram` / `gantt` / `mindmap` / `C4Context` …）；
- 样式指令 `%%{init: {...}}%%` 必须在首行**之前**；
- 每个文件一张图（`.mmd` 后缀）；图集多文件 + HTML 组装。

## 2. 工具选型

| 工具 | 用途 | 何时用 |
|------|------|--------|
| render-mermaid.sh | 本技能标准渲染 | 每次交付 |
| mermaid.ink | 服务器渲染（URL 即图） | 脚本默认后端 |
| mermaid-cli (mmdc) | 本地渲染（Chrome） | 离线/大图/字体问题 |
| VS Code Markdown Preview Mermaid | 快速预览 | 开发调试 |
| mermaid.live | 在线编辑器 | 手工实验 |

## 3. 环境配置

**mmdc 本地后端**（离线必需）：
```bash
npm install -g @mermaid-js/mermaid-cli   # 或 npx --yes @mermaid-js/mermaid-cli
# Chrome 非标准路径时：
export PUPPETEER_EXECUTABLE_PATH=/path/to/chrome
```

**服务器后端**：
- 默认 `https://mermaid.ink`（公共）；
- 内网部署 mermaid.ink 兼容服务时：`MERMAID_SERVER=http://内网地址`。

## 4. 校验手段

1. 渲染后 Read 图片（本技能 Step 8 标准动作）；
2. 语法错误：服务器返回错误信息（检查引号/括号/缩进）；
3. 版面问题：measure-svg-layout.py 量测（WBS/甘特）；
4. 跨图一致性：图集统一 init/classDef 段（diff 检查）。

## 5. 常见坑位备忘

- 中文/特殊字符不引号包裹 → 解析失败；
- `%%{init}%%` 放在图类型声明之后 → 不生效；
- mindmap 缩进混用空格/tab → 层级错乱；
- 旧版本语法（`stateDiagram`、`sankey`）在新版本已更名（`stateDiagram-v2`、`sankey-beta`）。
