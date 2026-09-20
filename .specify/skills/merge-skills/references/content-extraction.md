# Content Extraction — turning source form into neutral material

Phase 2 of the merge. Goal: get the source skill's **content** out of its **form** into a
neutral, readable intermediate you can freely reorganize — without hand-transcribing
(program-first: deterministic conversion belongs to a tool, not the LLM).

The intermediate is **scratch**: land it under `${SKILL_WORKDIR}/tmp/merge-<source>/`,
never inside the target's committed tree. It is deleted in Phase 8.

## By source form

| Source form | Extraction approach |
|-------------|---------------------|
| Markdown prose / reference docs | Already neutral — read directly, no conversion. Note headings so Phase 3 can remap them. |
| HTML documentation (doc site, `open-api/*.html`, `index.html`) | Convert to Markdown with a deterministic tool (below). Strip nav/breadcrumb/TOC chrome before converting. |
| Scripts (`scripts/*.py|*.sh`) | Do **not** re-express as prose — code is already the right form. Inventory each script's purpose; most move into the target's `scripts/` largely intact (Phase 4). |
| Assets (images, CSS, templates) | Inventory only. Most are *form* carriers of the source doc site and are **discarded**, not merged — keep an asset only if the target genuinely references it. |
| Frontmatter / registry metadata | Extract the **capability + trigger keywords** (they fold into the target's `description`); discard the source's `skill_id`, `name`, version. |

## HTML → Markdown converter (example)

A minimal, dependency-light converter (BeautifulSoup + markdownify). Adjust the chrome
selectors to the source's actual structure:

```python
#!/usr/bin/env python3
"""Convert a source skill's HTML docs to Markdown scratch material (Phase 2)."""
import os, re, sys
from bs4 import BeautifulSoup
from markdownify import markdownify

SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(DST, exist_ok=True)
for name in sorted(os.listdir(SRC)):
    if not name.endswith(".html"):
        continue
    soup = BeautifulSoup(open(os.path.join(SRC, name), encoding="utf-8").read(), "html.parser")
    main = soup.find("main") or soup
    for sel in ("nav.breadcrumbs", "aside.toc-aside", "nav.toc", "header", "footer"):
        for tag in main.select(sel):
            tag.decompose()
    md = markdownify(str(main), heading_style="ATX", bullets="-")
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    open(os.path.join(DST, name[:-5] + ".md"), "w", encoding="utf-8").write(md + "\n")
    print(f"{name} -> {name[:-5]}.md ({len(md)} chars)")
```

Run it against a scratch dir, then read the `.md` output as your Phase-3/4 material:

```bash
python3 /tmp/html2md.py <source>/open-api /tmp/merge-<source>/  # example
wc -c /tmp/merge-<source>/*.md                                  # size the material
```

Interpreter note: if the host `python3` lacks `bs4`/`markdownify`, use a project venv that
has them (e.g. `.venv/bin/python`) rather than installing globally.

## After extraction

- Record a size measurement (char counts per file) — it drives how many target reference
  docs the content should split into (Phase 3).
- Do a first read to build a mental **content inventory**: capabilities, command families,
  fact tables, enumerated values. This inventory is what the Phase-5 coverage probe will
  later confirm survived.
