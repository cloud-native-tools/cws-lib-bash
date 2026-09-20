# Cycle 4 R1 Improvements — draw-d3js（语法层）

1. 将 4 条微偏离折进 in-page QA 表（machine-checkable manifest），deviation-manifest.md 与页面 QA 同源。
2. 渲染时从 SDS YAML 加载几何（单一来源），不再内联字面量坐标；r3 的 13px head-gap 提为命名常量。
3. 读回校验线宽：视觉裁判读感 ~1.5px，需确认 T2/T3 落实为实测 2px（stroke-centering 补偿）。
