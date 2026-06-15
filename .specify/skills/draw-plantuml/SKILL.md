---
name: draw-plantuml
description: |
  Draw system architecture diagrams with PlantUML, render to SVG/PNG via PlantUML server, and output as HTML with rendered images.
  Use standard UML semantics (Component, Deployment, Sequence, Class/Package) to describe system architecture.
  Use when the user mentions "架构图", "architecture diagram", "UML图", "plantuml", "系统架构图", "画架构", "设计图", "组件图", "部署图", "时序图", "类图", "包图", "系统设计",
  "流程图", "状态图", "活动图", "用例图", "状态机图", "模块图", "交互图",
  "sequence diagram", "class diagram", "component diagram", "deployment diagram",
  "activity diagram", "state diagram", "use case diagram", "package diagram"
skill_id: "<SKILL:.specify/skills/draw-plantuml/SKILL.md>"
---

# Architecture Diagram Skill

Draw system architecture diagrams using PlantUML syntax and standard UML semantics, render diagrams to SVG/PNG via the PlantUML server, and output as a complete HTML document with rendered diagram images and descriptive text.

## Core Principles

### 1. UML Semantics, Not Free-Form Boxes
Every diagram must follow standard UML diagram types. Avoid ad-hoc "boxes and arrows" — use proper UML elements (components, nodes, lifelines, classes) with correct relationships (dependency, association, realization, etc.).

### 2. Architecture-First Narrative
The markdown text should tell a story: start with system context, then drill into components and their interactions. Diagrams and text complement each other — text explains *why*, diagrams show *what*.

### 3. PlantUML Best Practices
For PlantUML-specific conventions (syntax, styling, element types, relationship notation), see [plantuml-guide.md](references/plantuml-guide.md). Key principles: use `skinparam` for consistent styling, keep diagrams ≤15 elements, use meaningful labels.

## Workflow

This skill is designed to draw UML diagrams based on existing information (user descriptions, code, documents) and add corresponding text explanations. Follow the steps below in order.

### Step 1: Choose Diagram Type

**MUST** first read [01-choose-diagram-type.md](references/howto/01-choose-diagram-type.md) to determine the appropriate UML diagram type(s).

Based on the user's description, identify what they want to express and match it to the right diagram:

- Use the **快速匹配表** (Quick Match Table) to map user keywords → diagram type
- Use the **按开发阶段推荐** (By Development Phase) table if the user mentions a specific phase
- Use the **选择决策流程** (Decision Flow) to narrow down structure vs behavior diagrams

If multiple aspects need to be expressed, select multiple diagram types — each diagram focuses on one perspective.

### Step 2: Follow the How-To Guide

Once the diagram type is determined, **MUST** read and follow the corresponding how-to guide for detailed drawing instructions:

| Diagram Type | How-To Guide |
|-------------|-------------|
| 类图 (Class Diagram) | [02-class-diagram.md](references/howto/02-class-diagram.md) |
| 包图 (Package Diagram) | [06-package-diagram.md](references/howto/06-package-diagram.md) |
| 组件图 (Component Diagram) | [03-component-diagram.md](references/howto/03-component-diagram.md) |
| 部署图 (Deployment Diagram) | [04-deployment-diagram.md](references/howto/04-deployment-diagram.md) |
| 时序图 (Sequence Diagram) | [05-sequence-diagram.md](references/howto/05-sequence-diagram.md) |
| 用例图 (Use Case Diagram) | [07-usecase-diagram.md](references/howto/07-usecase-diagram.md) |
| 活动图 (Activity Diagram) | [08-activity-diagram.md](references/howto/08-activity-diagram.md) |
| 状态机图 (State Machine Diagram) | [09-state-machine-diagram.md](references/howto/09-state-machine-diagram.md) |

Each how-to guide provides:
- **Key elements**: UML elements and their PlantUML syntax
- **Complete examples**: Runnable PlantUML code blocks
- **Modeling steps**: Step-by-step instructions for constructing the diagram
- **Best practices**: Common patterns and pitfalls

For additional PlantUML syntax details, also reference [plantuml-guide.md](references/plantuml-guide.md).

### Step 3: Draft PlantUML Code

Based on the how-to guide and the user's system information:

1. Identify the key elements (participants/nodes/components/classes/etc.) from the user's description
2. Define the relationships between them (dependencies, messages, transitions, etc.)
3. Write PlantUML code with `@startuml` / `@enduml` wrapping
4. Keep each diagram focused: ≤15 elements; split into multiple diagrams if larger

For PlantUML syntax details (element types, relationship notation, styling, patterns), reference [plantuml-guide.md](references/plantuml-guide.md). The guide includes a **Quick Syntax Reference by Diagram Type** table covering all 7 diagram types.

### Step 4: Apply Standard Style

After drafting PlantUML code, **MUST** apply the standard style configuration defined in [plantuml-style.md](references/plantuml-style.md). For each diagram:

1. Insert the **base style block** immediately after `@startuml` (before any diagram content):
   ```plantuml
   top to bottom direction
   skinparam monochrome true
   skinparam shadowing false
   skinparam roundCorner 20
   skinparam dpi 300
   scale 2
   skinparam defaultFontSize 14
   skinparam defaultFontName "Arial, Helvetica, sans-serif"
   skinparam padding 8
   skinparam ArrowThickness 2
   skinparam BorderThickness 2
   skinparam svgDimensionStyle false
   skinparam svgLinkTarget _blank
   ```
2. If the diagram contains `actor` elements or is a Use Case Diagram, additionally add:
   ```plantuml
   skinparam actorStyle awesome
   ```
3. Verify placement: all style declarations must appear **after** `@startuml` and **before** any element definitions
4. Verify no conflicts: ensure no duplicate or overriding `skinparam` declarations exist in the diagram body

This ensures all output diagrams have a consistent, document-friendly visual style (monochrome, no shadow, rounded corners), rendered at 300 DPI with 2x scale for maximum resolution and crispness in both SVG and PNG output.

### Step 5: Write Accompanying Text

For each diagram, prepare the following descriptive content (to be included in the final HTML):
1. **Diagram Title** (will become H2/H3 heading in HTML)
2. **Context**: 1-2 sentences on what this diagram represents and why this type was chosen
3. **PlantUML source**: save the code as `.puml` file for reference and rendering
4. **Explanation**: Key points for each key element and relationship
5. **Design Rationale**: Why this structure/interaction pattern was chosen (if applicable)

### Step 6: Render PlantUML to SVG/PNG

After drafting and styling all PlantUML code, render each diagram into an SVG (preferred) or PNG image file using the PlantUML rendering service. All diagrams must be rendered at the highest possible quality — the style block in Step 4 already ensures `skinparam dpi 300` and `scale 2` are embedded in the PlantUML source, producing high-resolution output for both formats.

**Rendering Service:**
- SVG endpoint: `http://workspace.code-workspace.cloud:39156/plantuml/svg`
- PNG endpoint: `http://workspace.code-workspace.cloud:39156/plantuml/png`

**Method:** HTTP POST with `Content-Type: text/plain`, body is the raw PlantUML text (including `@startuml` / `@enduml`).

**Quality guarantees (built into the PlantUML source via Step 4 style block):**
- `skinparam dpi 300` — PNG rendered at 300 DPI, ensuring high pixel density; SVG rasterized fallback also benefits
- `scale 2` — diagram geometry doubled in size, increasing element spacing and detail precision
- `skinparam defaultFontSize 14` — text remains legible at 2x scale
- `skinparam ArrowThickness 2` / `BorderThickness 2` — lines stay visually clear after scaling
- `skinparam svgDimensionStyle false` — SVG uses `viewBox` (no fixed width/height), enabling lossless CSS scaling

**Procedure for each diagram:**
1. Save the PlantUML source text to a temporary `.puml` file (e.g., `diagram-01.puml`)
2. Use `curl` to POST the file content and save the response:
   ```bash
   # SVG (preferred — vector, infinitely scalable, no quality loss on zoom)
   curl -s -X POST -H "Content-Type: text/plain" --data-binary @diagram-01.puml \
     "http://workspace.code-workspace.cloud:39156/plantuml/svg" -o diagram-01.svg
   ```
   ```bash
   # PNG (high-res 300 DPI via skinparam dpi 300 + scale 2)
   curl -s -X POST -H "Content-Type: text/plain" --data-binary @diagram-01.puml \
     "http://workspace.code-workspace.cloud:39156/plantuml/png" -o diagram-01.png
   ```
3. Verify the output is a valid SVG/PNG (`file diagram-01.svg` should show SVG/XML content; `file diagram-01.png` should show PNG with large dimensions)
4. Name files descriptively: `{nn}-{short-title}.svg` or `{nn}-{short-title}.png` (e.g., `01-system-overview.svg`)
5. **For PNG output**: verify image dimensions with `identify diagram-01.png` or `file diagram-01.png` — expect dimensions significantly larger than default (typically 2000px+ width) due to `scale 2` and 300 DPI

**Prefer SVG** for scalability and crisp rendering at any zoom level; use PNG when the user explicitly requests it or when the target platform does not support SVG. Both formats are rendered at maximum quality by the style configuration.

### Step 7: Assemble Final HTML Document

Combine all rendered diagrams and text into a **single HTML document** that displays the architecture with embedded SVG/PNG images (not raw PlantUML code).

**HTML Structure:**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>[System Name] Architecture</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 960px; margin: 0 auto; padding: 2rem; line-height: 1.6; color: #333; }
    h1 { border-bottom: 2px solid #eee; padding-bottom: 0.5rem; }
    h2 { margin-top: 2rem; color: #2c3e50; }
    h3 { color: #34495e; }
    .diagram { text-align: center; margin: 1.5rem 0; }
    .diagram img { max-width: 100%; height: auto; border: 1px solid #eee; border-radius: 4px; }
    .explanation { background: #f8f9fa; padding: 1rem; border-radius: 4px; margin: 1rem 0; }
  </style>
</head>
<body>
  <h1>[System Name] Architecture</h1>
  <section>
    <h2>Overview</h2>
    <p>[High-level system description]</p>
  </section>
  <section>
    <h2>Architecture Diagrams</h2>
    <h3>[Diagram 1 Title]</h3>
    <p>[Context]</p>
    <div class="diagram">
      <img src="01-diagram-name.svg" alt="[Diagram 1 Title]" />
    </div>
    <div class="explanation">
      [Explanation + Rationale]
    </div>
    <h3>[Diagram 2 Title]</h3>
    ...
  </section>
  <section>
    <h2>Summary</h2>
    <p>[Key architectural decisions and trade-offs]</p>
  </section>
</body>
</html>
```

**Key Rules:**
- Reference SVG/PNG files using **relative paths** (diagrams and HTML in the same output directory)
- Alternatively, if only one diagram exists, embed the SVG content inline in the HTML using `<svg>...</svg>` directly
- Ensure all images have meaningful `alt` attributes
- HTML should be self-contained and viewable by opening the `.html` file directly in a browser

## Output Requirements

- Output as a **single HTML document** (`.html` file) with rendered SVG/PNG diagrams
- Diagrams MUST be rendered via the PlantUML server (`http://workspace.code-workspace.cloud:39156/plantuml/svg`) — do NOT embed raw PlantUML text in the final output
- SVG/PNG image files saved alongside the HTML in the same output directory
- HTML references images via relative paths (e.g., `<img src="01-overview.svg" />`)
- For single-diagram outputs, inline SVG embedding is acceptable as an alternative
- PlantUML source files (`.puml`) should also be saved for future editing/regeneration
- Text descriptions in HTML semantic elements (headings, paragraphs, lists)
- Default language: follow user's preferred language (Chinese by default for this project)
- Each diagram must have at minimum: a title, a rendered image, and a brief explanation

## Reference Documents

### How-To Guides (`references/howto/`)

Step-by-step guides organized by diagram type and PlantUML syntax. Start here for hands-on drawing:

| # | Document | Content |
|---|----------|---------|
| 1 | [01-choose-diagram-type.md](references/howto/01-choose-diagram-type.md) | How to select the right UML diagram type based on user description, development phase, and system type |
| 2 | [02-class-diagram.md](references/howto/02-class-diagram.md) | How to draw Class Diagrams — class definition, 6 relationship types with PlantUML syntax, packages, GRASP design principles |
| 3 | [03-component-diagram.md](references/howto/03-component-diagram.md) | How to draw Component Diagrams — layered architecture, microservice patterns, interface and dependency modeling |
| 4 | [04-deployment-diagram.md](references/howto/04-deployment-diagram.md) | How to draw Deployment Diagrams — physical topology, Kubernetes, cloud services, node-to-node communication |
| 5 | [05-sequence-diagram.md](references/howto/05-sequence-diagram.md) | How to draw Sequence Diagrams — message types, combined fragments (alt/loop/par), activation bars, interaction flow |
| 6 | [06-package-diagram.md](references/howto/06-package-diagram.md) | How to draw Package Diagrams — module organization, namespace hierarchy, layered architecture, dependency management |
| 7 | [07-usecase-diagram.md](references/howto/07-usecase-diagram.md) | How to draw Use Case Diagrams — actors, use cases, system boundary, include/extend/generalization, use case description template |
| 8 | [08-activity-diagram.md](references/howto/08-activity-diagram.md) | How to draw Activity Diagrams — business process modeling, swimlanes, fork/join for concurrency, decision nodes, control flow |
| 9 | [09-state-machine-diagram.md](references/howto/09-state-machine-diagram.md) | How to draw State Machine Diagrams — object lifecycle, state transitions, events/guards/actions, composite states, implementation patterns |

### Syntax Reference (`references/`)

| Document | Content |
|----------|---------|  
| [plantuml-guide.md](references/plantuml-guide.md) | Complete PlantUML syntax reference for architecture diagrams: all supported diagram types, element types, relationship syntax, skinparam customization, and common patterns |
| [plantuml-official-docs.md](references/plantuml-official-docs.md) | PlantUML official documentation and advanced features. Load on-demand for syntax edge cases or less common diagram types |

### Source Documents (`references/document/`)

Original reference materials on UML theory, PlantUML tools, modeling methodology, GRASP patterns, and best practices. Load on-demand for deeper understanding of design principles and methodology.

## Quality Checklist

Before delivering the final document, verify:
- [ ] All PlantUML source files (`.puml`) have matching `@startuml` / `@enduml`
- [ ] Each diagram has been successfully rendered to SVG/PNG via the PlantUML server
- [ ] SVG/PNG files are valid (verified with `file` command)
- [ ] PNG files have high dimensions (2000px+ width), confirming `dpi 300` and `scale 2` took effect
- [ ] SVG files use `viewBox` without fixed width/height (confirm `svgDimensionStyle false` is active)
- [ ] HTML references all diagram images with correct relative paths
- [ ] Each diagram uses the correct UML type for its purpose
- [ ] No diagram exceeds 15 elements (split if larger)
- [ ] Text explanations reference specific elements in the diagram
- [ ] `skinparam` provides consistent visual style across all diagrams
- [ ] High-quality rendering params (`dpi 300`, `scale 2`, `ArrowThickness 2`, `BorderThickness 2`) present in all diagrams
- [ ] Aliases and labels are human-readable (not code identifiers)
- [ ] Document has a clear narrative flow from overview to details
- [ ] Relationship labels are present and describe the interaction (e.g., "uses via HTTP", not just "uses")
- [ ] No orphan elements (every element has at least one relationship)
- [ ] HTML file opens correctly in a browser and displays all diagrams
