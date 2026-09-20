# Hugo Presentation Layer

Stage 2 of `create-pages`: how the docs directory becomes a Hugo project and renders **in
place** (`scripts/scaffold-hugo.py`). Optional — a documentation space is complete and valid
without it. Loaded on demand — `SKILL.md` carries only the dispatch.

## Ownership model

`docs/` is both the **Hugo project root** and the **single content source**. Hugo runs with
`docs/` as its working directory, and every documentation path is *mounted* into Hugo
rather than copied, so the Markdown tree is never duplicated or rewritten.

| Path | Owner | Notes |
|------|-------|-------|
| `docs/<type>/**.md` | documentation | The content. Never touched by the site layer. |
| `docs/hugo.toml` | shared | Scaffold owns only the managed block (navigation cascade + mounts); the rest is yours. The `theme` line and the `Book*` params are rendered once per mode and then yours too. |
| `docs/themes/book/**` | upstream theme | Vendored snapshot of `alex-shpak/hugo-book`. Do not edit; update with `--action theme --fetch --force`. |
| `docs/.speckit/nav/section-index.md` | scaffold | The one stub mounted as the section index of every directory without an `index.md`. |
| `docs/layouts/**` | scaffold (yours after edit) | Book mode: two overrides only. Builtin mode: minimal self-contained templates. |
| `docs/static/css/site.css` | scaffold (builtin only) | Single stylesheet, no build step. Book mode uses the theme's CSS. |
| `docs/.gitignore` | scaffold | Ignores `public/`, `resources/`, `.hugo_build.lock`. |
| `docs/public/` | Hugo | Build output. Never committed, never documentation. |

Scaffold-owned directories (`layouts`, `static`, `public`, `resources`, `themes`,
`archetypes`) are **not** documentation: a `create-docs` reconcile run must not triage them
as content. The vendored theme is reduced to its runtime parts (`layouts`, `assets`,
`static`, `i18n`, `theme.toml`, `hugo.toml`, `LICENSE`) precisely so that no third-party
`.md` lands under `docs/`, where `docs-utils.py --action validate` audits every Markdown
file it finds. Install the theme by other means (submodule, full clone) and that guarantee
is gone: `themes/book/README.md` alone trips the reserved-filename rule.

## Render modes

| Mode | Renderer | Requirements | Chosen when |
|------|----------|--------------|-------------|
| `book` (preferred) | Hugo Book, vendored at `docs/themes/book` | Hugo ≥ 0.158 (`theme.toml` `min_version`, enforced by Hugo itself) | `--theme auto` and the theme is installed, or `--theme book` |
| `builtin` | the skill's own layouts | any Hugo ≥ 0.56 (module mounts) | the theme is absent, or `--theme builtin` |

What book mode buys, all offline (the theme vendors fuse.js, mermaid and KaTeX itself):
sidebar navigation, client-side search, light/dark themes, print styles, mermaid and math
rendering, mobile layout. What it costs: ~5 MB of vendored third-party files committed to
the repository, and a Hugo floor of 0.158.

Book mode is configured through params only — `BookSection = "*"` (the menu spans the whole
content tree, because content is mounted at `content/<type>` rather than under a single
`docs` section), `BookPortableLinks = true`, `BookTheme = "auto"`, `BookSearch = true`,
`BookComments = false`. Two theme templates are overridden, and nothing else:

- `layouts/_partials/docs/title.html` — the label of a page or section. Documents here
  carry no front matter, so the theme would humanize the file name; this override reads the
  first `# H1` from `.RawContent`. It must not read `.Content`: the theme's heading render
  hook appends an anchor, so a plainified rendered `<h1>` ends in `#`.
- `layouts/_shortcodes/speckit-children.html` — the child index used by the mounted
  section-index stub (and available in any hand-written `index.md`). The theme's own
  `{{< section >}}` shortcode is deprecated upstream and warns on every use.

## Installing and updating the theme

```bash
# status: is it installed, which ref, which Hugo does it require, is the local Hugo new enough
python3 ${SKILL_HOME}/scripts/scaffold-hugo.py --action theme --root .

# install the pinned release (git clone --depth 1, then reduced to runtime parts)
python3 ${SKILL_HOME}/scripts/scaffold-hugo.py --action theme --root . --fetch

# update, or move to another ref / a mirror
python3 ${SKILL_HOME}/scripts/scaffold-hugo.py --action theme --root . --fetch --force \
  [--theme-ref v0.14.0] [--theme-url <mirror>]
```

The snapshot has no `.git`, so **commit it**: CI then builds with neither network access
nor Go, and `themes/book/.speckit-theme.json` records url, ref, commit and what was
dropped. A `themes/book` that carries its own `.git` (submodule or manual clone) is left
alone — the script refuses to replace it and says so.

A newer theme release may require a newer Hugo. `--theme-ref` is the escape hatch:
`v0.14.0` needs Hugo ≥ 0.158, `v12.0.0` needs ≥ 0.146. Older tags (`v9` and below) use the
pre-0.146 template layout, so the two overrides above do not apply to them.

## Navigation completion

Book mode builds its sidebar from the content tree, which exposes three gaps in a
front-matter-less docs space. All three are closed from `hugo.toml` and mounts — **no
document is created or edited**:

1. **Missing sections.** In Hugo, a top-level content directory is always a section, but a
   *nested* directory is one only if it has an `_index.md`. Without it, `reference/cli/`
   contributes no group at all and its pages appear directly under `reference`. The
   scaffolder therefore mounts `docs/.speckit/nav/section-index.md` as
   `content/<dir>/_index.md` for every Markdown-bearing directory that has no `index.md`,
   including the docs root (whose home page would otherwise render blank). The stub renders
   `{{< speckit-children >}}`, so each landing page lists its children from the live tree
   and can never go stale. Because the page then has content, the theme renders its sidebar
   entry as a real link instead of a dead label.
2. **Ordering.** With no `weight` anywhere, Hugo falls back to file path, so the sidebar
   opens with `archive/`. A `[[cascade]]` per directory assigns the documentation reading
   order (concepts 10, tutorials 20, tasks 30, reference 40, decisions 50, contribute 60,
   notes 70, archive 80; other directories follow alphabetically).
3. **Labels and crowding.** The same cascade carries a generated `title` for directories
   without an `index.md` (acronyms preserved: `cli` → `CLI`) and
   `params.bookCollapseSection` for sections with at least `--collapse-threshold` (default
   6) pages. Sections *with* an `index.md` get no cascade title, so their `# H1` stays the
   label.

Cascade targets are matched per directory (`[cascade.target] path = "/reference/cli"`), so
the collapse flag never reaches a document — a page with `bookCollapseSection` would render
as a toggle instead of a link. Use `cascade.target`, not `cascade._target`, which Hugo
deprecated in v0.156.0.

The `nav.generated_indexes` list in the JSON report is a to-do list for the documentation
owner, not a defect: a curated `index.md` (written via `create-docs` / `improve-docs`)
always reads better than a generated child list.

## Why mounts, and why `index.md` is remapped

Two project conventions collide with Hugo defaults, and mounts resolve both:

1. **Hugo reads `content/` by default; our Markdown lives in typed directories.** Each
   documentation directory is mounted to `content/<dir>`.
2. **Directory indexes are `index.md`** (project naming convention; a nested `README.md` is
   forbidden). In Hugo an `index.md` makes its directory a *leaf bundle*, which demotes every
   sibling page to a mere resource — the siblings stop being pages at all. So each `index.md`
   is mounted as `content/<dir>/_index.md` (branch bundle) and excluded from the directory
   mount via `excludeFiles`, leaving the file itself untouched on disk.

A directory containing no Markdown at all (pure media, e.g. `docs/assets/`) is mounted into
`static/<dir>` instead. Content directories additionally get a Markdown-excluding static
mount, so images stored beside their prose are published at the same relative path.

Because an explicit mount **replaces** Hugo's default mount for that component, the managed
block re-declares `static → static` for the scaffold's own stylesheet.

## Link and image resolution

The Markdown keeps repo-native relative links (`../concepts/overview.md`) — no site-specific
syntax, no shortcodes. In **book mode** the theme resolves them: `BookPortableLinks = true`
makes its own link/image hooks look each destination up in Hugo's page graph (and in page
resources), leaving anything unresolvable untouched. Set it to `"warning"` for an audit run —
expect noise, because documentation legitimately links to source files outside the docs
directory, which have no page on the site.

In **builtin mode** two render hooks of our own do the same job:

- `layouts/_default/_markup/render-link.html` resolves a `.md` destination through Hugo's
  page graph (`.Page.GetPage`) and emits the target page's real URL. Correct under any URL
  scheme; anything that does not resolve to a page (external links, bare fragments,
  unpublished paths) passes through untouched.
- `layouts/_default/_markup/render-image.html` resolves a relative image path against the
  content file's own directory, then emits it relative to the current page URL.

Book mode must **not** ship these hooks: a project-level render hook overrides the theme's,
losing its page-resource fallback and its link checking.

With `relativeURLs = true` every generated URL is page-relative, so the output works under a
sub-path (project Pages sites) and is browsable straight off disk via `file://`.

> Pitfall, verified on 0.141.0: the map form of `uglyURLs` (`[uglyURLs] page = true`) is
> **not** honored — Hugo silently falls back to pretty URLs. Do not try to fix link shapes
> with `uglyURLs`; the render hooks are the mechanism.

## Publish scope

Everything under `docs/` is published — the six formal types, `notes/`, `archive/`, and media.
`notes/` frontmatter uses `status: draft`, which is *not* Hugo's `draft` key, so notes are
published like any other page. To withhold a zone instead, drop its mount from the managed
block and record the decision in `hugo.toml` above the block.

## Build runner: the CI image first

A build must answer "does this render correctly *in CI*", so Hugo runs in the CI image by
default — not the workstation's binary, which is typically older (0.141 vs 0.163 in the
environment this was built in) and may not even reach the theme's floor. `--runner` picks:

| Runner | Behaviour |
|--------|-----------|
| `auto` (default) | docker with the CI image; on any docker/image gap, fall back to the local binary and say so in `warning` |
| `docker` | CI image only — no silent fallback; gaps are reported with a fix |
| `local` | workstation binary only (subject to the theme's minimum version) |

The image is resolved in this order, so a project that overrode it stays consistent:

1. `--hugo-image <ref>`
2. `SPECKIT_HUGO_IMAGE` environment variable
3. the **rendered CI pipeline** (`.aoneci/deploy-pages.yaml`, `.github/workflows/deploy-pages.yaml`) — the strongest "same as CI" signal
4. `scripts/ci-templates/hugo-image.txt` — the shared default that `scaffold-ci.sh` also
   renders into the pipeline, so stage 2 and stage 3 cannot drift apart

`--action image` prints the resolved image and its source. The workspace is bind-mounted at
`/workspace`, so `<docs>/public` is written straight back to the host; a probe first checks
the daemon can see the workspace and reports `workspace-not-visible` instead of silently
building an empty site. The container runs as root (this image's entrypoint hooks need it),
so build output is root-owned — harmless for a gitignored `public/`, but remove it with the
same privileges.

The reported `hugo_version` always comes from the runner that actually built, and the
command is the same `hugo --minify` the CI pipeline runs.

## Commands

```bash
# report the theme's state; add --fetch to install or update it (the only networked step)
python3 ${SKILL_HOME}/scripts/scaffold-hugo.py --action theme --root . [--fetch] [--force]

# scaffold or repair the site layer (safe local writes; never clobbers your edits)
# --theme auto (default) prefers the vendored theme and degrades to the builtin layouts
python3 ${SKILL_HOME}/scripts/scaffold-hugo.py --action scaffold --root . --site-title "<title>" \
  [--theme auto|book|builtin] [--collapse-threshold 6]

# report drift only (missing files, stale mounts, reserved-name collisions) — no writes
python3 ${SKILL_HOME}/scripts/scaffold-hugo.py --action check --root .

# print the computed navigation+mount block without touching disk
python3 ${SKILL_HOME}/scripts/scaffold-hugo.py --action mounts --root .

# which image would a build use, and why
python3 ${SKILL_HOME}/scripts/scaffold-hugo.py --action image --root .

# build into docs/public — in the CI image by default, local binary as fallback
python3 ${SKILL_HOME}/scripts/scaffold-hugo.py --action build --root . \
  [--runner auto|docker|local] [--hugo-image <ref>] [--base-url <url>]

# local preview in the same image (live reload; Ctrl-C to stop)
docker run --rm -p 1313:1313 -v "$PWD:/workspace" -w /workspace/docs <image> \
  hugo server --bind 0.0.0.0
```

File actions are reported per path: `created`, `unchanged`, `kept` (you edited it — left
alone), `overwritten` (only with `--force`), `mounts-synced`, `rewritten` (config re-rendered
for the other mode, `--force`), `mode-mismatch` (a mode switch was needed and **nothing** was
written), `removed` (an untouched file of the other mode, dropped by a switch),
`stale-edited` (an edited file of the other mode, kept for you to decide), `unmanaged` (the
managed block markers are missing from `hugo.toml`; nothing was written). A repeat run on an
unchanged tree reports `unchanged` for every path and writes nothing.

The JSON report also carries `theme` (mode, `config_mode` — what `hugo.toml` actually
selects, ref, commit, the theme's Hugo minimum, the local Hugo version, compatibility) and
`nav` (sections, `generated_indexes`, `collapsed`, `order`). A build additionally reports
`runner`, `image`, `image_source`, the `hugo_version` that built, and every `attempts`
entry when the default runner fell back.

## CI guidance (stage 3 input)

Stage 3 owns hosting: `scaffold-ci.sh --platform aoneci` renders a real pipeline, and the
`github` platform is a stub. The snippet below is the **starting point for that stub**, not a
generated file — verify each action version against current GitHub documentation before
turning it into a template. The build step itself is the same everywhere: install Hugo
extended, build from `docs/`, publish `docs/public`.

```yaml
- uses: peaceiris/actions-hugo@v3
  with:
    hugo-version: latest
    extended: true
- name: Build documentation site
  working-directory: docs          # docs/ is the Hugo project root
  run: hugo --minify --baseURL "${{ steps.pages.outputs.base_url }}/"
- uses: actions/upload-pages-artifact@v3
  with:
    path: docs/public
```

Two CI notes: run Hugo from `docs/`, not the repository root (the config lives in `docs/`), and
pass `--baseURL` explicitly when the site is served from a sub-path. A build that must fail on
broken content can add `--panicOnWarning`.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Error: Unable to locate config file` | Hugo run from the repository root | `cd docs` first, or use `--action build` |
| A section renders one page and swallows its siblings | `index.md` reached Hugo unmapped (leaf bundle) | Re-run `--action scaffold` to regenerate the remaps |
| New documentation directory missing from the site | Mount block is stale | `--action check` reports it; `--action scaffold` syncs it |
| `toml: table X already exists` | Duplicate table appended to `hugo.toml` | Merge your keys into the existing table |
| Raw HTML stripped from a page | `markup.goldmark.renderer.unsafe` disabled | Keep `unsafe = true` in `hugo.toml` |
| Images 404 | Media directory added after scaffolding | Re-run `--action scaffold` to add the static mount |
| `'assets' is a Hugo component name` | A docs directory shadows a Hugo component | Works (it is mounted explicitly); rename for clarity if convenient |
| `<title>· Site</title>`, or blank link text in lists/nav | Layout used `.Title`/`.LinkTitle` directly; documents here carry no front matter, so both are empty | Render titles through `partials/title.html` (first `<h1>` fallback) |
| `deprecated: module.mounts.excludeFiles` warning | The mount generator still emits `excludeFiles` (deprecated in Hugo v0.153.0 in favour of `files`) | Expected today; it still functions. Migrating needs the `files` semantics checked against current Hugo docs, because the `index.md` remap depends on the exclusion |
| A layout fix from a newer skill version never appears | Any file differing from the shipped asset is classified user-edited and reported `kept` | Diff the file against the asset, then re-scaffold with `--force` — which also discards genuine local edits |
| `Error: module "book" not found` | `theme = "book"` is in the config but `docs/themes/book` is missing (never committed, or a submodule was not initialised) | `--action theme --fetch`, then commit the snapshot; or switch back with `--theme builtin --force` |
| `Error: this project requires Hugo version >= 0.158.0` | The Hugo that ran is older than the vendored theme — e.g. `--runner local` on a stale workstation binary | Drop the `--runner local` override (the default builds in the CI image), upgrade Hugo, pass `--theme-ref v12.0.0` (needs ≥ 0.146), or scaffold `--theme builtin` |
| Build reports `reason: image-unavailable` | The CI image is environment-specific and not pullable here | `--hugo-image <ref>`, `SPECKIT_HUGO_IMAGE=<ref>`, or edit `ci-templates/hugo-image.txt` so stage 3 renders the same one; `--runner local` builds without docker (version may differ from CI) |
| Build reports `reason: workspace-not-visible` | A sandboxed docker daemon cannot see host paths, so the mount is empty | Copy the tree into a container (`docker cp`) and build there, or use `--runner local` |
| Build reports `runner: local` with a `warning` | The docker path was unavailable, so the workstation Hugo rendered the site | Fine for a quick look; re-run in the CI image before trusting the result |
| The site renders locally but breaks in CI | Local build used a different Hugo | `--action image` to see which image CI uses, then `--runner docker` |
| `mode-mismatch` in the report and nothing was written | The config on disk belongs to the other render mode; a partial switch would leave the site unbuildable | Re-run with `--force` to re-render the config, or keep the current mode with `--theme builtin` / `--theme book` |
| A nested directory shows no group in the sidebar, its pages sit under the parent | The generated section index is missing — book mode not active, or the block is stale | `--action check`; scaffold in book mode. Hugo only treats a nested directory as a section when it has an `_index.md` |
| Sidebar labels read like file names (`Directory Structure`), or end with `#` | The `docs/title.html` override is missing or was edited to read `.Content` | Re-scaffold (`--force` if you edited it); the H1 must come from `.RawContent` |
| A sidebar entry looks clickable but does nothing | A section page with no content: the theme renders a label, not a link | Add an `index.md`, or re-scaffold so the section-index stub is mounted |
| Sidebar opens with `Archive` | The navigation cascade is missing (builtin mode, or an `unmanaged` config) | Scaffold in book mode with the managed block present |
| `docs-utils validate` reports `reserved-name-misplaced: docs/themes/book/README.md` | The theme was installed as a submodule/full clone, keeping its own Markdown | Re-install with `--action theme --fetch --force` (runtime parts only) |
| `unmarshal failed: invalid character '{'` on a content file | The file starts with `{`, which Hugo parses as JSON front matter | Do not start a mounted stub with a shortcode; keep the leading comment |

Verified against `hugo v0.163.3+extended` and `v0.163.2+extended` (mount behaviour, title
fallback, the navigation cascade and the Book theme at `v0.14.0`), and earlier against
`v0.141.0+extended` (render hooks, `uglyURLs` pitfall, builtin mode end-to-end). Module
mounts require Hugo ≥ 0.56; the extended build is not required by either mode (no SCSS — the
theme ships plain CSS since its 0.13 line). Book mode requires Hugo ≥ 0.158, so a workstation
with an older binary can still scaffold and commit it and let CI build — that split is
expected, and `--action build` reports it instead of failing.
