# draw-mermaid 最佳实践（Best Practices）

> 从 viz-skill-arena 竞技 cycle（Substrate 架构图，2026-08-07）的 R1 评审建议与重绘改进中沉淀。每条均为「评审指出 → 重绘验证有效」的教训。配套陷阱见 [pitfalls.md](pitfalls.md)。

## 1. 多子系统图必配「子系统配色 + 图例」

多个子系统/分层时，每个子系统一个 `classDef` 色相族，并在图内用 `legend` 指令给出图例——否则全图只剩默认蓝，读者无法靠颜色区分语义族（R1：*"全部子系统使用默认同色，视觉单调"*）。

```mermaid
flowchart TD
  subgraph 认证域
    A[认证服务]
  end
  subgraph 业务域
    B[订单服务]
  end
  A --> B
  classDef auth fill:#fde8e8,stroke:#b3261e,color:#7a1a12
  classDef biz fill:#e8f0fe,stroke:#1a73e8,color:#174ea6
  A:::auth
  B:::biz
  legend
    认证域:::auth
    业务域:::biz
  end
```

- 颜色是语义通道：同子系统同色相族、跨子系统不同色相；配色后再加图例说明「色 → 子系统」映射；
- 图例条目与 classDef 同义（同色块 + 同名字），跨图集复制同一段 classDef/legend 配置保持同义。

## 2. 多子系统用中心辐射布局（hub-and-spoke）防交叉

多个子系统**不要单列纵向堆叠**——堆叠后「枢纽 → 其余子系统」的跨层连线必然交叉密集（R1：*"五个子系统纵向堆叠，跨层连线交叉密集，视觉凌乱"*）。改用：

- 枢纽子系统放中间层，其余子系统分列其上/下（或左右），subgraph 内可 `direction LR` 翻转；
- 跨层边一律经枢纽汇聚（N+M 条而非 N×M 条全互联），交叉随之消失；
- 仍交叉 → 重排声明顺序（先声明 hub 再声明周边）或按架构接缝拆图集。

## 3. 序列图：字号、关键消息强调与统一 Note 样式

- 参与者过多（>8）时增大字号（≥12px），避免小屏压缩；
- 关键消息（Resume/Suspend/CAS 状态迁移）加粗或高亮；
- 阶段说明（phase note）样式全图统一；关键分支（如请求 parking 的 opt 块）必须入图，不能只写进 HTML 说明（R1：*"序列图缺池饱和请求 parking 分支"*）。

## 4. 需求清单驱动图型选择（防漏交付）

按任务需求清单逐项映射 Mermaid 原生图型，不要只画「顺手」的图：

| 需求类型 | Mermaid 图型 |
|----------|--------------|
| 状态机 | `stateDiagram-v2`（原生，优于在序列图底部放文字 note） |
| 双层资源模型（CRD ↔ 状态库） | flowchart/C4 分层子图 |
| 组件/部署 | C4Context / C4Deployment |

R1 反复指出「5 类图只交付 3 类」——绘制前先列图型清单，逐项勾选。

## 5. HTML 内嵌 .mmd 源码与渲染命令（可复现）

HTML 交付物中内嵌：图源 `.mmd` 全文 + `render-mermaid.sh` 调用命令。评审明确要求 *"HTML 内嵌 .mmd 源码与渲染命令以便复现"*——只给渲染后图片的文件不可复现、不可维护。

## 6. 部署图显式标注网络关系与 namespace

- 隧道/代理关系用显式 Rel 边（如 router → atunnel，标签 `mTLS :443`），不要只靠节点位置暗示；
- 部署图标注 namespace 名（如 substrate-system / substrate-worker），提升部署语义精度。

## 7. C4 容器描述只放关键词行

容器框内文本过长会渲染拥挤/截断（R1：*"容器描述文本过长，渲染时框内文字拥挤"*）。容器内只放 2-3 行关键词（职责 + 关键端口），详情下移到 HTML 说明列表。

## 8. 宽图提高渲染宽度/字号

节点边框与文字间距紧凑（如 824px 宽渲染被压缩）时，提高渲染宽度或字号，避免小屏压缩导致的文字挤压（R1：*"部署图节点边框与文字间距紧凑，建议提高渲染宽度/字号"*）。
