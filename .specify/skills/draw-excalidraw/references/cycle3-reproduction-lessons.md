# Cycle 3 R1 Improvements — draw-excalidraw

> R1 weighted avg: 0.880 (rank 2/5). Good structure and semantics; primary defect is hand-drawn rough style deviating from target's crisp strokes.

## Mandatory fixes for redraw (ALL must be applied)

1. **roughness: 0 on ALL elements**: the default hand-drawn wobble produces double-stroked, warped box outlines and zone borders. The target uses clean, crisp single-stroke rectangles. Set `"roughness": 0` on every rectangle, arrow, and text element in the scene JSON. This is an architecture REPRODUCTION task, not a whiteboard sketch.
2. **Sharp-cornered zone borders**: zone containers must use sharp corners (`"roundness": null` or type 0), NOT rounded hand-drawn corners. The target's zone borders are sharp dashed rectangles.
3. **Fine dash pattern for zones**: zone border `strokeStyle` must be `"dashed"` with a fine dash period matching the target (short dashes, not long hand-drawn segments).
4. **Arrowhead anchoring**: arrowheads are currently attached at box corners. Anchor them to target box EDGE MIDPOINTS with a small gap (2-4px) between arrowhead tip and box border, matching the target's arrow termination.
5. **Uniform box size grid**: snap all component boxes to a consistent width/height grid. Several boxes drift in size/rotation, breaking the target's precise staggered columns. All boxes in the same column must have identical width and height.
6. **Pin export scale**: set a fixed export scale factor (e.g. scale=2) in the render command so PNG dimensions are stable and deterministic across re-exports.

## Invariants (DO NOT CHANGE)

- Scene JSON direct path (NOT Mermaid bridge) — correct choice for free-layout topology
- Container-bound text (`containerId`) for all labels — keep this pattern
- Fixed seeds on all elements for determinism — keep
- All 21 components, 5 bound arrows, 3 zone containers present
- Bound text coordinates must carry exact centered values (renderer does NOT auto-recenter — lesson from R1)
- `endArrowhead: "triangle"` (solid triangular heads matching target)
