# Cycle 4 R1 Improvements — draw-plantuml（语法层）

1. 组件标签居中：`defaultTextAlignment center`（SDS placement=center-of-box；当前左对齐）。
2. 盒填充改白：`BackgroundColor white`（当前灰填充破坏 monochrome 意图）。
3. n10 宽度用 label padding 区分（MinimumWidth 是下限不是等宽器）；其余盒宽向实测 228px 比例归一。
4. 圆角 pin 12px；zone dash 粒度偏离 +70% 尝试收窄（BorderStyle dash 参数若不可控则声明）。
