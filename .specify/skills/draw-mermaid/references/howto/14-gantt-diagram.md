# 甘特图（14-gantt-diagram）

## 1. 适用场景

项目进度、任务依赖、里程碑、资源排期。

## 2. 基本语法

```mermaid
gantt
  dateFormat YYYY-MM-DD
  axisFormat %m-%d
  title 订单项目排期
  section 阶段一
  需求确认 : a1, 2026-08-01, 5d
  设计评审 : a2, after a1, 3d
  里程碑-设计完成 : milestone, m1, 2026-08-09, 0d
  section 阶段二
  后端开发 : b1, after m1, 10d
  前端开发 : b2, after m1, 8d
  联调 : after b1, 5d
```

- 任务：`名称 : id, 开始, 工期`；id 用于依赖（`after <id>`）；
- 依赖：`after a1`（也可 `after a1, b1` 多依赖）；
- 里程碑：`milestone`（0d 或指定日期）；
- 状态：`crit`（关键路径，红）、`active`（进行中，蓝）、`done`（完成，灰）；
- 完成度（v11.7+）：`任务 : id, 开始, 工期, progress 60`。

## 3. 日期与刻度

| 指令 | 说明 |
|------|------|
| `dateFormat YYYY-MM-DD` | 输入日期格式（也可 `YYYY-MM-DD HH:mm`） |
| `axisFormat %m-%d` | 横轴刻度格式（`%Y-%m-%d`、`%H:%M`、`%W` 周） |
| `excludes 2026-10-01, 2026-10-02` | 排除日期（节假日） |
| `weekends` / 默认 | 默认排除周末（`excludes` 仅列日期时） |
| `todayMarker off` | 关闭今日线（或 `todayMarker stroke-width:0`） |

## 4. 布局与间距

```mermaid
%%{init: {"gantt": {"barHeight": 24, "barGap": 6, "leftPadding": 70, "rightPadding": 20, "topPadding": 40, "sectionFontSize": 14}}}%%
gantt
  dateFormat YYYY-MM-DD
  axisFormat %m-%d
  section 阶段一
  任务A : a1, 2026-08-01, 5d
```

- 任务名 ≤10 字符，否则条形标签溢出；
- section ≤6 个；每 section 任务 ≤8。

## 5. 里程碑视图写法（管理层交付）

```mermaid
gantt
  dateFormat YYYY-MM-DD
  axisFormat %m-%d
  title 里程碑视图
  section 里程碑
  M1 环境就绪 : milestone, m1, 2026-08-10, 0d
  M2 服务上线 : milestone, m2, 2026-08-25, 0d
  M3 全量发布 : milestone, m3, 2026-09-05, 0d
```

- 里程碑编号（M1/M2/M3）与 WBS 图锚点一致（跨图对账）；
- 只画里程碑时任务全部省略。

## 6. 量测自检（交付前必做）

```bash
python3 skills/draw-mermaid/scripts/measure-svg-layout.py gantt.svg --display-width 1400
```

三判据：**正文有效字号 ≥12px**、**长宽比 1.2~1.8:1**、**标签不越过时间轴右边界**。
A/B 判断某写法是否改写排期：

```bash
python3 skills/draw-mermaid/scripts/measure-svg-layout.py a.svg --compare b.svg
```

看 `scheduleChanged` 字段（依赖箭头、标题字号、zoom 都可能实际影响排期布局）。

## 7. 常见陷阱

- `dateFormat` 与输入日期格式不匹配（渲染报错或错位）；
- 依赖写错 id（`after` 引用了不存在的 id）；
- 里程碑用任务画（0d + milestone 才是里程碑）；
- 任务名过长（标签溢出时间轴）；
- 排期改动靠肉眼判断（必须 `--compare` 量测）。
