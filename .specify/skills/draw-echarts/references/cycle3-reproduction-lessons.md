# Cycle 3 R1 Improvements — draw-echarts

> R1 weighted avg: 0.840 (rank 4/5). Critical defects: missing arrowhead, toolbox artifact, dead whitespace, box shadows.

## Mandatory fixes for redraw (ALL must be applied)

1. **Arrowheads on ALL directed edges**: the Qoder→xuanji-cli edge renders as a plain line with NO arrowhead. Set `symbol: ['none', 'arrow']` uniformly on ALL 5 edges. Verify each edge has a visible filled triangular head at the target end. Arrowhead must point ALONG the line direction into the target box's left edge (not downward into box bottoms).
2. **Remove toolbox artifact**: disable the ECharts toolbox `saveAsImage` button entirely (`toolbox: { show: false }`) OR hide it during headless PNG export. The exported render.png must contain NO UI chrome — only the diagram.
3. **Eliminate bottom dead band**: ~15% empty whitespace below the zones. Size the export viewport/canvas to the content bounding box. Zones must fill the full canvas height as in the target.
4. **Remove box drop-shadows**: component boxes show a visible dark offset shadow (数字员工, xuanji-robot, xuanji-agent). Disable all `shadowBlur`/`shadowColor`/`shadowOffset` — target uses clean single thin black strokes only.
5. **Arrow tip landing**: nudge arrow endpoints to land on target box edge midpoints, not box corners.

## Invariants (DO NOT CHANGE)

- External `architecture.config.json` as single source of truth (good pattern — keep it)
- 4 invisible 1×1 corner anchor nodes for bounds-fit identity (required for `graph layout:'none'`)
- All 21 components, 5 edges, 3 zones present with correct labels
- `lineStyle.opacity: 1` on all edges (already fixed in R1 — do not regress)
- Per-node exact-size `path://` rounded-rect symbols with radius 10 (already fixed — keep)
