# 布局指南（layout）

## 1. 语义驱动布局

布局不是随机摆放：**位置即角色**（见 diagram-principles §2.1）。编码前先规划空间语义，再选择方向与分组。

## 2. 布局优化

### 2.1 方向决策

- 数「最宽层宽 B」与「主流深 D」：
  - 宽浅（B 大、D 小）→ `flowchart TD`（上下流，横向展开）；
  - 深窄长链（D 大）→ `flowchart LR`（左右流，纵向展开）；
- 状态图（stateDiagram-v2）默认上下布局；ER 图用 `%%{init: {er: {layout: "leftRight"}}}%%` 或默认分层。

### 2.2 宽高比与网格

- `C≈round(sqrt(N×1.3))` 估列数，摆近正方形网格（每行 ≈C 个兄弟节点）；
- 单层兄弟 ≤6，超出下沉一层或拆 subgraph；
- 目标宽高比 1.2~1.8:1（WBS/甘特图用量测脚本校验）。

### 2.3 分组（subgraph）

- 宏观分区：具名 `subgraph 标题 { ... }`（可见边界框）；
- 细分组：同色系 + 无边框样式统一；
- subgraph 内可用 `direction LR` 覆盖内部方向；
- 分组层级 ≤2 层，超过则拆分图集。

### 2.4 间距与隐藏连线

- `%%{init: {flowchart: {nodeSpacing: 50, rankSpacing: 60}}}%%` 调间距；
- 隐藏脚手架线：不表达语义的线用 `~~~` 或干脆不画（Mermaid 无 hidden 边，用虚线 `-.->` 弱化）；
- 连线交叉：调整方向、拆分 subgraph、或重排声明顺序（Mermaid 按声明顺序布局）。

## 3. 按图表类型的布局速查

| 类型 | 默认 | 常用调整 |
|------|------|---------|
| flowchart | TD | LR 给深链；subgraph 内 direction |
| sequenceDiagram | 纵向生命线 | `%%{init: {sequence: {mirrorActors: false, actorMargin: 60}}}%%` |
| classDiagram | 自由布局 | namespace 分组；`%%{init: {class: {}}}` 有限 |
| stateDiagram-v2 | 上下 | `direction LR` 支持（v10.9+ 部分版本） |
| erDiagram | 分层 | `layout: "leftRight"` |
| gantt | 时间轴 | `%%{init: {gantt: {barHeight: 24, barGap: 6, leftPadding: 60}}}%%` |
| mindmap | 树状展开 | 根节点形状选型 |
| C4 | 网格 | `UpdateLayoutConfig($c4ShapeInRow="3")` |

## 4. 常见布局问题排查

| 症状 | 原因 | 处理 |
|------|------|------|
| 图过宽 | 方向错 | 换 LR/TD，或拆 subgraph |
| 线交叉严重 | 兄弟节点顺序/方向 | 重排声明顺序、加分组 |
| 节点挤成一团 | 间距太小 | nodeSpacing/rankSpacing 调大 |
| subgraph 内节点乱跑 | 内部方向未定 | subgraph 内 `direction TD/LR` |
| 标签被截断 | 节点宽度不足 | 用 `id["..."]` 引号 + 换行 `\n`，或缩短标签 |
| 中文渲染为方块 | 服务器字体缺失 | 换本地 mmdc 后端，或 init 指定 fontFamily |
| 渲染超时/URL 太长 | 图太大 | 拆分图集；服务器后端已用 pako 压缩仍超限则换本地 |

## 5. 渲染服务限制

- **mermaid.ink 服务器**：无硬性像素上限，但 URL 长度受服务端限制（pako 压缩可显著缩短）；超大图建议用本地 mmdc 后端；
- **CJK 字体**：mermaid.ink 默认字体栈对 CJK 支持良好；如出现方块字，改用本地后端 + 系统字体；
- **mmdc 本地后端**：需要 Chrome/Chromium（puppeteer）；无网络环境时的唯一选择。

## 6. 版本演进注意

- C4 系列 v10.9+ 原生；`kanban`/`block` 实验性（v11.x）；`progress` 任务属性 v11.7+；
- 文档/交付物标注所用 Mermaid 版本（渲染脚本默认 npx 拉最新，必要时锁定版本）。
