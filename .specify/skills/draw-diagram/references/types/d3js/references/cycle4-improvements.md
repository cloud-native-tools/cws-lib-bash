# Cycle 4 R1 Improvements — d3js（语法层）

> Dated record：本文件记的是 cycle 4 R1 的原始待办，不作为当前规范引用。第 1、3 条已**收编**为
> [sds-realization.md](sds-realization.md) §4「关三：渲染读回 ↔ 源图差量」的检查项（规范以该处为准，
> 此处只留指针）；第 2 条仍为待办。

1. 将 4 条微偏离折进 in-page QA 表（machine-checkable manifest），deviation-manifest.md 与页面 QA 同源。→ 已收编：§4 关三第 7 条。
2. 渲染时从 SDS YAML 加载几何（单一来源），不再内联字面量坐标；r3 的 13px head-gap 提为命名常量。
3. 读回校验线宽：视觉裁判读感 ~1.5px，需确认 T2/T3 落实为实测 2px（stroke-centering 补偿）。→ 已收编：§4 关三第 6 条。
