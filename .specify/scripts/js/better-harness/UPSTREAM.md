# Upstream Provenance

- **Source repository**: `better-harness` (local checkout `/cws_work/better-harness`)
- **Baseline commit**: `b2e621d` (upstream v0.3.0)
- **Copied**: 2026-07-29
- **License**: MIT (see `LICENSE` in this directory, copied verbatim from upstream)
- **Resync**: manual, per-file, diff-driven (see § Resync Policy)

## Subset Manifest

Collection-facts subset only (evidence layer). Directories/files copied, preserving
upstream relative layout so cross-imports (`../session-analysis/...`) resolve unchanged:

| Path | Purpose |
|------|---------|
| `session-analysis.mjs` | session-lane CLI entry (upstream root-level entry, kept sibling to `session-analysis/`) |
| `session-analysis/` | session discovery, Task Episodes, redaction funnel (`privacy-safe-text.mjs`, `semantic-facets.mjs`), platform adapters (`platforms/{qoder,codex,claude,cursor}.mjs` from upstream + `platforms/opencode.mjs` spec-kit-owned, P7-b) |
| `core-change-watch/` | project profile, git history signals, core paths, diff impact (8 self-executable scripts) |
| `agent-customize/` | configured-asset inventory providers (`providers/{qoder,codex,claude,cursor,index}.mjs`) |
| `coding-agent-practices/` | `asset-baseline.mjs` + `asset-integrity.mjs` + `inventory.mjs` + `asset-eval/` (three read-only envelopes; **no `checkup/`**) |
| `agent-lint/` | lint dependency of asset-baseline (4 files) — included because `asset-baseline.mjs` imports `../agent-lint/index.mjs` |
| `dependency-governance/cli.mjs` | optional dependency-governance signals |
| `package.json` | minimal (`type: module` + `engines`); **zero npm dependencies** |

`coding-agent-practices/asset-eval/` was added during the copy after import
resolution showed `asset-integrity.mjs` requires it (facts-layer scoring tables,
not verdict rendering).

## Exclusions

Deliberately NOT copied (verdict/presentation layer or out of evidence scope):
`harness-analysis/` (lead analyzers, report-source, renderers, canvas-preview),
`better-harness-cli/` (root facade/registry), `evidence-bundle` facade,
`findings-recommend/` (recommendation catalog), `checkup/` + `checkup.mjs`
(mutators), `packaging/`, `hooks/`, `doc-link-graph/`, `agent-guardrails/`,
`review-trigger/`, upstream docs/templates/references/case-studies/skills,
and the `@vscode/tree-sitter-wasm` / `esbuild-wasm` dependencies (only used by
the excluded canvas subtree). The subset uses `node:` built-ins exclusively.

## Local Modifications

| Date | File | Motivation | Upstreamable |
|------|------|-----------|--------------|
| 2026-07-29 | `agent-lint/index.mjs` | Removed `import ... "../findings-recommend.mjs"` and made `withAgentsMdRecommendation()` an identity function — findings-recommend is verdict-layer, excluded per contracts C-B2; findings pass through without recommendation enrichment | No (subset-boundary specific) |
| 2026-07-29 | `agent-lint/index.mjs` | `resolveReference` normalizes the spec-kit `${SKILL_HOME}/` path variable to owner-relative `./` before resolution — eliminates 4 false-positive "missing local reference" findings on skills using the documented `${SKILL_HOME}` convention | Yes (generic path-variable hook could be upstreamed) |
| 2026-07-29 | `session-analysis/platforms/claude.mjs` | `workspaceToClaudeSlugVariants` adds the observed Claude Code slug rule (every non-alphanumeric char → `-`; verified against a real store: `/cws_work` → `-cws-work`); previous variants kept for compatibility | Yes (fixes real-store discovery) |
| 2026-07-29 | `session-analysis/platforms/opencode.mjs` (new file) | spec-kit owned opencode session adapter (provider-runner pattern, P7-b): project/storage JSON layout (info/message/part), workspace filtering by session `directory`, tool lifecycle events, inherited-timestamp gap declared via `opencode-partial-event-timestamps` warning | Yes (new platform, upstream-compatible shape) |
| 2026-07-29 | `session-analysis.mjs` + `session-analysis/analyzer.mjs` | `loadPlatform` registers the `opencode` branch (explicit dispatch, per upstream pattern) | Yes (accompanies the opencode adapter) |
| 2026-07-30 | `session-analysis/platforms/qoder.mjs` | P7-c adoption from export-session: (1) `discoverProjectSessions` scans all `projects/` subdirs and decides ownership by the **embedded cwd field** (jsonl first-lines / sibling `state.json`), slug variants as fallback only — real-store verified: eligible sessions 0→4 for a workspace whose slug rule had silently mismatched; (2) `resolveIdeSessionModel` reads IDE `state.vscdb` (`chat.modelConfig.session.<sid>`) overlaying real model over `kmodel_*` tier aliases; (3) `inferRequestId` strips `chatcmpl-` from `message.id` (bailian request id); (4) `currentSessionId` added (`QODER_SESSION_ID`) | Yes |
| 2026-07-30 | `session-analysis/platforms/codex.mjs` + `claude.mjs` | P7-c: `currentSessionId` env factors added (`CODEX_THREAD_ID`/`CODEX_SESSION_ID`; `CLAUDE_CODE_SESSION_ID`) | Yes |
| 2026-07-30 | `session-analysis/platforms/cursor.mjs` | P7-c: transcript discovery probes embedded `cwd` (200-line window), skipping sessions of other workspaces; cwd-less transcripts stay included (no inference) | Yes |
| 2026-07-30 | `session-analysis/platforms/opencode.mjs` | P7-c: parallel SQLite source (`opencode.db`, lazy `node:sqlite`): workspace filtering by `directory`, `parent_id` subsessions, messages/parts through the same normalizeEvent pipeline, merged with JSON layout by sessionId | Yes |
| 2026-07-29 | `tests/js/*.test.mjs` (spec-kit side, not in this dir) | Import/spawn paths rewritten `../scripts/...` → `../../scripts/js/better-harness/...`; facade invocations (`better-harness.mjs <group> <cmd>`) rewritten to direct capability-CLI invocations; two verdict-layer tests (agents-md-review recommendation fields, findings-recommend catalog) removed; `session-analysis-opencode.test.mjs` added (5 fixture tests) | No (layout specific) |

## Resync Policy

Manual, per-file, diff-driven. No automatic merging. Suggested cadence: quarterly —
diff the subset against upstream HEAD, cherry-pick fixes per file, and append a row
to Local Modifications for every change kept. New files may only be added if they are
NOT in the Exclusions list; update the Subset Manifest in the same change.
