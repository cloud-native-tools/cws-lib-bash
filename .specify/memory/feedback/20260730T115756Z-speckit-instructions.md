---
id: "20260730T115756Z-speckit-instructions"
unit_id: "/speckit.instructions"
unit_type: "command"
run_id: "docs-map-refresh-20260730-195640"
scope: "local"
partial: false
created: "2026-07-30T11:57:56Z"
summary: "Directed refresh after /speckit.docs bootstrap: Documentation Map gained Glossary/Architecture/Docs-Space rows and updated Development/Readme key-content; Tech Stack fixed stale scripts count (55->59)"
---

## Review
Directed refresh after /speckit.docs bootstrap: Documentation Map gained Glossary/Architecture/Docs-Space rows and updated Development/Readme key-content; Tech Stack fixed stale scripts count (55->59), removed vanished expect/ dir, added docs/. All other sections within tolerance; registries and symlinks intact; no user-authored loss found in backup history; glossary seeded with 3 auto proposals.

## Optimization Points
- The Tech Stack "Key Directories" list silently drifted (55->59 scripts, vanished expect/ dir); adding a scripted directory/count probe to the command doc (like the Documentation Map existence loop) would catch these deterministically.
