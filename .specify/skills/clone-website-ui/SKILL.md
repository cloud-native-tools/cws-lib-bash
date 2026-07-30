---
name: clone-website-ui
description: Reverse-engineer and replicate a website's front-end UI by inspecting the live page in a browser — extracts exact design tokens, computed CSS, assets, content, and interaction models section-by-section, writes auditable component specs, and dispatches parallel builder agents to reconstruct each section in any frontend stack. Use when the user wants to clone, replicate, rebuild, reverse-engineer, or copy a website's front-end/UI, or mentions "clone this site", "copy this page design", "rebuild this page", "pixel-perfect clone", "复刻页面", "克隆网站", "复制前端页面", "还原页面设计", "仿站".
argument-hint: "<url1> [<url2> ...]"
user-invocable: true
skill_id: "<SKILL:.specify/skills/clone-website-ui/SKILL.md>"
---

# clone-website-ui

Reverse-engineer a live web page and rebuild its front-end UI as a **pixel-perfect, framework-agnostic** clone. You are a **foreman walking the job site**: as you inspect each section you write a detailed spec file, then hand it to a specialist builder agent with everything they need. Extraction and construction happen in parallel; extraction is meticulous and produces auditable artifacts.

This is **not** a two-phase "inspect then build" process — the extract → spec → dispatch loop runs section by section.

## Scope Defaults

Clone exactly what's visible at the target URL. Unless the user says otherwise:

- **Fidelity:** Pixel-perfect — exact colors, spacing, typography, animations
- **In scope:** Visual layout & styling, component structure & interactions, responsive design, mock data for demos
- **Out of scope:** Real backend/database, authentication, real-time features, SEO, accessibility audit
- **Customization:** None — pure emulation (customize only after the base clone is verified)

Honor any explicit user instructions (fidelity level, customizations, extra context) over these defaults.

## Ethics Gate (check before proceeding)

This skill is for legitimate use only: platform migration, recovering lost source of a site you own, or learning. Do **not** proceed for phishing/impersonation, passing off others' brand/logos/copy as original, or where the target's terms of service prohibit reproduction. If the request looks deceptive or infringing, stop and ask the user to confirm a legitimate purpose.

## Phase 0: Setup

1. **Browser automation.** This skill cannot work without it. Use the **`browser-utils` skill** to select and drive the right browser strategy (Tier 1 built-in / Tier 2 MCP / Tier 3 Playwright) for the current agent. All "inspect / scroll / click / screenshot / run JS in page" steps below route through browser-utils.
2. **Target stack.** Determine where the clone will be built:
   - If run inside an existing frontend project, **detect** the stack (framework, styling approach, component conventions) and match it.
   - Otherwise ask the user which stack to target (e.g. React, Vue, Svelte, SvelteKit, Astro, plain HTML/CSS). Default to **React + TypeScript + a utility-CSS or CSS-modules approach** if they have no preference.
   - Record the chosen stack, its file/naming conventions, and how components are styled — every builder prompt must speak this stack's idiom.
3. **Parse `$ARGUMENTS`** as one or more URLs. Normalize and validate each; ask the user to fix any invalid ones. Verify each is reachable in the browser. When multiple URLs are given, process them independently, keeping artifacts isolated per host (`docs/research/<hostname>/`).
4. **Verify the base builds** with the project's own build/typecheck command before you start, so you have a known-good baseline.
5. **Create output dirs** if missing: `docs/research/`, `docs/research/components/`, `docs/design-references/`, `scripts/`.

## Guiding Principles

These separate a real clone from a "close enough" mess. Internalize them.

1. **Completeness beats speed.** Every builder must receive *everything*: screenshot, exact CSS values, downloaded assets with local paths, real text, component structure. If a builder has to guess a color/size/padding, extraction failed. Extract one more property rather than ship an incomplete brief.
2. **Small tasks, perfect results.** "Build the entire features section" produces approximations; a single focused component with exact CSS gets nailed. **Complexity budget:** if a builder prompt exceeds ~150 lines of spec, split the section. This is mechanical — don't override it with "but it's all related."
3. **Real content, real assets.** Extract actual text (`element.textContent`), download every `<img>`/`<video>`, extract inline `<svg>` as components. Only generate content that is clearly server-generated and unique per session. **Layered assets matter** — one apparent image is often a background + foreground mockup + overlay icon; enumerate ALL images and background-images in each container, including absolutely-positioned overlays.
4. **Foundation first.** Nothing builds until the foundation exists: global styles with the target's design tokens (colors, fonts, spacing), type definitions for content structures, and global assets (fonts, favicons). Sequential and non-negotiable; everything after can be parallel.
5. **Extract how it looks AND how it behaves.** A page is a living thing. For every element capture its **appearance** (exact `getComputedStyle()`) AND its **behavior** (what changes, what triggers it, how it transitions). Not "looks like 16px" — the computed value. Not "nav changes on scroll" — the exact trigger, before/after states, and transition. See `references/inspection-guide.md` for the full behavior catalog.
6. **Identify the interaction model before building.** The #1 most expensive mistake is building click-based UI when the original is scroll-driven (or vice versa) — it requires a full rewrite, not a CSS tweak. **Scroll first, don't click:** scroll slowly and watch what changes on its own → scroll-driven (extract the mechanism: `IntersectionObserver`, `scroll-snap`, `position: sticky`, `animation-timeline`, JS scroll listeners). Only if nothing changes on scroll, test click/hover. Document the model explicitly in every spec.
7. **Extract every state, not just the default.** Tabs show different cards per tab; a header differs at scroll 0 vs 100; cards have hover states. Click each tab and extract content per state; capture computed styles at scroll 0 and past the trigger, then diff.
8. **Spec files are the source of truth.** Every component gets a spec in `docs/research/components/` BEFORE any builder is dispatched. The builder receives the spec contents inline; the file persists as an auditable artifact. No spec → the builder guesses. Not optional.
9. **Build must always compile.** Every builder verifies the project's typecheck/build passes before finishing. After merging, you verify the full build. A broken build is never acceptable, even temporarily.

## Phase 1: Reconnaissance

Navigate to the target with browser-utils.

**Screenshots** — Full-page captures at desktop (1440px) and mobile (390px). Save to `docs/design-references/` with descriptive names. These are your master reference.

**Global extraction** (before anything else):
- **Fonts** — Inspect `<link>` tags (Google/self-hosted) and computed `font-family` on headings, body, code, labels. Document every family/weight/style actually used, then configure them in the target stack's font-loading mechanism.
- **Colors** — Extract the palette from computed styles across the page. Populate the target's global stylesheet with real colors (light/dark if present). Map to the stack's token/variable system where it fits; add custom properties for the rest.
- **Favicons & meta** — Download favicons, apple-touch-icons, OG images, webmanifest to `public/seo/` (or the stack's static dir). Wire up metadata.
- **Global UI patterns** — Site-wide CSS/JS: scrollbar hiding, page-level scroll-snap, global keyframes, backdrop filters, gradient overlays, and **smooth-scroll libraries** (Lenis, Locomotive Scroll — check for `.lenis`, `.locomotive-scroll`, or custom scroll wrappers). Note libraries that must be installed.

**Mandatory interaction sweep** — a dedicated pass AFTER screenshots to discover behaviors invisible in a static shot. Run the scroll / click / hover / responsive sweeps described in `references/inspection-guide.md` and save findings to `docs/research/BEHAVIORS.md` — your behavior bible for every spec.

**Page topology** — Map every distinct section top to bottom, give each a working name, and record: visual order, fixed/sticky overlays vs. flow content, overall layout (scroll container, columns, z-index layers), dependencies (e.g. a floating nav overlaying everything), and each section's interaction model. Save as `docs/research/PAGE_TOPOLOGY.md` — your assembly blueprint.

## Phase 2: Foundation Build

Sequential; do it yourself (it touches many files):

1. **Fonts** — configure the target's actual fonts in the stack's font mechanism.
2. **Global styles** — write the target's color tokens, spacing scale, keyframes, utility classes, and global scroll behaviors into the project's global stylesheet.
3. **Content types** — define type/interface structures for the content shapes you observed (skip if the stack is untyped).
4. **Icons** — find all inline `<svg>` on the page, deduplicate, and save as named components (e.g. `SearchIcon`, `ArrowRightIcon`, `LogoIcon`) in the stack's idiomatic location.
5. **Assets** — write and run a small download script (`scripts/download-assets.mjs` or `.py`) that fetches all images/videos/binaries to the static dir, preserving meaningful structure. Use the asset-discovery snippet in `references/extraction-scripts.md` to enumerate first; download in batches (~4 at a time) with error handling.
6. **Verify** the build passes.

## Phase 3: Component Specification & Dispatch

The core loop. For each section in the topology (top to bottom): **extract → write spec → dispatch builders**.

### Step 1 — Extract
For each section, via browser-utils:
1. **Screenshot** the section in isolation → `docs/design-references/`.
2. **Extract CSS** for every element using the per-component `getComputedStyle` walker in `references/extraction-scripts.md` — don't hand-measure. Run once per container, capture full output.
3. **Extract multi-state styles** — for scroll/hover/active-tab elements, capture state A, trigger the change, re-run extraction for state B; the **diff IS the behavior spec** ("Property X: A → B, triggered by TRIGGER, transition TRANSITION_CSS").
4. **Extract real content** — all text, alt, aria-labels, placeholders. For tabbed content, click each tab and extract per state.
5. **Identify assets** — which downloaded files and icon components this section uses; check for layered/overlay images.
6. **Assess complexity** — count distinct sub-components (each with its own styling/structure/behavior).

### Step 2 — Write the spec file
Create `docs/research/components/<component-name>.spec.md` using the template in `references/component-spec-template.md`. Fill **every** section; write "N/A" only after genuinely confirming it (even footers have link hover states). This is the contract between extraction and the builder — never skip it.

### Step 3 — Dispatch builders
Based on complexity, dispatch builder agent(s) (via the Agent/subagent tool; use isolated git worktrees when the environment supports them so parallel builders don't collide):
- **Simple section** (1–2 sub-components): one builder for the whole section.
- **Complex section** (3+ distinct sub-components): one builder per sub-component + one wrapper builder that imports them (sub-components first).

Every builder receives, **inline in the prompt** (never "go read the spec"):
- The full spec file contents
- Path to the section screenshot
- Which shared pieces to import (icon components, class-name/util helpers, the stack's UI primitives)
- The target file path in the chosen stack's idiom
- The exact responsive breakpoints and what changes at each
- Instruction to verify the project's typecheck/build before finishing

**Don't wait.** After dispatching a section's builders, move to extracting the next section — builders run in parallel while you continue.

### Step 4 — Merge
As builders complete: merge their branches/worktrees, resolve conflicts intelligently (you have full context), and verify the build after each merge. Fix any type errors immediately. Repeat the extract → spec → dispatch → merge cycle until all sections are built.

## Phase 4: Page Assembly

Wire everything into the root page/route:
- Import all section components in topology order
- Implement page-level layout (scroll containers, columns, sticky positioning, z-index layering)
- Connect real content to component props
- Implement page-level behaviors: scroll-snap, scroll-driven animations, theme transitions between sections, intersection observers, smooth scroll (Lenis etc.)
- Verify the full build passes clean

## Phase 5: Visual QA Diff

Do NOT declare done after assembly.
1. Put the original and your clone side by side (or screenshot both at the same widths).
2. Compare section by section, top to bottom, at **1440px**, then again at **390px**.
3. For each discrepancy: check the spec — if the spec was wrong, re-extract and update it, then fix the component; if the spec was right but the build diverged, fix the component to match.
4. Test all behaviors: scroll the whole page, click every button/tab, hover interactive elements. Confirm smooth scroll feels right, header transitions fire, tab switching works, animations play.

Only after this pass is the clone complete.

## Pre-Dispatch Checklist

Before dispatching ANY builder, verify every box — if you can't, extract more:
- [ ] Spec file written with ALL sections filled
- [ ] Every CSS value is from `getComputedStyle()`, not estimated
- [ ] Interaction model identified and documented (static / click / scroll / time)
- [ ] Stateful components: every state's content and styles captured
- [ ] Scroll-driven components: trigger threshold, before/after styles, transition recorded
- [ ] Hover states: before/after values and transition timing recorded
- [ ] All images identified (including overlays and layered compositions)
- [ ] Responsive behavior documented for at least desktop and mobile
- [ ] Text content is verbatim, not paraphrased
- [ ] Builder prompt is under ~150 lines of spec; if over, split the section

## What NOT to Do

Lessons from failed clones — each cost hours of rework:
- **Don't build click-tabs when the original is scroll-driven** (or vice versa). Determine the model FIRST by scrolling before clicking. #1 most expensive mistake.
- **Don't extract only the default state.** Click every tab; capture header styles at scroll 0 AND past the threshold.
- **Don't miss overlay/layered images.** Check every container's DOM tree for stacked `<img>` and positioned overlays.
- **Don't build mockups of content that's actually video/animation.** Check for `<video>`, Lottie, canvas before hand-building HTML.
- **Don't approximate CSS.** "Looks like `text-lg`" is wrong when the computed line-height differs. Use exact values.
- **Don't build one monolithic commit.** Incremental progress with verified builds at each step is the whole point.
- **Don't reference external docs from builder prompts.** Every builder gets its spec inline — zero need to read anything else.
- **Don't skip asset extraction.** Without real images/videos/fonts the clone always looks fake, however perfect the CSS.
- **Don't over-scope a builder.** A long prompt because the section is complex = split it.
- **Don't bundle unrelated sections** (a CTA and a footer) into one agent.
- **Don't skip responsive extraction.** Inspect at 1440 / 768 / 390 during extraction.
- **Don't forget smooth-scroll libraries.** Native scrolling feels different; users spot it instantly.
- **Don't dispatch without a spec file.**

## Completion

Report: total sections built, total components created, total spec files (should match components), total assets downloaded (images/videos/SVGs/fonts), build status, visual-QA results (remaining discrepancies), and any known gaps or limitations.

## References
- `references/inspection-guide.md` — behavior catalog, interaction sweeps, design-token & component-inventory checklists
- `references/extraction-scripts.md` — browser JS snippets (asset discovery, per-component `getComputedStyle` walker, multi-state diffing)
- `references/component-spec-template.md` — the component spec file template

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At the end of a substantial run of this skill, perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this run reached a meaningful wrap-up. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against this skill's declared purpose and produce a short review plus ≥1 concrete, skill-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this skill's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id`; if a parent flow already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "skill:clone-website-ui" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
