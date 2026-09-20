# 最佳实践（实测沉淀）

## 路径选型

1. **标准结构图先走 Mermaid 桥接**：flowchart/sequence/class/er/state 由官方转换器自动布局 + 文本绑定，一次成功率远高于手写坐标。产物是标准 `.excalidraw` 场景，不满意可继续手改。
2. **直出先过 Step 3**：带 SDS 时零偏离实现其 box（几何归语义层）；仅无 SDS 直接调用才用网格法自规划（定尺寸 → 定间距 → 算坐标）并声明假设。落 JSON 前先列实现/规划表（[../references/sds-realization.md](../references/sds-realization.md)）。
3. **超 15 节点拆图**：概览图 + 下钻子图，图间共享编号与配色词汇。

## 文本处理

4. **容器文本一律用 containerId 绑定**：渲染服务按真实字体度量重算尺寸并自动居中——不要手算文本 x/y 居中，算不准。
5. **容器宽度按 CJK≈fontSize×字数 + 40px padding 预留**，宁宽勿窄；绑定文本超宽会自动换行但会撑高溢出。
6. **字号三档够用**：16 正文 / 20 节点标题 / 28 图标题；跨图一致。
7. **箭头标签用独立 text**，放箭头中点上方，与箭头同色。**多折点箭头注意**：几何中点可能恰是折点极值处（如下弯弧的最低点），标签会与线重叠——改放在最长水平段的上方，回看时重点检查这类标签。

## 样式

8. **手绘感来自 roughness: 1 + 官方色板**；`fillStyle: "solid"` 最干净，hachure 适合强调"草稿感"。**复刻场景例外**：roughness 0 + 直角 + 细虚线 zone（见 [../references/sds-realization.md §4](../references/sds-realization.md)）。
9. **同子系统同色系**（蓝系/绿系/黄系分区），跨区关系用红/橙箭头突出。
10. **分组用垫底大矩形**（浅色背景 + solid）比 frame 美观；frame 适合需要标题栏的强分组。

## 渲染与验收

11. **PNG 与 SVG 同时产出**：PNG 用于预览/嵌入，SVG 无损放大看细节。
12. **渲染后必须 Read PNG 回看**：坐标是算出来的，重叠/溢出只有看图才能发现；对照布局规划表逐项验收。
13. **`.excalidraw` 源文件随交付物保存**：用户可直接拖进 excalidraw.com 或自部署白板继续编辑——这是 Excalidraw 相对 PlantUML 的核心体验优势，别丢。
14. **远端渲染优先**：默认 `EXCALIDRAW_BACKEND=server`；local 模式（临时自起服务）必须用户确认后启用。
