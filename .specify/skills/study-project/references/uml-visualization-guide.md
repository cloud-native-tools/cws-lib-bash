# UML Visualization Guide — study-project

Normative rules for expressing study-project report views as standard UML diagrams. Rendering is **delegated to the draw-plantuml skill** — this package contains no rendering code; draw-plantuml owns diagram syntax, its `scripts/render-plantuml.sh`, and image conventions.

## 1. Primary views and required coverage

The report's **primary views** MUST be expressed as rendered UML figures:

| Analysis view | Primary diagram type | Acceptable alternative | draw-plantuml howto guide |
|---------------|----------------------|------------------------|---------------------------|
| Architecture structure (subsystems, modules, boundaries) | component | package | `draw-plantuml/references/howto/05-component-diagram.md` (or 07-package) |
| Key behavior flows (request/call chains, interactions) | sequence | activity (for business/process flows with decision branches) | `.../howto/04-sequence-diagram.md`, `.../howto/09-activity-diagram.md` |
| Deployment topology (nodes, runtime, delivery) | deployment | — | `.../howto/06-deployment-diagram.md` |
| Data structures (core entities, schemas) — where relevant | class | ER | `.../howto/08-class-diagram.md`, `.../howto/18-er-diagram.md` |

**Minimum coverage per report**: at least one figure for *architecture structure*, AND at least one figure for *behavior flow* or *deployment topology*. Add data-structure figures when the project's data model is a core selling point.

**Type-selection discipline**: choose the type that matches the view's semantics. If no UML type fits a view without misrepresenting it, keep that view textual/tabular — correctness of meaning outranks figure count. The `activity` alternative applies only to process/business-flow narratives; interaction and call-chain views stay on `sequence`.

## 2. Secondary content

Mermaid inline sketches remain acceptable for **secondary, quick-glance content only** (minor flows, small data illustrations). They are never a substitute for a primary-view UML figure.

## 3. Figure output conventions

- **Storage**: all figure files live under `$WORK_DIR/docs/figures/` (alongside the report at `$WORK_DIR/docs/overview.md`).
- **Formats**: every figure ships as **PNG + SVG** — embed the PNG, link the SVG for lossless zoom (follow draw-plantuml's single-mechanism rule: all-inline-HTML `<a href=x.svg target="_blank" rel="noopener"><img src=x.png></a>`, or all-plain-Markdown if HTML is stripped).
- **Sources**: keep the `.puml` source next to the images for future edits.
- **Captions**: every figure carries a brief caption — what the view shows and what the reader should notice.
- **References**: the report references figures by **relative paths** (`figures/<name>.png`); raw diagram source is never embedded in the reader-facing report.
- **Chart sets**: when one figure would be unreadable (too many elements), split into an overview figure plus drill-down figures with consistent naming and cross-references, per draw-plantuml's large-diagram guidance.

## 4. Rendering delegation

For each planned figure: write the `.puml` source following the mapped draw-plantuml howto guide, then render via draw-plantuml's `scripts/render-plantuml.sh <input.puml> docs/figures <name>` (PNG and SVG produced together). UML diagram types here (component/deployment/sequence/class/activity/ER) may require Graphviz `dot` for local-jar rendering; the server backend needs no local dependency — see draw-plantuml's rendering documentation for backend selection.

## 5. Degradation rule

If draw-plantuml rendering is unavailable during the run (server unreachable and no local jar, or Graphviz missing for the needed type):

1. Fall back to a Mermaid inline sketch for each affected primary view.
2. Add a visible **degradation note** next to each affected view, e.g. `> Note: UML rendering unavailable during this run; view shown as a Mermaid sketch.`
3. Keep the planned `.puml` sources (or the figure plan) in the drafts so figures can be rendered and swapped in later.

Never silently drop a primary view's figure.
