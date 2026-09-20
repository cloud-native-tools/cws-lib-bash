---
name: create-pages
description: |
  Publish a project's documentation as a static site — the optional presentation
  layer on top of a documentation space, delivered as a three-stage pipeline:
  local doc library (the docs directory) → Hugo-rendered static site
  (docs/public) → pages service (local preview / aoneci / github). Rendering
  prefers the Hugo Book theme and completes the site navigation (sidebar order,
  labels, section landing pages) from the live docs tree. Content is
  mounted, never copied, and everything the skill writes stays inside the docs
  directory except the one CI file a hosting platform requires at the repository
  root. Use when the user mentions ["setup pages", "hugo build", "hugo serve",
  "deploy docs", "create-pages", "documentation site", "Hugo", "hugo site",
  "Hugo Book", "hugo-book", "theme", "static site", "hugo.toml", "site build",
  "publish docs", "gh-pages", "aoneci", "sidebar", "navigation",
  "文档构建", "页面部署", "CI配置", "静态网站", "文档站点", "文档网站",
  "对外呈现", "发布文档", "本地预览", "主题", "导航", "侧边栏", "目录结构"]
skill_id: "<SKILL:.specify/skills/create-pages/SKILL.md>"
---

# Create Pages — doc library → Hugo site → pages service

## Overview

The **optional presentation layer** on top of a documentation space. Optional
means a space is complete and valid without it: the library's structure belongs
to `create-docs`, the content of a document belongs to `improve-docs`, and this
skill only adds the machinery that renders and serves what they produce — it
never rewrites documentation.

One pipeline, three stages, run in order. Each stage has exactly one owner and
one output, so a failure is always attributable to a stage:

| Stage | Question it answers | Output | Tooling |
|-------|--------------------|--------|---------|
| **1 — 本地文档库** | What content is published? | The docs directory (default `docs/`), pure Markdown | none of this skill's — read-only here |
| **2 — Hugo 渲染** | How does Markdown become HTML? | The docs directory *is* a Hugo project; site builds to `<docs>/public` | `${SKILL_HOME}/scripts/scaffold-hugo.py` (Hugo Book theme preferred, built-in layouts as fallback) |
| **3 — Pages 服务** | Who serves the HTML? | `local` preview, or a hosting platform's CI pipeline | `hugo serve` / `${SKILL_HOME}/scripts/scaffold-ci.sh` |

Stage 3 targets — pick one, ask when the input does not say:

| Target | What it is | Status |
|--------|-----------|--------|
| `local` | A web server on this machine (`hugo serve`), for preview | works wherever `hugo` is installed |
| `aoneci` | The Alibaba-internal, GitLab-like hosting platform's pages service | implemented (`--platform aoneci`) |
| `github` | GitHub Actions + GitHub Pages (`gh-pages`) | **not implemented** — writes nothing and warns; contract in `scripts/ci-templates/github/README.md` |

`gitlab` means the open-source GitLab project and its hosting service. It is
**not** a target here — do not treat `aoneci` as "gitlab", and do not accept
`--platform gitlab` (the registry rejects it).

Do NOT use this skill when the project already has a different front-end build
pipeline, or when there is no documentation directory to serve.

## Workflow

Run the stages in order. A later stage never repairs an earlier one — it reports
back. Verification for every stage: [`./references/verification.md`](./references/verification.md).

### Stage 1 — 本地文档库 (read-only)

Establish what gets published, and nothing more:

- Resolve the docs directory (default `docs/`, else `--docs-dir`). It must exist
  and contain `.md` content; if it does not, stop and ask — do not scaffold a
  site over an empty library.
- The library is the **only** content source: every published page comes from a
  file inside it. Content outside it (root `README.md`, a sibling directory) is
  **excluded by default** and may be included only on an explicit user request,
  recorded in the report along with the mechanism chosen.
- Do not restructure, rename, or rewrite anything in the library. Placement and
  taxonomy → `create-docs`; document content → `improve-docs`.

### Stage 2 — Hugo 渲染

Make the docs directory the **Hugo project root** and render it. Deterministic — the
scaffold is a script, never hand-written HTML. Two render modes, and the preferred one
is a theme:

| Mode | What renders the site | Used when |
|------|----------------------|-----------|
| `book` (**preferred**) | **Hugo Book** — `alex-shpak/hugo-book`, vendored at `<docs>/themes/book`: sidebar, search, dark mode, mermaid/katex, all offline | the theme is installed (needs Hugo ≥ 0.158) |
| `builtin` | the skill's own minimal layouts, zero dependencies | the theme is absent — `--theme auto` degrades here rather than failing |

Install the theme first — the only step that touches the network — then scaffold and
build. **Builds run in the CI image by default** (`--runner auto` → docker), so a local
render and the CI render use the same Hugo; a workstation binary is only the fallback.
Full command catalogue, ownership map, mount and navigation rationale, and
troubleshooting: [`./references/hugo-site.md`](./references/hugo-site.md).

```bash
python3 "${SKILL_HOME}/scripts/scaffold-hugo.py" --action theme --root .            # status only
python3 "${SKILL_HOME}/scripts/scaffold-hugo.py" --action theme --root . --fetch    # install pinned tag
python3 "${SKILL_HOME}/scripts/scaffold-hugo.py" --action check --root .            # drift only, no writes
python3 "${SKILL_HOME}/scripts/scaffold-hugo.py" --action build --root .            # build in the CI image
```

**Navigation completion** (book mode) is part of scaffolding, and it is derived from the
live docs tree — no document is edited to achieve it:

- **Every Markdown-bearing directory becomes a section.** Hugo does *not* treat a nested
  directory without an index page as a section, so its pages would flatten into the
  parent and the grouping would vanish from the sidebar. One shared stub is *mounted* as
  the section index of each such directory, giving it a real landing page that lists its
  children at build time.
- **Reading order, not alphabetical**: concepts → tutorials → tasks → reference →
  decisions → contribute → notes → archive, then any other directory. Otherwise the
  sidebar opens with `archive/`.
- **Labels** come from each document's first `# H1`; a directory with no index page gets
  a generated label instead.
- **Sections above `--collapse-threshold` (default 6) pages collapse**, so a 24-page
  reference does not flood the sidebar.

Report `nav.generated_indexes` in the wrap-up: every entry is a directory that would read
better with a real `index.md` — authoring one is `create-docs`' job, not this skill's.

Guarantees this stage provides and that you MUST NOT break:

- **Mount, never copy** — no `.md` is duplicated, moved, or rewritten; no staged
  copy of the tree, and `content/` never materializes on disk.
- **`index.md` stays `index.md`** on disk; it is mounted as `_index.md` (branch
  bundle) so sibling pages stay pages.
- **Documentation is never written** — navigation is achieved with config (a Hugo
  cascade) and mounts only. No generated Markdown lands in the library.
- **Repo-native links keep working** — relative `.md` links and relative image
  paths resolve at build time (the theme's portable links in book mode, render hooks in
  builtin mode); never rewrite links.
- **Only the managed block is machine-owned** — everything else in `hugo.toml`,
  and any layout or stylesheet the user edited, is reported `kept` (`--force`
  overrides). A repeat run on an unchanged tree writes nothing.
- **Mode switches are atomic** — switching between `book` and `builtin` rewrites the
  config and drops the other mode's layouts together, or does nothing at all: a
  `mode-mismatch` report means the run wrote nothing and needs `--force`. Locally edited
  leftovers are reported (`stale_edited`), never deleted.
- **Build output is `<docs>/public`**, inside the library's directory — never a
  repository-root `dist/`.
- **Local rendering equals CI rendering** — `--action build` runs Hugo inside the CI
  image (resolved from the rendered pipeline, `SPECKIT_HUGO_IMAGE`, or the shared
  `ci-templates/hugo-image.txt` that stage 3 renders from), never the workstation's
  Hugo, which is typically older than the image and often older than the theme's floor.
  A local binary is used only as a fallback and the report says so; verifying a site
  with a different Hugo than CI proves nothing.
- **Scaffolding is offline** — only `--action theme --fetch` uses the network, and its
  failure degrades to `builtin` instead of failing the stage. Missing docker, an
  unpullable image, an absent binary, or a binary older than the theme are reported as
  environment gaps with the fix, not as scaffold defects.

Commit the vendored theme: it carries no `.git`, so CI needs neither network access nor
Go, and the pinned ref/commit is recorded in `themes/book/.speckit-theme.json`.

There is exactly **one** renderer. Do not add a second config, a staging copy,
or a parallel build script for a particular hosting target.

### Stage 3 — Pages 服务

Serve the rendered site. For `local`, nothing is scaffolded — run Hugo's own server from
the docs directory. Use the CI image here too, so preview and CI agree:

```bash
IMAGE=$(python3 "${SKILL_HOME}/scripts/scaffold-hugo.py" --action image --root . \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["image"])')
docker run --rm -p 1313:1313 -v "$PWD:/workspace" -w "/workspace/<docs>" "$IMAGE" \
  hugo server --bind 0.0.0.0     # then report http://localhost:1313/
```

A workstation `hugo server` is the fallback and only works when its version satisfies
the theme; say which one you used.

For a hosting platform, render its pipeline (one file, no Hugo artifacts):

```bash
bash "${SKILL_HOME}/scripts/scaffold-ci.sh" --site-name <name> [--platform aoneci|github] [--branch ...] [--image ...] [--force]
```

- **Preflight**: an existing CI file is skipped, not overwritten — confirm
  overwrite intent with the user before passing `--force`. Review the JSON
  summary (`created` / `skipped` / `warnings`); a `skipped` entry without a
  prior confirmation is a stop condition.
- **The rendered CI file is the only artifact outside the docs directory**,
  because platforms discover pipelines at a fixed repository-root path. That is
  the single sanctioned exception to stage 1's containment rule — never widen it.
- **`--image` is environment-specific.** The default is pullable only in the
  Alibaba-internal environment; outside it, ask for the user's Hugo image (or a
  local-target plan) before scaffolding.
- Platform without a template (`github` today) → nothing is written and a
  warning names the manual-authoring contract. Report that honestly; do not
  claim the target is wired.

### Wrap-up

Report per stage: the library that was published, the render mode with the theme ref it
used, the scaffolded/kept Hugo files, the navigation summary (sections, generated section
indexes, collapsed sections), the stage-3 target with its verification outcome, and any
content deliberately excluded. Suggest committing — including the vendored theme, which
CI needs. Then run the Feedback step below.

## Resources

| Path | Contents |
|------|----------|
| `${SKILL_HOME}/scripts/scaffold-hugo.py` | **Stage 2**: deterministic mount-mode scaffolder (`scaffold` / `check` / `mounts` / `build` / `theme` / `image`) — resolves the render mode, computes the module-mount block and the navigation cascade from the live docs tree, vendors the Book theme on request, builds in the CI image (docker) with a local-Hugo fallback, never clobbers user-edited files. Stdlib-only, one JSON object per invocation |
| `${SKILL_HOME}/assets/book/` | **Stage 2, book mode**: `hugo.toml.tmpl` (theme + Book params), `layouts/_partials/docs/title.html` (H1 label override), `layouts/_shortcodes/speckit-children.html` (child index), `dotspeckit/nav/section-index.md` → the mounted section-index stub, `dotgitignore` |
| `${SKILL_HOME}/assets/hugo/` | **Stage 2, builtin mode**: `hugo.toml.tmpl` (`{{SITE_TITLE}}` / `{{SITE_DESCRIPTION}}` / `{{MOUNTS}}`), `layouts/` (`_default/baseof,list,single`, `index.html`, `_markup/render-link,render-image`), `static/css/site.css`, `dotgitignore` → `<docs>/.gitignore` |
| `${SKILL_HOME}/references/hugo-site.md` | **Stage 2**: ownership map, theme install/update, navigation completion, mount rationale (`index.md` → `_index.md`), link/image resolution, publish scope, commands, local serve, CI guidance, troubleshooting |
| `${SKILL_HOME}/scripts/scaffold-ci.sh` | **Stage 3**: renders one hosting platform's CI pipeline and nothing else (run with `--help`) |
| `${SKILL_HOME}/scripts/ci-templates/` | **Stage 3**: per-platform pipeline templates + registry/extension contract (`README.md`); `hugo-image.txt` is the shared build image (stage 2 builds locally in it, stage 3 renders it into the pipeline); `aoneci/` implemented, `github/` structural stub |
| `${SKILL_HOME}/references/design-rationale.md` | Why behind each stage boundary and guarantee (observed failures) |
| `${SKILL_HOME}/references/verification.md` | Per-stage verification: render check, output checks, local serve, no-docs guard |

## Self-Improvement Alignment

A rendered documentation site is a Harness output, not an Execution Subject by default; do not add self-modifying behavior to generated sites or deployment configuration. Site fixes remain Assisted Improvement through `create-pages`/`improve-docs`. This `create-pages` Skill is itself an Execution Subject: qualified own-run evidence may enter `.specify/shared/workflow/self-improvement-workflow.md` and route to `improve-skills`.

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:create-pages" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
