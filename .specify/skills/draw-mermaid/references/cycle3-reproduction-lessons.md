# Cycle 3 R1 Improvements — draw-mermaid

> **Dated 历史记录**：本文件是 Cycle 3 评审的原始证据记录，不作现行规范引用。其脚手架技术（等高锚点、`~~~` 行锁、sans-serif、2x 导出、版本 pin、curve:linear）已泛化进现行 owner [sds-realization.md](sds-realization.md)。

> R1 weighted avg: 0.723 (rank 5/5). Structural layout failure: zones render at different heights/offsets, breaking the core "three parallel network boundaries" message.

## Mandatory fixes for redraw (ALL must be applied)

1. **Equal-height, top-aligned zone panels**: THIS IS THE CRITICAL FIX. Currently 用户网络 sits lower and shorter, Aone/ASO spans full height, and 阿里云 collapses to a small content-hugging box floating mid-right. The target shows THREE equal-height, top-aligned, full-canvas dashed panels side by side. Fix by:
   - Adding invisible full-height anchor/spacer nodes at TOP and BOTTOM inside EACH subgraph (minimum 2 per subgraph) to force equal vertical extent
   - OR switching to `block-beta` diagram type with explicit column heights if flowchart cannot achieve equal-height subgraphs
   - All three zone titles must form ONE horizontal reading line at the same y-position
2. **Sans-serif font**: replace the default serif typeface with sans-serif. Add init directive: `%%{init: {'theme': 'default', 'themeVariables': {'fontFamily': 'Arial, Helvetica, sans-serif'}}}%%`
3. **Straight solid arrows with filled heads**: replace thin elbow/polyline connectors with straight solid lines and filled black triangular arrowheads. Use `curve: linear` (already set — verify it takes effect) and ensure link style is `stroke: #000, stroke-width: 2px` with filled arrowhead markers.
4. **Higher export resolution**: current raster is ~half the target's pixel density. Export at minimum 2x scale (e.g. `--scale 2` or `--width 3200`) so strokes and text are crisp at display size.
5. **Pin mermaid version**: add version pin in the init directive or render command so layout scaffolding reproduces identically (e.g. record the mermaid.ink API version or use a pinned local mmdc version).
6. **Widen 阿里云 cluster**: the 阿里云 zone must be visually comparable in width to the other two zones, not a narrow content-hugging box.

## Invariants (DO NOT CHANGE)

- Declarative .mmd source (excellent maintainability — keep)
- All 21 components, 5 arrows, 3 subgraphs semantically present in source
- Invisible link (`~~~`) scaffolding pattern for rank/order control (but extend it with the anchor-node fix above)
- `flowchart LR` direction (left-to-right zone ordering matches target)
