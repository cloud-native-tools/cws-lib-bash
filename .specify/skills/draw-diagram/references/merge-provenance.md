# Merge Provenance — draw-diagram

Capability-inheritance record for the six engine skills merged into this one on 2026-10-12.
Committed, not scratch: it is the standing evidence that this skill still covers what its
sources could do, and the only way a later session can re-check that.

Re-verify (from the repository root; the record names a literal path because `${SKILL_HOME}`
would resolve to *this* skill's home, not to merge-skills'):

```bash
python3 .specify/skills/merge-skills/scripts/provenance_check.py skills/external/draw-diagram
# installed-mirror equivalent:
python3 .specify/skills/merge-skills/scripts/provenance_check.py .specify/skills/draw-diagram
```

Each source's `**Corpus**` is scoped to its own engine layer plus this skill's shared docs.
That scoping is load-bearing: 14–34% of one engine's fact tokens also occur in its siblings,
so an unscoped corpus would read a fact lost from one engine as covered by another.

The method and flow below are this skill's own; only the **responsibility** is inherited.
`verified` means the destination exists and the capability was walked through at merge time;
the Verification column names how to check it again.

## Source: draw-d3js

- **Merged**: 2026-10-12
- **Source identity**: `draw-d3js` · `<SKILL:.specify/skills/draw-d3js/SKILL.md>` · class: peer (host-managed)
- **Retirement registered**: `_OBSOLETE_SKILLS` in `src/specify_cli/__init__.py`
- **Baseline**: `./merge-provenance/d3js.baseline.txt`
- **Corpus**: `references/types/d3js`, `references/*.md`, `SKILL.md`

### Capability inheritance

| # | Capability (what the source could do) | Target destination | Verification | Status |
|---|---------------------------------------|--------------------|--------------|--------|
| 1 | Build bespoke interactive D3 data visualizations delivered as standalone HTML | `references/types/d3js/d3js.md` | data-join → interaction → HTML recipe present; `references/types/d3js/assets/template.html` on disk | verified |
| 2 | Reproduce an existing image pixel-for-pixel with absolute-coordinate SVG and no layout engine | `references/types/d3js/references/cycle3-reproduction-lessons.md` | measure-from-source flow and reproduction lessons present | verified |
| 3 | Realize the SDS geometry and weight contract in D3 | `references/types/d3js/references/sds-realization.md` | `box{x,y,w,h}` realization rules present | verified |
| 4 | D3 syntax/API guidance, official-doc lookup, and known pitfalls | `references/types/d3js/references/d3js-guide.md` | guide + `references/d3js-official-docs.md` + `best-practices/pitfalls.md` present | verified |
| 5 | Cycle-4 improvement lessons for reproduction fidelity | `references/types/d3js/references/cycle4-improvements.md` | file present and linked from the engine entry doc | verified |

## Source: draw-drawio

- **Merged**: 2026-10-12
- **Source identity**: `draw-drawio` · `<SKILL:.specify/skills/draw-drawio/SKILL.md>` · class: peer (host-managed)
- **Retirement registered**: `_OBSOLETE_SKILLS` in `src/specify_cli/__init__.py`
- **Baseline**: `./merge-provenance/drawio.baseline.txt`
- **Corpus**: `references/types/drawio`, `references/*.md`, `SKILL.md`

### Capability inheritance

| # | Capability (what the source could do) | Target destination | Verification | Status |
|---|---------------------------------------|--------------------|--------------|--------|
| 1 | Author uncompressed mxGraph XML diagrams (`.drawio`) with native shape libraries | `references/types/drawio/drawio.md` | `mxGraphModel` structure and no-compression rule present | verified |
| 2 | Export headlessly to SVG / PNG / PDF via the draw.io CLI | `references/types/drawio/references/render-and-export.md` | `drawio -x -f svg\|png\|pdf` recipes present | verified |
| 3 | mxGraph format reference (cells, geometry, styles) | `references/types/drawio/references/mxgraph-format.md` | format doc present | verified |

## Source: draw-echarts

- **Merged**: 2026-10-12
- **Source identity**: `draw-echarts` · `<SKILL:.specify/skills/draw-echarts/SKILL.md>` · class: peer (host-managed)
- **Retirement registered**: `_OBSOLETE_SKILLS` in `src/specify_cli/__init__.py`
- **Baseline**: `./merge-provenance/echarts.baseline.txt`
- **Corpus**: `references/types/echarts`, `references/*.md`, `SKILL.md`

### Capability inheritance

| # | Capability (what the source could do) | Target destination | Verification | Status |
|---|---------------------------------------|--------------------|--------------|--------|
| 1 | Standard data-series charts (bar/line/pie/scatter/radar/gauge/funnel/sankey/sunburst/boxplot/K-line) as interactive HTML | `references/types/echarts/echarts.md` | series catalogue and option contract present | verified |
| 2 | Dashboards with toolbox and chart linkage interaction | `references/types/echarts/references/echarts-guide.md` | toolbox/linkage guidance present | verified |
| 3 | Mechanically verify the delivered artifact | `references/types/echarts/scripts/verify-deliverable.mjs` | `node --check references/types/echarts/scripts/verify-deliverable.mjs` | verified |
| 4 | Mechanically check layout against the SDS boxes | `references/types/echarts/scripts/check-layout.mjs` | `node --check references/types/echarts/scripts/check-layout.mjs` | verified |
| 5 | Vendor ECharts locally for offline self-contained HTML | `references/types/echarts/scripts/vendor-echarts.sh` | `bash -n references/types/echarts/scripts/vendor-echarts.sh`; `.specify/scripts/sync-config.mjs` passes `node --check` | verified |
| 6 | Realize the SDS geometry and weight contract in ECharts | `references/types/echarts/references/sds-realization.md` | `layout:'none'` + corner-anchor realization rules present | verified |

## Source: draw-excalidraw

- **Merged**: 2026-10-12
- **Source identity**: `draw-excalidraw` · `<SKILL:.specify/skills/draw-excalidraw/SKILL.md>` · class: peer (host-managed)
- **Retirement registered**: `_OBSOLETE_SKILLS` in `src/specify_cli/__init__.py`
- **Baseline**: `./merge-provenance/excalidraw.baseline.txt`
- **Corpus**: `references/types/excalidraw`, `references/*.md`, `SKILL.md`

### Capability inheritance

| # | Capability (what the source could do) | Target destination | Verification | Status |
|---|---------------------------------------|--------------------|--------------|--------|
| 1 | Hand-drawn-style diagrams authored as Excalidraw scene JSON | `references/types/excalidraw/excalidraw.md` | scene-element authoring flow present | verified |
| 2 | Render scene JSON to SVG/PNG through a self-hosted headless-Chromium service | `references/types/excalidraw/scripts/render-excalidraw.sh` | `bash -n references/types/excalidraw/scripts/render-excalidraw.sh`; `.specify/scripts/server/server.mjs` passes `node --check` | verified |
| 3 | Bridge a mermaid definition into a hand-drawn rendering | `references/types/excalidraw/references/howto/01-path-selection.md` | mermaid→excalidraw path selection present | verified |
| 4 | Scene-schema reference (elements, appState, files) | `references/types/excalidraw/references/guide/scene-schema-reference.md` | schema doc present | verified |
| 5 | Self-deploy the excalidraw render service | `references/types/excalidraw/references/guide/server-deployment.md` | deployment doc present; port authority in `references/self-deploy-render-service.md` §0.1 | verified |
| 6 | Semantic analysis, scene generation, and rendering how-tos | `references/types/excalidraw/references/howto/00-semantic-analysis.md` | howto set 00/01/03/04 present | verified |
| 7 | Realize the SDS geometry and weight contract in Excalidraw | `references/types/excalidraw/references/sds-realization.md` | realization rules present | verified |

## Source: draw-mermaid

- **Merged**: 2026-10-12
- **Source identity**: `draw-mermaid` · `<SKILL:.specify/skills/draw-mermaid/SKILL.md>` · class: peer (host-managed)
- **Retirement registered**: `_OBSOLETE_SKILLS` in `src/specify_cli/__init__.py`
- **Baseline**: `./merge-provenance/mermaid.baseline.txt`
- **Corpus**: `references/types/mermaid`, `references/*.md`, `SKILL.md`

### Capability inheritance

| # | Capability (what the source could do) | Target destination | Verification | Status |
|---|---------------------------------------|--------------------|--------------|--------|
| 1 | Repo-native declarative text diagrams (flowchart, sequence, class, state, ER, gantt, mindmap, WBS, JSON, YAML) rendered natively by GitHub/CI | `references/types/mermaid/mermaid.md` | chapter set `references/types/mermaid/references/document/00..16` present | verified |
| 2 | Render mermaid text to SVG/PNG via a mermaid.ink-compatible backend | `references/types/mermaid/scripts/render-mermaid.sh` | `bash -n references/types/mermaid/scripts/render-mermaid.sh`; `MERMAID_SERVER` override documented | verified |
| 3 | CJK-safe SVG→PNG conversion | `references/types/mermaid/scripts/svg-to-png-cjk.cjs` | `node --check references/types/mermaid/scripts/svg-to-png-cjk.cjs` | verified |
| 4 | Measure effective font size in dense diagrams before delivery | `references/types/mermaid/scripts/measure-svg-layout.py` | `python3 -m py_compile references/types/mermaid/scripts/measure-svg-layout.py` | verified |
| 5 | Self-host a single-engine mermaid render server (fallback form) | `references/types/mermaid/server/README.md` | `bash -n references/types/mermaid/server/docker-run.sh`; port authority in `references/self-deploy-render-service.md` §0.1 | verified |
| 6 | Modeling methodology, GRASP principles, and content/style guides | `references/types/mermaid/references/document/08-modeling-methodology.md` | `09-grasp-principles.md` + `references/guide/content.md` + `references/guide/style.md` present | verified |
| 7 | Realize the SDS geometry and weight contract in mermaid | `references/types/mermaid/references/sds-realization.md` | realization rules present | verified |

## Source: draw-plantuml

- **Merged**: 2026-10-12
- **Source identity**: `draw-plantuml` · `<SKILL:.specify/skills/draw-plantuml/SKILL.md>` · class: peer (host-managed)
- **Retirement registered**: `_OBSOLETE_SKILLS` in `src/specify_cli/__init__.py`
- **Baseline**: `./merge-provenance/plantuml.baseline.txt`
- **Corpus**: `references/types/plantuml`, `references/*.md`, `SKILL.md`

### Capability inheritance

| # | Capability (what the source could do) | Target destination | Verification | Status |
|---|---------------------------------------|--------------------|--------------|--------|
| 1 | Strict-UML diagrams (component, deployment, sequence, class, package, usecase, activity, state) with automatic layout | `references/types/plantuml/plantuml.md` | chapter set `references/types/plantuml/references/document/00..15` present | verified |
| 2 | Six non-UML specialties: WBS, Gantt, MindMap, JSON, YAML, Salt UI wireframe | `references/types/plantuml/references/document/11-wbs-diagram.md` | siblings `12-gantt-diagram.md`, `13-mindmap-diagram.md`, `14-json-diagram.md`, `15-yaml-diagram.md` present; Salt in `references/guide/syntax-reference.md` | verified |
| 3 | ER / entity-relationship diagrams with crow's foot notation | `references/types/plantuml/references/guide/syntax-reference.md` | `entity` + crow's-foot syntax present; also `document/00-plantuml-overview.md` | verified |
| 4 | Render PlantUML to SVG/PNG via a PlantUML server | `references/types/plantuml/scripts/render-plantuml.sh` | `bash -n references/types/plantuml/scripts/render-plantuml.sh`; `PLANTUML_SERVER` override documented | verified |
| 5 | CJK-safe SVG→PNG conversion and effective-font-size measurement | `references/types/plantuml/scripts/svg-to-png-cjk.cjs` | `node --check` on it; `python3 -m py_compile references/types/plantuml/scripts/measure-svg-layout.py` | verified |
| 6 | Modeling methodology, GRASP principles, style and content guides | `references/types/plantuml/references/document/08-modeling-methodology.md` | `09-grasp-principles.md` + `references/guide/{style,content,layout}.md` present | verified |
| 7 | Realize the SDS geometry and weight contract in PlantUML | `references/types/plantuml/references/sds-realization.md` | §2.1 two-cycle hard rule present (pinned by `tests/contract/test_hidden_edge_two_cycle.py`) | verified |
