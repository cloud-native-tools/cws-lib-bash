# Editing Existing DOCX Documents

## Common Operations

### Converting .doc to .docx

Legacy `.doc` files must be converted before editing:

```bash
python ${SKILL_HOME}/scripts/office/soffice.py --headless --convert-to docx document.doc
```

### Reading Content

```bash
# Text extraction with tracked changes
pandoc --track-changes=all document.docx -o output.md

# Raw XML access
python ${SKILL_HOME}/scripts/office/unpack.py document.docx unpacked/
```

### Converting to Images

```bash
python ${SKILL_HOME}/scripts/office/soffice.py --headless --convert-to pdf document.docx
pdftoppm -jpeg -r 150 document.pdf page
```

### Accepting Tracked Changes

To produce a clean document with all tracked changes accepted (requires LibreOffice):

```bash
python ${SKILL_HOME}/scripts/docx/accept_changes.py input.docx output.docx
```

## Editing Workflow

**Follow all 3 steps in order.**

### Step 1: Unpack

```bash
python ${SKILL_HOME}/scripts/office/unpack.py document.docx unpacked/
```

Extracts XML, pretty-prints, merges adjacent runs, and converts smart quotes to XML entities (`&#x201C;` etc.) so they survive editing. Use `--merge-runs false` to skip run merging.

### Step 2: Edit XML

Edit files in `unpacked/word/`. See [docx-xml-reference.md](./docx-xml-reference.md) for patterns.

**Use "Claude" as the author** for tracked changes and comments, unless the user explicitly requests use of a different name.

**Use the Edit tool directly for string replacement. Do not write Python scripts.** Scripts introduce unnecessary complexity. The Edit tool shows exactly what is being replaced.

**CRITICAL: Use smart quotes for new content.** When adding text with apostrophes or quotes, use XML entities to produce smart quotes:

```xml
<!-- Use these entities for professional typography -->
<w:t>Here&#x2019;s a quote: &#x201C;Hello&#x201D;</w:t>
```

| Entity | Character |
|--------|-----------|
| `&#x2018;` | ' (left single) |
| `&#x2019;` | ' (right single / apostrophe) |
| `&#x201C;` | " (left double) |
| `&#x201D;` | " (right double) |

**Adding comments:** Use `comment.py` to handle boilerplate across multiple XML files (text must be pre-escaped XML):

```bash
python ${SKILL_HOME}/scripts/docx/comment.py unpacked/ 0 "Comment text with &amp; and &#x2019;"
python ${SKILL_HOME}/scripts/docx/comment.py unpacked/ 1 "Reply text" --parent 0  # reply to comment 0
python ${SKILL_HOME}/scripts/docx/comment.py unpacked/ 0 "Text" --author "Custom Author"  # custom author name
```

Then add markers to document.xml (see Comments in [docx-xml-reference.md](./docx-xml-reference.md)).

### Step 3: Pack

```bash
python ${SKILL_HOME}/scripts/office/pack.py unpacked/ output.docx --original document.docx
```

Validates with auto-repair, condenses XML, and creates DOCX. Use `--validate false` to skip.

**Auto-repair will fix:**
- `durableId` >= 0x7FFFFFFF (regenerates valid ID)
- Missing `xml:space="preserve"` on `<w:t>` with whitespace

**Auto-repair won't fix:**
- Malformed XML, invalid element nesting, missing relationships, schema violations

## Common Pitfalls

- **Replace entire `<w:r>` elements**: When adding tracked changes, replace the whole `<w:r>...</w:r>` block with `<w:del>...<w:ins>...` as siblings. Don't inject tracked change tags inside a run.
- **Preserve `<w:rPr>` formatting**: Copy the original run's `<w:rPr>` block into your tracked change runs to maintain bold, font size, etc.
