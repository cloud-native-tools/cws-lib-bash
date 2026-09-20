# Cycle 4 R1 Improvements — draw-excalidraw（语法层）

1. manifest 的 "none" 行替换为实测读回值（measured readback），不得以未测量的 "none" 声明零偏离。
2. 矩形圆角 pin 到实测 12px（当前 ~16px）；箭头 head 比例对齐目标（T3 2px + 实测 head 尺寸）。
