# Design Rationale — create-pages

Why each stage boundary and guarantee exists. Every item was observed as a real
failure, not inferred. Observations marked *(v0.163.3)* were reproduced in this
repository against Hugo v0.163.3 extended; those marked *(book)* were reproduced
against Hugo v0.163.2 extended in
`reg.docker.alibaba-inc.com/xuanji-images/hugo:latest` with hugo-book `v0.14.0`;
the earlier ones come from the original implementation run (Hugo v0.163.2 in the
same image).

## Stage boundaries

### Why three stages instead of one scaffold

The first implementation fused rendering and hosting into a single script: one
run wrote Hugo config, layouts, a build script, a CI pipeline, and a staging
directory. Two consequences showed up immediately — a hosting change forced a
re-run that also rewrote rendering artifacts, and the build script existed only
to serve one CI pipeline's expectations (a repository-root `dist/`). Splitting
content → rendering → hosting makes each failure attributable and lets a project
change its hosting target without touching a single rendered file.

### Why the docs directory is the only content source

Upper-layer systems (framework detectors, IDE indexers, AI instruction
generators, code-review heuristics) judge a project's type from its root files.
A root-level `hugo.toml` / `layouts/` makes a Go backend project look like a
Hugo docs project. Keeping every artifact inside the docs directory preserves
the project's true identity and makes the capability removable: deleting the
docs directory must leave core logic and build flow untouched.

The one sanctioned exception is the platform CI file. Hosting platforms discover
pipelines at a fixed repository-root path (`.aoneci/`, `.github/workflows/`), so
it physically cannot live in the docs directory. It is one file, it is named in
the report, and nothing else joins it.

### Why one renderer, not one per hosting target

The retired second renderer copied the whole Markdown tree into
`docs/.hugo-content/`, renamed files inside the copy, and published a
repository-root `dist/`. It worked, but it duplicated every document (two
sources of truth during a build), needed a root `.gitignore` entry, and wrote
outside the docs directory. Mount-based rendering achieves the same result with
zero duplication, so the staging renderer had no remaining justification.

## Rendering guarantees

### `index.md` stays `index.md`; the mount remaps it

Hugo bundle semantics: `index.md` in a directory is a **leaf bundle** — sibling
`.md` files in that directory are not rendered as pages. `_index.md` is a
**branch bundle** and siblings render normally. The docs taxonomy uses
`index.md` as each type directory's index, so a naive build silently drops
individual document pages: 18 output files instead of 39 (only index pages).
The mount block therefore maps each `<dir>/index.md` to
`content/<dir>/_index.md` and excludes it from the directory mount. The file on
disk keeps the name the docs convention requires.

### Scaffold-owned directories are never mounted as content

`layouts/index.html` reachable as content makes Hugo try to build a page from
it and abort with a security-policy error (`"text/html" is not whitelisted`);
a config file reachable as content gets copied into the output and published.
The mount computation therefore treats `layouts`, `static`, `public`,
`resources`, `themes`, `archetypes` as scaffold-owned, never as content — the
same list a `create-docs` reconcile run must skip when triaging.

### Title fallback partial *(v0.163.3)*

Documents here carry no YAML front matter, and Hugo returns an **empty**
`.Title` for such pages. Observed before the fix: a page rendered
`<title>· Spec Kit</title>`, and every list/nav entry built from `.LinkTitle`
rendered as a blank link. `partials/title.html` falls back to the first `<h1>`
of the rendered content — the document's authoritative title — then to a
humanized filename. Verified after the fix: `Spec Driven Development · Demo
Docs`, and non-empty link text on home, list, and nav.

### Raw HTML safety — `unsafe = true`

Documentation legitimately contains inline HTML (`<details>`, `<br>`, badges,
`<span style=...>`). Goldmark's default renderer **omits** raw HTML with a
warning, silently losing content; observed 137 `span style` occurrences
preserved in one material after enabling it.

### `relativeURLs = true`, `disableKinds`

Relative URLs keep the built site working under a hosting sub-path and when
browsed straight off disk. `disableKinds = ["taxonomy", "term", "RSS"]` stops
Hugo emitting empty `categories/`/`tags/` indexes and an unused feed for a site
that uses none.

### Config keys kept current *(v0.163.3)*

`languageCode` was deprecated in Hugo v0.158.0 in favour of `locale`, and
`.Site.LanguageCode` in favour of `.Site.Language.Locale`; both emitted build
warnings and are now fixed. **Still outstanding**: `module.mounts.excludeFiles`
was deprecated in v0.153.0 and replaced by a `files` setting — the mount
generator still emits `excludeFiles`, so builds print one deprecation warning.
It functions on v0.163.3; migrating it requires checking the `files` semantics
against current Hugo documentation, because the index remap depends on the
exclusion behaviour.

### Shipped-asset upgrades do not reach an existing site by themselves

The scaffolder classifies any file whose content differs from the shipped asset
as user-edited and reports it `kept`. That protects real edits, but it also
means a fixed layout in a newer skill version stays out of an already-scaffolded
site until someone passes `--force` — which also discards genuine local edits.
Diff before forcing.

## Theme and navigation

### Why Hugo Book is preferred, but the built-in layouts stay *(book)*

The built-in layouts render every document correctly and depend on nothing, but
they give a reader one flat home page and a header of top-level links: no
sidebar, no search, no dark mode, no mermaid. Hugo Book supplies all of that and
vendors its own fuse.js, mermaid and KaTeX, so nothing is fetched at build time.
It is therefore the default *when installed* — and only then. Two hard
constraints keep the fallback alive: the theme requires Hugo ≥ 0.158
(`theme.toml` `min_version`, enforced by Hugo, and the workstation used for this
work runs 0.141.0), and installing it needs network access, which was
intermittently unavailable during this very implementation. A capability that
fails when GitHub is unreachable cannot be the only path, so `--theme auto`
degrades to `builtin` and says so.

### Why the theme is vendored as a snapshot, not a submodule or Hugo module

A Hugo module import (`[[module.imports]]`) resolves the theme at build time,
which needs Go plus network in CI; a submodule needs the CI checkout to recurse.
Both make the build depend on a fetch that our pipelines do not guarantee. A
plain snapshot under `docs/themes/book` — clone, then delete everything outside
the runtime whitelist, including `.git` — is committed with the project, so CI
needs neither Go nor network, and `.speckit-theme.json` keeps url/ref/commit for
audit. The ref is a pinned release tag, never `main`: the upstream default branch
moves and would make the snapshot irreproducible.

### Why the snapshot drops the theme's own Markdown *(book)*

`docs-utils.py --action validate` walks `docs/**/*.md` with no exclusions. A full
theme checkout adds `themes/book/README.md` (reserved filename outside its
registered location — a blocking violation) plus an `exampleSite/` tree of
Markdown that would enter link checking. Keeping only `layouts`, `assets`,
`static`, `i18n`, `theme.toml`, `hugo.toml` and `LICENSE` leaves zero `.md` under
`themes/`, verified after install; the licence is kept because MIT requires it.

### Why navigation needs completing at all *(book)*

Measured on this repository's own `docs/` (87 pages): the sidebar was
alphabetical, so it opened with `archive/`; five of the ten directories —
`reference/agents`, `reference/cli`, `reference/commands`, `reference/skills`,
`reference/teams` — produced **no group whatsoever**, because Hugo treats a
*nested* directory as a section only when it has an `_index.md`, and their 48
pages appeared flat under `Reference`; the home page rendered empty (the docs
root has no `index.md`, and the theme's `main` block renders only `.Content`);
and every label came from a humanized file name, which turned
`reference/` into "References" and Chinese titles into their slugs.

### Why a mounted stub instead of generated `index.md` files

Writing the missing index pages into the docs tree is the obvious fix and the
wrong one: it makes the presentation layer author documentation (that belongs to
`create-docs`), and every generated file then goes stale as the tree changes. One
stub file mounted N times keeps the library untouched, and because its body is
`{{< speckit-children >}}` the child list is computed at build time — it cannot
drift. Two traps were hit while building it: a content file that *starts* with
`{` is parsed as JSON front matter (`unmarshal failed: invalid character '{'`),
hence the leading comment; and the theme's own `{{< section >}}` shortcode is
deprecated upstream and warns on every use, hence our own shortcode.

### Why order, labels and collapse come from a config cascade

Ordering needs `weight` and collapsing needs `bookCollapseSection` — both are
front-matter fields, and these documents have no front matter. A site-config
`[[cascade]]` with a per-directory `target.path` sets them from outside the
library. Verified *(book)*: section pages received `weight` and
`bookCollapseSection`, regular pages received neither (a page carrying
`bookCollapseSection` would render as a toggle instead of a link), and multiple
matching cascade entries merged instead of overriding each other. Hugo deprecated
`cascade._target` in v0.156.0 in favour of `cascade.target`; book mode requires
0.158 anyway, so the new key is emitted unconditionally.

### Why the label override reads `.RawContent` *(book)*

The first attempt reused the builtin approach — regex the first `<h1>` out of
`.Content` — and produced `Task Guides#`, `Notes — 临时文档区#` in the sidebar:
the theme's heading render hook appends an anchor link whose text is `#`. Reading
the first `# ` line out of the raw Markdown avoids the rendered form entirely, is
cheaper, and is stable across theme versions. Sections that have no index page
have no H1 either, so their label comes from the generated cascade `title`
instead — with acronyms preserved, because `cli` humanizes to "Cli".

### Why a mode switch is all-or-nothing

Observed while implementing: a book-mode run on a builtin site placed the theme
overrides and deleted the builtin layouts, but left the config selecting the
builtin mode — an unbuildable site. The parts that differ between modes (the
`theme` line, the `Book*` params) live *outside* the managed block, so they can
only change by re-rendering the whole config, which needs consent. A blocked
switch now reports `mode-mismatch` and writes nothing at all; `--force` performs
the whole switch. Untouched files of the other mode are removed (they are
recoverable from the skill), edited ones are reported as `stale-edited` and left
on disk.

### Built-in layouts must not require a Hugo that built-in mode exists to avoid

The builtin `baseof.html` used `.Site.Language.Locale`, added in Hugo v0.158.
Every page of a builtin-mode site therefore failed to render on v0.141.0
(`can't evaluate field Locale in type *langs.Language`) — exactly the environment
for which builtin mode is the answer. It now uses `.Site.Language.Lang`, which
exists in both, verified by a real build on v0.141.0.

### Why a local build runs in the CI image

The workstation this was built on has Hugo v0.141.0; the pipeline image has
v0.163.2. Two different renderers means a local "it builds" proves nothing about
CI — and with the Book theme it is worse than useless, because the local binary is
below the theme's floor, so the only signal it can produce is a false negative.
`--action build` therefore defaults to docker with the pipeline's image, and the
local binary is a reported fallback (`runner: local` plus a warning that the
rendered site may differ). Real numbers from the verification run: the default
runner reported `hugo_version: 0.163.2` while `hugo version` on the host said
0.141.0.

The image must be *the same one CI uses*, so it is resolved flag > environment >
the rendered pipeline file > a shared `ci-templates/hugo-image.txt` that
`scaffold-ci.sh` renders from as well. Before that file existed the default lived
only in the stage-3 script, so a stage-2 local build had no way to know it — two
places to edit, and silent divergence when only one was updated.

Mounting is a bind mount at `/workspace`, checked by a probe first: a sandboxed
daemon that cannot see host paths would otherwise build an empty site and report
success. `--user $(id -u):$(id -g)` was tried to keep output ownership sane and
rejected — this image's entrypoint hooks write to `/etc/profile.d` and abort as
non-root (`Failed to load general hooks`), so the container runs as root and the
gitignored `public/` is root-owned.

### The theme's Hugo floor binds the config, not the directory

The first version gated on the theme being *present* under `themes/`, which
refused a build for a site whose `hugo.toml` had been scaffolded in builtin mode
with a vendored theme still lying around. The gate now reads what the config
actually selects (`theme.config_mode`). Related correction: `theme.toml`'s
`min_version` is the author's declaration — what Hugo actually enforces is the
theme's own `hugo.toml` (`[module.hugoVersion] min`). Both carry 0.158.0 in
hugo-book v0.14.0; a hand-made theme fixture with only `theme.toml` is not
enforced by Hugo at all, which is why that test now pins the local runner.

## Hosting guarantees

### CI guard — `if [ -d <docs> ]`

The pipeline triggers on every push. Without the guard, deleting the docs
directory fails the build step (the directory the build `cd`s into is missing).
The guard makes the step a no-op, and the follow-up unconditional
`mkdir -p <docs>/public` guarantees the publish step always finds its
`deploy-dir`.

### Build from inside the docs directory

`hugo.toml` lives in the docs directory, which is the Hugo project root. Running
Hugo from the repository root picks up no config and produces an empty site, so
every pipeline invokes `(cd <docs> && hugo --minify)` and publishes
`<docs>/public`.
