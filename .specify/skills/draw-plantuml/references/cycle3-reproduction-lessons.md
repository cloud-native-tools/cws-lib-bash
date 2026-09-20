# Cycle 3 R1 Improvements — draw-plantuml

> **性质**：本文件是 Cycle 3 R1 的**当期记录**（dated record），不作为当前配方来源。其中仍然成立的不变式（stereotype 作用域 skinparam + `hide stereotypes` 的虚线分区配方、`-[hidden]down-` 锁秩 / `-[hidden]right-` 不锁秩、`<<ph>>` 透明占位、远端渲染、`scale 4`/`dpi 300`）已被重述为 SDS 逼近技术并**以 [sds-realization.md](sds-realization.md) 为准**；两者不一致处（如内联 `#line.dashed` 尾缀会把作用域块的 `BorderThickness` 重置回基线、虚线须改用块内 `BorderStyle dashed`）按复验后的 sds-realization.md §1.3 执行。

> R1 weighted avg: 0.853 (rank 3/5). Good structure; defects are zone width imbalance, heavy arrows, coarse dashes, non-uniform box sizes.

## Mandatory fixes for redraw (ALL must be applied)

1. **Equalize zone widths**: the 阿里云 panel is markedly wider than the other two, leaving a large empty right region. The target uses three near-equal-width panels. Fix by:
   - Using fixed-width stereotype-scoped skinparam or explicit `skinparam minClassWidth`-equivalent for rectangle containers
   - OR adding invisible width-constraining elements to the narrower zones / reducing padding in the wider zone
   - All three zones must have visually comparable widths (within ~10% of each other)
2. **Thin arrows with small arrowheads**: arrows are much thicker with oversized heads versus the target's thin lines with small solid triangles. Set:
   - `skinparam ArrowThickness 1.2` (or lower)
   - `skinparam ArrowHeadSize 6` (or equivalent small size)
   - Match the target's monochrome thin-line weight
3. **Fine dash pattern for zone borders**: zone borders use coarse long dashes. The target uses a fine, short-dash pattern. Adjust `skinparam packageBorderStyle dashed` rendering or use a custom dash length if the server supports it. If dash granularity cannot be controlled, accept the default but ensure border weight is thin (1px).
4. **Normalize component box sizes**: FBI, SLS, RDS, 钉钉 boxes render visibly narrower/smaller than column neighbors. The target uses uniform box sizes per column. Enforce equal widths via:
   - Consistent label padding (add spaces or use `skinparam Padding`)
   - OR a fixed-width skinparam for all component rectangles
5. **Inner padding**: add margin so boxes (xuanji-console, xuanji-cli, Qoder) do NOT touch their zone borders. Minimum 8-10px visual gap between any component box and its containing zone border.
6. **Aone/ASO stagger**: xuanji-service and xuanji-robot stack vertically in the right column; the target staggers them (service centered, robot bottom-left). Extend the hidden-link scaffolding to reproduce this stagger.

## Invariants (DO NOT CHANGE)

- Stereotyped rectangle containers (`rectangle "X" <<zone>>` + `hide stereotypes`) with stereotype-scoped skinparam — this is the working recipe for dashed borders (packageStyle rectangle suppresses dashed — lesson from R1)
- Hidden-edge semantics: `-[hidden]down-` constrains rank (keep), `-[hidden]right-` does not (avoid)
- Invisible transparent placeholder nodes (`<<ph>>`) for full-height zones — keep but consider replacing brittle ideographic-space labels with sized placeholders if possible
- All 21 components, 5 arrows, 3 zones present with correct labels
- Remote server rendering (do NOT switch to local)
- `scale 4` / `dpi 300` for high-resolution output
