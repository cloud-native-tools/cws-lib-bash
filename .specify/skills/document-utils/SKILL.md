---
name: document-utils
description: |
  Create, read, edit, and manipulate office documents including Word (.docx), PDF, PowerPoint (.pptx),
  and Excel (.xlsx) files. Also apply professional visual themes to any document type.
  Use when the user mentions "Word", "docx", "PDF", "PowerPoint", "pptx", "Excel", "xlsx",
  "spreadsheet", "presentation", "slides", "deck", "report", "memo", "letter", "template",
  "theme", "文档", "Word文档", "PDF文件", "表格", "电子表格", "幻灯片", "演示文稿",
  "主题", "财务模型", "报告", or any request to produce, read, edit, or analyze
  office document files.
skill_id: "<SKILL:.specify/skills/document-utils/SKILL.md>"
license: Proprietary. LICENSE.txt has complete terms
---

# Document Utilities

## Overview

This skill creates, reads, edits, and manipulates office documents across four formats:

- **DOCX** (Word) — create with `docx-js`, edit via XML unpack/edit/repack, extract content, handle tracked changes and comments
- **PDF** — read/extract text and tables, create, merge/split, rotate, watermark, OCR, fill forms, password protect
- **PPTX** (PowerPoint) — create from scratch with PptxGenJS, edit existing presentations via XML workflow, design guidance, visual QA
- **XLSX** (Excel) — create and edit spreadsheets with formulas, formatting, and financial-model standards; recalculate and verify
- **Themes** — apply professional visual themes (10 presets + custom) to any document type

## Quick Reference

| Task | Format | Approach |
|------|--------|----------|
| Read/analyze content | DOCX | `pandoc` or unpack for raw XML — see [docx-editing.md](./references/docx-editing.md) |
| Create new document | DOCX | `docx-js` — see [docx-creation.md](./references/docx-creation.md) |
| Edit existing document | DOCX | Unpack → edit XML → repack — see [docx-editing.md](./references/docx-editing.md) |
| Read/extract text | PDF | `pypdf`, `pdfplumber`, or `pdftotext` — see [pdf-operations.md](./references/pdf-operations.md) |
| Extract tables | PDF | `pdfplumber` — see [pdf-operations.md](./references/pdf-operations.md) |
| Create new PDF | PDF | `reportlab` (Python) or `pdf-lib` (JS) — see [pdf-operations.md](./references/pdf-operations.md) |
| Merge/split PDFs | PDF | `pypdf` or `qpdf` — see [pdf-operations.md](./references/pdf-operations.md) |
| Fill PDF forms | PDF | See [pdf-forms.md](./references/pdf-forms.md) |
| Read/analyze slides | PPTX | `python -m markitdown` — see [pptx-editing.md](./references/pptx-editing.md) |
| Edit existing presentation | PPTX | See [pptx-editing.md](./references/pptx-editing.md) |
| Create from scratch | PPTX | See [pptx-creation.md](./references/pptx-creation.md) |
| Read/analyze spreadsheet | XLSX | `pandas` — see [xlsx-creation.md](./references/xlsx-creation.md) |
| Create/edit spreadsheet | XLSX | `openpyxl` with formulas — see [xlsx-creation.md](./references/xlsx-creation.md) |
| Apply visual theme | Any | See [themes-guide.md](./references/themes-guide.md) |

## DOCX

### Overview

A `.docx` file is a ZIP archive containing XML files.

### Creating New Documents

Generate `.docx` files with `docx-js`, validate the output, and follow the critical layout and style rules in [docx-creation.md](./references/docx-creation.md).

### Editing Existing Documents

Unpack the document, edit XML directly with the Edit tool, then repack. Full workflow, smart-quote rules, and pitfalls are in [docx-editing.md](./references/docx-editing.md).

### XML Reference

Tracked changes, comments, images, and schema patterns are in [docx-xml-reference.md](./references/docx-xml-reference.md).

## PDF

### Overview

For essential Python-library and command-line operations, see [pdf-operations.md](./references/pdf-operations.md). For advanced libraries (`pypdfium2`, `pdf-lib`, `pdfjs-dist`) and complex workflows, see [pdf-reference.md](./references/pdf-reference.md). For filling PDF forms, see [pdf-forms.md](./references/pdf-forms.md).

## PPTX

### Reading Content

Use `python -m markitdown presentation.pptx` for text extraction and `${SKILL_HOME}/scripts/pptx/thumbnail.py` for a visual overview.

### Editing Workflow

For template-based editing, see [pptx-editing.md](./references/pptx-editing.md).

### Creating from Scratch

For PptxGenJS setup, shapes, charts, tables, and common pitfalls, see [pptx-creation.md](./references/pptx-creation.md).

### Design Ideas

Color palettes, typography, layout options, and common mistakes are in [pptx-design.md](./references/pptx-design.md).

### QA

Content checks, visual QA with subagents, and the verify-fix-reverify loop are in [pptx-qa.md](./references/pptx-qa.md).

## XLSX

### Requirements for Outputs

Financial-model color coding, number formatting, and formula-construction rules are in [xlsx-financial-models.md](./references/xlsx-financial-models.md).

### Creation, Editing, and Analysis

Library selection, pandas/openpyxl workflows, formula usage, recalculation with `recalc.py`, and verification are in [xlsx-creation.md](./references/xlsx-creation.md).

## Themes

Apply a chosen theme's colors and fonts consistently across any artifact. Usage steps, the list of 10 preset themes, and custom-theme creation are in [themes-guide.md](./references/themes-guide.md).

## Hard Constraints

These rules are non-negotiable. Violating them produces corrupt or wrong output.

1. **DOCX page size**: Always set explicitly; `docx-js` defaults to A4. Use 12240×15840 DXA for US Letter.
2. **DOCX table widths**: Always use `WidthType.DXA`; set both `columnWidths` and per-cell `width`; never use `WidthType.PERCENTAGE`.
3. **DOCX tracked changes**: Author is "Claude" unless the user says otherwise; use XML entities for smart quotes.
4. **Excel formulas**: Never hardcode calculated values; always write Excel formulas and run `${SKILL_HOME}/scripts/xlsx/recalc.py`.
5. **PptxGenJS colors**: Never use `#` prefix or 8-character hex colors; never reuse option objects across calls.
6. **PPTX bullets**: Use `bullet: true`; never unicode bullet characters.
7. **Themes**: Show `${SKILL_HOME}/themes/theme-showcase.pdf`, ask for choice, and wait for explicit confirmation before applying.

## Path Conventions

This Skill follows the canonical path conventions:

- Use `${SKILL_HOME}/<relative-path>` for every Skill-owned resource reference.
- Use `${SKILL_WORKDIR}/<relative-path>` for every runtime/user-facing path.
- Never embed agent-specific install paths.

## Resources

### Scripts

| Directory | Contents |
|-----------|----------|
| `${SKILL_HOME}/scripts/office/` | Shared Office tools: `soffice.py`, `pack.py`, `unpack.py`, `validate.py`, `helpers/`, `validators/`, `schemas/` |
| `${SKILL_HOME}/scripts/docx/` | DOCX-specific: `accept_changes.py`, `comment.py`, `templates/` |
| `${SKILL_HOME}/scripts/pdf/` | PDF-specific: `check_bounding_boxes.py`, `check_fillable_fields.py`, `convert_pdf_to_images.py`, `create_validation_image.py`, `extract_form_field_info.py`, `extract_form_structure.py`, `fill_fillable_fields.py`, `fill_pdf_form_with_annotations.py` |
| `${SKILL_HOME}/scripts/pptx/` | PPTX-specific: `add_slide.py`, `clean.py`, `thumbnail.py` |
| `${SKILL_HOME}/scripts/xlsx/` | XLSX-specific: `recalc.py` |

### References

| File | Description |
|------|-------------|
| `${SKILL_HOME}/references/docx-creation.md` | Creating new DOCX documents with `docx-js` |
| `${SKILL_HOME}/references/docx-editing.md` | Editing existing DOCX documents via XML |
| `${SKILL_HOME}/references/docx-xml-reference.md` | DOCX XML patterns for tracked changes, comments, and images |
| `${SKILL_HOME}/references/pdf-operations.md` | Essential PDF operations with Python and CLI tools |
| `${SKILL_HOME}/references/pdf-forms.md` | PDF form filling instructions (fillable and non-fillable) |
| `${SKILL_HOME}/references/pdf-reference.md` | Advanced PDF processing (`pypdfium2`, `pdf-lib`, `pdfjs-dist`, advanced CLI) |
| `${SKILL_HOME}/references/pptx-creation.md` | PptxGenJS tutorial (creating presentations from scratch) |
| `${SKILL_HOME}/references/pptx-editing.md` | PPTX editing workflow (template-based, XML manipulation) |
| `${SKILL_HOME}/references/pptx-design.md` | Design guidance for PPTX slides |
| `${SKILL_HOME}/references/pptx-qa.md` | PPTX quality-assurance workflow |
| `${SKILL_HOME}/references/xlsx-creation.md` | Creating and editing XLSX files with formulas |
| `${SKILL_HOME}/references/xlsx-financial-models.md` | Financial-model formatting and formula standards |
| `${SKILL_HOME}/references/themes-guide.md` | Applying and creating document themes |

### Themes

| Directory | Contents |
|-----------|----------|
| `${SKILL_HOME}/themes/` | 10 theme definition files (`.md`) and `theme-showcase.pdf` |

## Dependencies

### DOCX
- **pandoc**: Text extraction
- **docx**: `npm install -g docx` (new documents)
- **LibreOffice**: PDF conversion, accepting tracked changes (auto-configured via `${SKILL_HOME}/scripts/office/soffice.py`)
- **Poppler**: `pdftoppm` for images

### PDF
- **pypdf**: Basic PDF operations (merge, split, rotate, encrypt)
- **pdfplumber**: Text and table extraction
- **reportlab**: PDF creation (Python)
- **pdf-lib**: PDF creation and manipulation (JavaScript) -- `npm install pdf-lib`
- **pypdfium2**: Fast rendering and image generation
- **poppler-utils**: `pdftotext`, `pdftoppm`, `pdfimages` command-line tools
- **qpdf**: Command-line PDF manipulation, optimization, encryption
- **pdftk**: Alternative command-line PDF toolkit (if available)
- **pytesseract** + **pdf2image**: OCR for scanned PDFs
- **ImageMagick**: Image cropping for form field analysis

### PPTX
- **markitdown**: `pip install "markitdown[pptx]"` -- text extraction
- **Pillow**: `pip install Pillow` -- thumbnail grids
- **pptxgenjs**: `npm install -g pptxgenjs` -- creating from scratch
- **react-icons** + **react** + **react-dom** + **sharp**: `npm install -g react-icons react react-dom sharp` -- SVG icons for slides
- **LibreOffice** (`soffice`): PDF conversion (auto-configured via `${SKILL_HOME}/scripts/office/soffice.py`)
- **Poppler** (`pdftoppm`): PDF to images

### XLSX
- **pandas**: Data analysis and basic Excel I/O
- **openpyxl**: Excel file creation, editing, formatting, and formulas
- **LibreOffice**: Formula recalculation (auto-configured via `${SKILL_HOME}/scripts/office/soffice.py`)

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:document-utils" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
