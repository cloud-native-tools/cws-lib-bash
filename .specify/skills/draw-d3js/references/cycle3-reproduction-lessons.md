# Cycle 3 R1 Improvements — draw-d3js

> R1 weighted avg: 0.963 (rank 1/5). Near-perfect reproduction. Minor refinements only.

> **Dated record.** 本文件是当次复刻竞技场的记录，其中的具体数值（21 nodes / 5 edges / 3 panels、viewBox 2000×1257）只属于那次运行，不作为当前规范引用。可通用的质量实践（zone-title 字重、数据分离为可校验 JSON 块、`?clean=1` 快照元数据、复刻不变量）已由 [sds-realization.md](sds-realization.md) §5 承载；源实测覆盖默认档位的规则见同文 §5。

## Mandatory fixes for redraw

1. **Zone-title font weight**: target uses regular/medium weight titles, NOT bold. Change zone title `font-weight` from `bold` to `normal` (or `500`) at the same font size.
2. **Data separation**: factor `PANELS`/`NODES`/`EDGES` arrays out of the inline script into a clearly delimited JSON block (or a `<script type="application/json">` element) so a validator can check 21 nodes / 5 edges / 3 panels without parsing JS. Keep the rendering logic reading from that block.

## Optional enhancements (do not regress fidelity)

3. Add a per-zone one-line role annotation (e.g. 用户网络=entry points, Aone/ASO=platform services, 阿里云=managed cloud services) as a subtle subtitle under each zone title — only if it does not alter layout or overlap components.
4. Surface node/edge metadata in the `?clean=1` static snapshot via `<title>` attributes so printed embeds carry information without visible HUD.

## Invariants (DO NOT CHANGE)

- Pixel-measured fixed coordinates (viewBox 0 0 2000 1257) — do NOT switch to force layout
- All 21 components, 5 arrows, 3 dashed zones must remain present and correctly positioned
- Monochrome palette, stroke widths, dash patterns as measured from target
