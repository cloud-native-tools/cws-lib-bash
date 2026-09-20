# SDS 实现手册（PlantUML 语法层）

> **本文件拥有什么**：draw-plantuml 作为**语法层**实现 draw-diagram SDS 的落地点——「SDS 档位 → PlantUML 语法」映射（含实测值）、SDS 几何**逼近**配方、偏离声明模板。
> **本文件不拥有什么**：SDS schema、档位语义（T1–T4 相对层级与"谁该更显眼"）、偏离声明**规则**属语义层，见 `../../draw-diagram/references/semantic-model.md`（此处只落地、不重述）。
> **非委派场景**（用户直接调用本技能、无 SDS 输入）：用本技能默认档位与样式 [guide/style.md §十一](guide/style.md)，布局技巧 [guide/layout.md](guide/layout.md)，大图技术栈 [guide/large-diagram-playbook.md](guide/large-diagram-playbook.md)。

---

## 0. 输入契约：只实现，不改语义

委派输入 = **SDS 文件路径**（Semantic Drawing Spec：逻辑模型 elements/relations/zones + 几何 canvas/box/anchor + `weight_plan` 档位 + typography 层级）。

| 允许（语法层职责） | 禁止（语义层职责） |
|---|---|
| 选 PlantUML 图类型与元素关键字（`rectangle`/`component`/`package`/`entity`…）承载 SDS 元素 | 增删/重命名/合并 SDS 元素与关系 |
| 用 skinparam / `<style>` / 宏把档位落成绝对线宽、深浅、虚实 | 改写 zone 成员、`layout`（equal-height/stack/grid/free）语义 |
| 用脚手架（隐藏边、占位节点、方向关键字）**逼近**几何 | "优化"复刻版面（`fidelity_intent=reproduction` 时照抄源图语义） |
| 补 SDS 未声明的引擎必需项（渲染参数、字体、图例）并在回报中声明 | 自行调整权重层级顺序或把关键路径加粗越过结构档 |

SDS 缺项 → 按本技能默认流程补，并在最终回报里逐项声明"补了什么、按什么默认"。

---

## 1. 强弱实现：SDS 档位 → PlantUML 语法（经 PlantUML server 实测）

### 1.1 默认映射（新建类 SDS；SDS 只给相对档，绝对值由本表落实）

| SDS 档 | 语义角色（相对权重见语义层） | PlantUML 落地 | 实测 `stroke-width`（@scale 4） |
|---|---|---|---|
| **T1** | 大模块 / 分区（zone）边界 | `skinparam rectangle<<zone>> { BorderThickness 3 }` | **37.5**（=3px） |
| **T2** | 小模块 / 子容器边界 | `skinparam rectangle<<sub>> { BorderThickness 2 }`（或 `package<<sub>>`） | **25**（=2px） |
| **T3** | 数据流 / 依赖连线 | `skinparam ArrowThickness 1.2` | **15**（=1.2px） |
| **T4** | 注释 / 副标题 | 保持基线不加粗 + `skinparam noteFontColor #90A4AE` 压浅 | 12.5 / 6.25（基线） |
| （叶元素边框） | 不属 SDS 结构档 | 引擎默认（`component`），**不得高于 T3** | 6.25（≈0.5px） |

> ⚠️ **档位编号勿跨表抄**：本技能**独立默认表** [guide/style.md §十一](guide/style.md) 的四档编号与本表不同（那里 T3=叶元素边框、T4=流线）。受委派时以**语义层编号**（本表 = SDS `weight_plan`：T3=数据流、T4=注释）为准，两表只共享"结构档压过流线档"的层级不变式，不共享编号。

### 1.2 可直接抄的配方（档位常量用宏承载）

```plantuml
@startuml
' ── SDS 档位常量：!define 宏承载（渲染脚本 strip_style 不剥离宏行）──
!define SDS_T1 3        ' 大模块/分区边界
!define SDS_T2 2        ' 小模块/子容器边界
!define SDS_T3 1.2      ' 数据流/依赖连线
hide stereotypes        ' 构造型只用于选样式，不在图上显示 «zone»
skinparam rectangle<<zone>> {
  MinimumWidth 420      ' 逼近 SDS zone 宽度 / 拉平多 zone 等宽（下限，非精确等宽）
  BorderThickness SDS_T1
  BorderColor #37474F   ' 深浅随档位递减：T1 最深
  BorderStyle dashed    ' 需要虚线分区时用本键 —— 不要用内联 #line.dashed（见 1.3）
}
skinparam rectangle<<sub>> {
  BorderThickness SDS_T2
  BorderColor #607D8B
}
skinparam ArrowThickness SDS_T3
skinparam noteFontColor #90A4AE          ' T4：注释退到最浅
' …元素与关系：rectangle "标签" as za <<zone>> { … }（构造型在别名前后均可，勿再追加 #line.dashed 尾缀）…
@enduml
```

### 1.3 四条硬规则（每条都来自实测，违反即静默失效）

1. **内联样式尾缀会重置作用域块的粗细/颜色**：`rectangle "标签" <<zone>> as za #line.dashed { … }` 把块内 `BorderThickness 3` 覆盖回基线（实测 37.5 → 12.5），`#line.dashed;line.bold` 同样无效。虚线 + 粗边框只能由块内 **`BorderStyle dashed` + `BorderThickness N`** 共同给出（或 `skinparam packageBorderStyle dashed` + `package<<zone>>`，实测同样得到 3px 虚线）。构造型写在别名**前或后都可以**（`rectangle "X" <<zone>> as z` 与 `rectangle "X" as z <<zone>>` 实测都生效）——失效的是尾缀，不是顺序。
2. **档位常量不要用扁平 skinparam 行承载**：`render-plantuml.sh` 的 `strip_style` 会删除与注入键同名的扁平行（`monochrome true`、`shadowing`、`roundCorner`、`dpi`、`defaultFontSize`、`defaultFontName`、`padding`、`svgDimensionStyle`、`svgLinkTarget`、`actorStyle`）、`scale …` 行与裸 `FontSize N` 行；`!define` 宏行、stereotype 作用域块、`skinparam ArrowThickness/BorderThickness` 全局行**不在剥离集合内**（注入块之后出现即整体覆盖基线）。
3. **嵌套 `<style>` 选择器与单行冒号写法不可靠**：`package { package { … } }` 不生效、`LineThickness 3 : LineColor #…` 在真实大图上解析爆炸（stroke-width 出天文数字）。要么用本节的 stereotype 作用域 skinparam，要么用**扁平选择器 + 多行属性**的 `<style>`（写法见 [guide/style.md §十一](guide/style.md)）。
4. **`skinparam packageStyle rectangle` 会抑制虚线**（复刻评审 R1 教训）；要虚线分区就不要开它。

### 1.4 复刻类 SDS：源图实测权重覆盖默认档

`fidelity_intent=reproduction` 的 SDS 携带**从源图量出来的绝对权重**（如"zone 边框 4px、流线 1px、子模块 2.5px"）。此时**以 SDS 实测值替换 §1.1 的默认数字**（宏常量改值即可，配方结构不变），**不得回落到默认档**；渲染后按 §1.5 复量并与 SDS 声明值比对，差值 >0.5px 记入偏离声明。

### 1.5 自检（确定性优先，别靠肉眼）

```bash
grep -oE 'stroke-width:[0-9.]+' <out>.svg | sort | uniq -c   # 须见 ≥3 档：37.5 / 25 / 15
```

- 三档不可辨、或全图单一 `stroke-width` → 判不合格（语义层同判据）。
- 关键路径只允许**色相**抬升，`[thickness=2]` 封顶（≤ T2），不得反压结构档。
- **深浅与单色**：默认注入 `monochrome true` 时色相被灰度化，但**深浅层级仍保留**（实测 T1 `#37474F`→`#434343` 深于 T2 `#607D8B`→`#757575`）；若 SDS 要求按色相分档，走保色配方（源中放 `skinparam monochrome false` + 至少一处 `<color:#…>` 标记，见 [guide/large-diagram-playbook.md §2](guide/large-diagram-playbook.md)）。

---

## 2. 几何逼近：graphviz 自动布局下的 SDS geometry

PlantUML（UML/ER 类）走 graphviz 自动布局：**没有绝对坐标输入通道**。SDS 的 `box{x,y,w,h}`、`anchor`、`gap` 只能**逼近**，逼近不了的必须量化声明（§3）。

### 2.1 能做的（实测有效）

| SDS 几何意图 | 语法手段 | 实测效果 / 边界 |
|---|---|---|
| zone 目标宽度、多 zone 等宽 | `skinparam rectangle<<zone>> { MinimumWidth N }` | **下限**而非精确等宽：N=420 时两 zone 实测 472px / 453px（内容同宽时严格相等，内容不等宽时差 ~4%）；内容更宽的 zone 会超出 → 残差要量、要声明 |
| 上下秩（谁在谁上方） | `A -[hidden]down- B` | 稳定约束 rank（实测 zone 严格上下堆叠） |
| 同排 / 跨列对齐同类行 | `A -[hidden]right- B`（跨列"肋网格"串链） | **不改变 rank**，只把元素拉到同排/收拢游离元素；多列对应行串链可拉到同一水平线 |
| 列错位 stagger、锁列序 | 隐藏链 + 每列独立锚点 | 只能部分逼近；跨 cluster 强制 same-rank **做不到**（真实依赖边决定 rank，强行加锚点净负收益，见 [guide/large-diagram-playbook.md §4c](guide/large-diagram-playbook.md)） |
| 撑高/撑宽某区（等高 zone 逼近） | `<<ph>>` 透明占位节点：`skinparam rectangle<<ph>> { BackgroundColor transparent; BorderColor transparent }` + 标签用**全角空格 U+3000** 控宽（实测 1 个 U+3000 → 162.5px，渲染为 `stroke:none` 不可见） | 占位节点上的 `MinimumWidth` **不生效**（实测声明 260 → 渲染 62.5px）→ 宽度只能靠 U+3000 个数估，属"脆"手段，偏离要声明 |
| 主流方向 / 宽高比 | `top to bottom direction`、`left to right direction`、`nodesep`/`ranksep`、`linetype ortho` | 决策规则见 [guide/layout.md §2.1/§2.5](guide/layout.md)；SDS 已声明 canvas 宽高比时按 SDS 选方向，实测比值写入回报 |
| 关系 anchor / gap | 无对应输入 | 由引擎决定；SDS 指定 `anchor: corner` 等一律记为偏离 |

> 布局陷阱（LTR 下 `-right->` 被重解释、actor→zone 内元素致 zone 膨胀、嵌套 rectangle 内 `together{}` 失效、note 撑大 zone）见 [howto/10-layout-planning.md §三](howto/10-layout-planning.md) 与 [guide/layout.md §五](guide/layout.md)——它们直接决定几何逼近的可达上限。

### 2.2 量测（偏离必须"量出来"，不许目测）

- **WBS / 甘特图**：用 [../scripts/measure-svg-layout.py](../scripts/measure-svg-layout.py) 量三判据（有效字号 ≥12px、长宽比 1.2~1.8、标签不越时间轴右边界），`--compare` 做 A/B 判断某写法有没有改写排期。
- **UML / ER（graphviz）图**：量 SVG 几何与线宽，作为偏离幅度的证据来源：

```bash
python3 - <<'PY'
import re, sys
s = open(sys.argv[1] if len(sys.argv)>1 else "out.svg").read()
vb = [float(v) for v in re.search(r'viewBox="([\d.\s-]+)"', s).group(1).split()]
print("viewBox", vb, "aspect", round(vb[2]/vb[3], 3))
for r in re.findall(r'<rect[^>]*?/>', s):
    if 'stroke:none' in r: continue
    a = dict(re.findall(r'([a-zA-Z]+)="([^"]*)"', r))
    sw = re.search(r'stroke-width:([\d.]+)', r)
    print(a.get('x'), a.get('y'), a.get('width'), a.get('height'), "sw=", sw.group(1) if sw else "-")
PY
```

（坐标/宽高为 `scale 4` 后的像素，除以 4 得基础像素；`stroke-width` 除以 12.5 得 px 线宽。）

---

## 3. 偏离声明模板（自动布局引擎 MUST 量化）

规则归属语义层（`../../draw-diagram/references/semantic-model.md` § Deviation Declaration）：**未声明的偏离按 semantic-fidelity 扣分；已声明且量化的偏离计入引擎实现质量，不算语义缺陷**。交付时随产物回报以下表（无偏离则写"零偏离"并给出实测证据）：

```markdown
## 偏离声明（plantuml / graphviz 自动布局）
| SDS 项 | SDS 目标值 | 实测值 | 偏离幅度 | 引擎原因 | 处置 |
|--------|-----------|--------|---------|---------|------|
| zone "接入区" box.w | 420px | 453px | +7.9% | graphviz 按内容+padding 撑框，MinimumWidth 只是下限 | 已用 MinimumWidth 逼近；接受 |
| zone 等宽（3 区） | 三区等宽 | 453/448/390px | 最大 −14% | 内容宽度不同，无绝对宽度通道 | 已压标签长度；残差声明 |
| zone-A box.x/y | (40,60) | 不可控 | 全量 | 自动布局无绝对坐标输入 | 用 -[hidden]down- 锁秩替代 |
| zones equal-height | 三区等高 | 1588/1588/1250px | 第三区 −21% | 无 height 通道；<<ph>> 占位仅部分撑高 | 加 U+3000 占位；残差声明 |
| relation r3 anchor | corner | edge-midpoint | 全量 | anchor 不可指定 | 声明为引擎限制 |
| stagger（service 居中 / robot 左下） | 错位 | 竖直堆叠 | 全量 | 跨 cluster same-rank 不可强制 | 隐藏链部分逼近；声明 |
| T1 线宽 | 3px（SDS 实测 4px） | 3px | −1px | 复刻 SDS 值未覆盖默认档 | 改宏常量 SDS_T1=4 重渲 |
```

填写纪律：**每行都要有实测数字**（来源 = §2.2 的量测），禁止"大致接近/基本一致"；幅度用 % 或 px；原因必须是引擎机制（不是"忘了"）；能修的先修再声明，不能修的写清"已试过的逼近手段"。

---

## 4. 交付前自检清单

- [ ] SDS 元素/关系/zone 成员**逐条对得上**（数量 + 标签集合 + 边方向），无擅自增删
- [ ] 档位落地：`stroke-width` ≥3 档可辨（37.5/25/15），T1 深于 T2、结构档压得住流线
- [ ] 关键路径仅色相抬升、`thickness ≤ 2`；全图单一线宽 = 不合格
- [ ] 复刻类：SDS 源图实测权重已覆盖默认档，且复量差值 ≤0.5px（否则进偏离表）
- [ ] 几何残差已量测并写入偏离声明表（含"零偏离"也要给证据）
- [ ] typography 层级按 SDS（相对层级）落实为绝对字号，跨图统一 16px 基线（渲染脚本注入）
- [ ] 渲染走远端 server；本地产物含 SVG + PNG + `.puml` + HTML 复现性附录（见 [howto/12-rendering-and-output.md](howto/12-rendering-and-output.md)）

---

## 相关

- 复刻评审固化的不变式与 R1 教训（本文件 §1.3/§2.1 的来源记录）：[cycle3-reproduction-lessons.md](cycle3-reproduction-lessons.md)
- 默认（非委派）样式规范与档位表：[guide/style.md §十一](guide/style.md)
- 布局技巧全量：[guide/layout.md](guide/layout.md)；大图技术栈：[guide/large-diagram-playbook.md](guide/large-diagram-playbook.md)
- 索引：[index.md](index.md)
