# Cycle 4 R1 Improvements — draw-echarts（语法层）

1. 补像素读回 QA（d3js 式 readback）以实证 zero-deviation 声明（R1 指出声明无证据）。
2. zone 标题去 bold：源层级仅靠字号（size-only），不得加字重。
3. 箭头 symbolSize 收缩到实测 18–23px head；当前 head 偏大且挤占盒角。
