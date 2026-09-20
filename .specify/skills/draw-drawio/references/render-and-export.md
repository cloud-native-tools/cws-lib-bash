# Render & Export — 渲染、导出与布局事实

本文件覆盖三件事：交付产物**怎么跑出图**、**几何为什么必须由调用方给出**、以及**布局/走线 pass 到底能做什么**。XML 语法侧见 `./mxgraph-format.md`。

> **轴②「渲染位置」不在本文件内声明。** 渲染方式（本地 / 远端 / 共享渲染服务）正在另一条流程中重新裁定。本文件只登记 draw.io 的**引擎能力事实**——它能经哪些路径渲染与导出——不声明本套件采用哪条路径，也**不对各路径排优劣**；选路判据 owner 是 `skills/draw-diagram/references/routing-matrix.md` §0（该节目前明确**不登记轴②取值**）。下文对「远端路径」的记录是能力清单的一部分，**不是**选型结论。

> **验证状态**：本机无 draw.io Desktop / CLI，故本文件的全部渲染与导出结论**均来自官方文档，未经一次真实执行**。已实测的部分只有 XML 结构层（见 `./mxgraph-format.md` §9 第 1 项）。

## 1. 渲染 / 查看 / 嵌入路径（能力清单，**不分优劣**）

### 1.1 本机路径（不依赖外部 SaaS）

| # | 路径 | 形态 | 能做什么 |
|---|------|------|----------|
| 1 | **draw.io Desktop**（Electron 应用） | 桌面 GUI + CLI | 交互查看、人工微调；**无头导出走它的 CLI**（§2） |
| 2 | **自托管 webapp** | 本地服务 | 团队内共享的浏览器访问入口 |
| 3 | **`viewer-static.min.js`** | 静态只读 HTML | 把图内嵌进已有页面/报告，只读展示 |
| 4 | **embed iframe + `postMessage`** | 宿主页面 ⇄ 内嵌编辑器/查看器 | 程序化加载、导出、回存，`action: load \| export \| save`；另有 `layout` action（§3.3） |

路径 4 是本机侧唯一的**程序化**接口。

### 1.2 远端 / 托管路径（官方提供，能力事实）

| # | 路径 | 形态 |
|---|------|------|
| 5 | **`app.diagrams.net` + `#create` URL** | 把 XML 压缩后经 URL hash 传入，直接在官方编辑器打开：`https://app.diagrams.net/?grid=0&pv=0#create=ENCODED_JSON`。`#create` 值是 URL 编码的 JSON：`{"type":"xml"\|"csv"\|"mermaid","compressed":true,"data":"BASE64_DEFLATED_XML"}`；可加 `layout` 与 `applyLayouts` 字段（§3.3）。`type=mermaid` 时默认插入为**可编辑的 draw.io 形状**，加 `"image": true` 则插入为单张静态 SVG（Mermaid 源保留在图上可再编辑） |
| 6 | **官方 draw.io MCP server** | 远端 `mcp.draw.io/mcp`（在对话内渲染交互式 viewer）；或 `@drawio/mcp`（npm，`npx @drawio/mcp`，在浏览器编辑器中打开，支持 XML / CSV / Mermaid） |
| 7 | **官方 assistant plugins** | Claude Code / Codex CLI / GitHub Copilot CLI 插件，生成原生 `.drawio` 并**经 draw.io Desktop CLI 可选导出 PNG/SVG/PDF** |

> 路径 5–7 与「共享渲染服务」的选型问题高度相关，属**另一条流程的输入**，本文件只登记其存在与接口形态，不做取舍。

## 2. CLI 导出

```
drawio -x -f svg|png|pdf -o <out> <in>
```

- `<in>` = `.drawio` / mxGraph XML 产物，`<out>` = 目标文件；`-f` 选格式。`svg` / `png` / `pdf` 三种格式由官方 assistant-plugin 说明确证（「optional PNG/SVG/PDF export via the draw.io Desktop CLI」）。
- **输入接受面已确证**：完整形与简化形（裸 `mxGraphModel`）draw.io 都接受，后者打开时自动补外层；**一律未压缩**（详见 `./mxgraph-format.md` §1）。
- **`--layout` 开关**（官方文档确证）：在创建后跑一次布局 pass。取值 = 预设名（`verticalFlow` / `horizontalFlow` / `verticalTree` / `horizontalTree` / `radialTree` / `organic`，与编辑器 `Arrange > Layout` 菜单同名）或自定义 layout JSON 数组（完整 JSON layout 规范，支持布局序列与逐项选项；数组也可以是以 `[` 开头的 JSON 字符串传入）。该取值格式与 embed 协议的 `layout` action、`#create` 的 `layout` 字段**三者同格式**。
- **无图形环境的 Linux**：以 `xvfb-run -a` 包裹调用。
- **二进制定位**（已确证的路径常量）：
  - macOS：`/Applications/draw.io.app/Contents/MacOS/draw.io`
  - Windows：`C:\Program Files\draw.io\draw.io.exe`
  - Linux：来自 draw.io Desktop 的可执行文件位置（获取方式见 §4 未决项）
- 关闭联网更新可设环境变量 `DRAWIO_DISABLE_UPDATE=true`（drawio-desktop 官方 README）。

## 3. 布局与走线的事实（**对 S1f 草稿的更正**）

### 3.1 更正声明

S1f 草稿曾断言「**引擎不含自动布局**，调用方必须自算全部 `x/y/width/height`（Node 侧 dagre/elkjs/graphlib，Python 侧 networkx/pygraphviz/graphviz）」。该断言**作为绝对命题不成立**，现更正为下面 §3.2–§3.5 的分层事实。仍成立的部分是：`.drawio` **文件格式自身不做任何布局计算**，vertex 必须携带显式几何；edge 只需 `source`/`target`，无需手写路径点。

### 3.2 默认行为：内建 router 很基础

默认由 draw.io 的**内建 router** 画线，它「intentionally basic」：每条 edge 是直线或简单直角路径，**无避障**——连线会直接**穿过** `source` 与 `target` 之间的任何形状。**没有服务端后处理**。

### 3.3 两个可选、独立、可叠加的 pass

均为**显式开启**，在图渲染后于客户端执行；导出/复制得到的 XML 反映**最终走线结果**。

> **调用面警告（必读）**：`routing` / `postLayout` / `applyLayouts` 这三个名字在官方文档中是 **MCP server `create_diagram` 工具的参数名**。它们在 Desktop CLI 上的等价开关**只确证了 `--layout`**（§2）。**不得**把 `routing=libavoid` / `postLayout=elk` 当作 CLI 开关直接拼进命令行——见 §4 未决项 9。

- **`routing: "libavoid"`**（仅 XML）— **避障正交走线**。**vertex 保持在调用方放置的位置不动**，只重算连线，使其走干净的直角线段并**绕开**形状（平行时段间自动分开）。
- **`postLayout: "elk"`** — **整体重布局**（ELK `layered` 流）。vertex 从调用方位置**动画迁移到规范层级位置**，连线作为布局的一部分一并路由。方向：XML 场景设可选 `direction` 字段（`"vertical"` 默认 / `"horizontal"`）。
- **`applyLayouts: true`**（`#create` 路径）— 让**图内自带的布局**（cell style 上的 `childLayout`，如 `childLayout=flowLayout;flowOrientation=west;`）在创建后立刻跑一次。这类布局平时只在**编辑时**响应变化、打开时不跑，所以依赖它的生成图在首次编辑前会显示在存储坐标上（通常全在 `(0,0)`）。嵌套容器由内向外布局，外层能看到内层的最终尺寸。`applyLayouts` 与 `layout` 相互独立、可组合。

四种组合的结果：

| `postLayout` | `routing` | 结果 |
|---|---|---|
| — | — | 基础内建 router（直线 / 简单直角，**无避障**）；保留调用方坐标 |
| — | `libavoid` | 保留调用方坐标；连线重路由为**绕开形状**的正交线 |
| `elk` | — | ELK **既排 vertex 也路由 edge**（自带尚可的走线） |
| `elk` | `libavoid` | 通常不值得——ELK 已路由；仅当 ELK 走线确实差时再加 |

### 3.4 引擎侧的取舍判据（**只关于 pass，不关于图类**）

**二选一，本质是替代关系而非叠加：**

- **都不开** — 相连节点处于清爽的行/列且其间空旷、基础 router 的直线/直角不会穿过形状时。稀疏版面下最轻的选择。
- **`routing: "libavoid"`** — 要**保留调用方给的版面**、只整理连线：只要某条 edge 否则会切过某个盒子，或想要一致的绕形正交走线。
- **`postLayout: "elk"`** — 要**规范化重布局**（vertex 会被移动）。ELK 自己会路由 edge，故**不要再同时设 `routing`**（几乎总是冗余）。左→右流向加 `direction: "horizontal"`。

**引擎侧的硬事实**：`postLayout` **会移动 vertex**。因此凡「调用方给定的位置本身必须保留」，就不能开 `postLayout`——`libavoid` 明确「Vertices stay exactly where you placed them」，是这种场景的选项。

> **边界声明（防层级越界）**：官方文档在描述各 pass 时会举例说明它们**各自擅长哪类图**（如 libavoid 之于连接密集的架构/拓扑，elk 之于有向层级流程）。本文件**只登记「pass 会不会动 vertex」这一引擎侧事实**，不据此推荐图类、也不判断某张图的空间排布是否「承载含义」——**「该画成什么图类」「版面本身是否承载语义」是语义判断，owner 是前门**（`skills/draw-diagram/SKILL.md`）。前门若已给出几何与版面意图，本文件的一切 pass 建议**一律让位**。

### 3.5 因此「布局」在本技能里的含义

生成侧的正确姿态是：**声明逻辑结构**（有哪些节点、哪些连线、什么标签、什么泳道/容器分组），坐标用 `./mxgraph-format.md` §6.1 的**兜底网格公式**粗放，把路由与（可选的）重布局交给引擎的 pass。**不要在推理里做版面算术**，也不要自己引 dagre/elkjs/networkx 解算坐标——官方指引明确「you do **not** need to do layout math」。版面**规划**决策（该不该自由版面、该多密、该分几组）仍归前门（指针见 §5）。

## 4. 未决项（官方文档未能确证；拒绝臆造）

原 S1f 草稿的 **9 项**渲染/导出未决项处置如下 —— **1 项确证消解**（CLI 输入接受面：完整形与简化形均接受、一律未压缩、裸 `mxGraphModel` 自动补外层，见 §2 与 `./mxgraph-format.md` §1），**3 项收窄后仍开放**（CLI 其余开关与 `-x` 语义、postMessage 细节、导出格式是否为全集），**5 项原样开放**。合计 1 + 3 + 5 = 9。另**新增 1 项**（第 9 条），故下表共 9 条：

1. **CLI 其余开关的完整清单**（收窄）：`--layout` 已确证；除 `-x` / `-f` / `-o` / `--layout` 外可用的开关（页面选择、透明背景、缩放、边框、字体嵌入等）与 `-x` 的确切语义仍未确证 —— drawio-desktop 官方 README **无 CLI 章节**（已核对 dev 分支），故完整开关表无处确证。落地使用时以 `drawio --help` 的实测输出为准，并经 `improve-skills` 回填本文件。
2. **失败面**：CLI 退出码语义、错误输出格式、超时行为 —— 未确证。
3. **容器/无头环境附加要求**：除 `xvfb-run -a` 外是否还需其它开关（如沙箱相关）—— 未确证。
4. **`viewer-static.min.js` 获取方式**：来自哪个发行包/产物、版本如何锁定 —— 未确证。
5. **postMessage 协议细节**（收窄）：`layout` action 的**取值格式**已确证（§2）；三种 `action`（`load`/`export`/`save`）与 `layout` 的消息信封结构、请求/响应配对方式、导出结果回传形态仍未确证。
6. **自托管 webapp 的获取与部署**：镜像/发行物来源与最低运行要求 —— 未确证。
7. **导出格式是否为全集**（收窄）：`svg` / `png` / `pdf` 已确证可用（官方 assistant-plugin 说明）；是否还有其它格式未确证。
8. **各平台二进制的获取与许可**（收窄）：macOS / Windows 路径常量已确证；Linux 二进制与 Desktop 应用的分发方式、版本要求未确证。
9. **【新增】三个 pass 的调用面 + 全链路未实测**：本机无 draw.io 环境，故 §2 的导出命令与 §3 的 pass **未经一次真实执行验证**；且 `routing=libavoid` / `postLayout=elk` / `applyLayouts` 在官方文档中是 **MCP server `create_diagram` 的参数名**，其 Desktop CLI 等价开关**只确证了 `--layout`**。首次真实出图时须实测「CLI 到底怎么触发避障走线与重布局」，并按结果修订 §3.3 的调用面警告。

## 5. 语义层与引擎选择指针（本文件不承载）

- 语义模型 → `skills/draw-diagram/references/semantic-model.md`（**现存**）
- **引擎选择**、`drawio` ↔ `excalidraw` 优先序、能力轴层与反路由红线 → `skills/draw-diagram/references/routing-matrix.md`（**现存**）
- 版面规划与自由度判据、图类选择、样式配色、内容措辞、类专属约定 → 前门 `skills/draw-diagram/SKILL.md`（**现存**）；其专章参考文件（`references/howto/*`、`references/guide/*`、`references/document/*`）由 stage S1d 规划、**尚未落盘**，故不预建具体路径
- XML 语法、容器构造与生成硬性规则 → `./mxgraph-format.md`（同技能内）
