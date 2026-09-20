# Verification — create-pages

One section per stage. Run the stage you touched, plus stage 2 whenever
rendering assets changed. Substitute `<docs>` for the docs directory (default
`docs`) and `<image>` for the `--image` value chosen at stage 3 (the aoneci
default image only pulls inside that environment).

## Stage 1 — 本地文档库 containment

```bash
find <docs> -name '*.md' | wc -l          # > 0; the library has content
git status --short | grep -v '^.. <docs>/' # only the platform CI file may appear
```

Expected: every path this skill wrote is under `<docs>/`, with exactly one
allowed exception — the rendered CI file (`.aoneci/deploy-pages.yaml` or
`.github/workflows/deploy-pages.yaml`). Any other root-level path is a
containment violation: report it and remove it.

## Stage 2 — Hugo 渲染

```bash
python3 "${SKILL_HOME}/scripts/scaffold-hugo.py" --action theme --root .           # mode & theme state
python3 "${SKILL_HOME}/scripts/scaffold-hugo.py" --action image --root .           # image a build will use
python3 "${SKILL_HOME}/scripts/scaffold-hugo.py" --action check --root .           # drift, no writes
python3 "${SKILL_HOME}/scripts/scaffold-hugo.py" --action scaffold --root . --site-title "<t>"
python3 "${SKILL_HOME}/scripts/scaffold-hugo.py" --action scaffold --root . # idempotence: all `unchanged`
python3 "${SKILL_HOME}/scripts/scaffold-hugo.py" --action build --root .    # builds in the CI image
```

Expected:

- The build reports `runner: docker`, the CI `image`, and the `hugo_version` **of the
  image** — compare it against `hugo version` on the host: they usually differ, and the
  image's is the one that matters. A `runner: local` result with a `warning` means the
  docker path was unavailable; treat that site as unverified for CI.
- `Pages > 0` and **no ERROR lines**; page count ≈ number of `.md` documents
  plus section pages (book mode adds one per generated section index).
- The second `scaffold` run reports every file `unchanged` and writes nothing
  (zero churn). Files you edited locally are reported `kept`.
- Exactly one deprecation warning is currently expected —
  `module.mounts.excludeFiles` (see design-rationale). Any *other* deprecation
  or warning is a finding — with one qualifier: `BookPortableLinks = "warning"`
  (not the default) reports every link that leaves the docs directory, which is
  legitimate in this repository.
- `--runner local` on a Hugo older than the theme's floor must refuse with
  `hugo-older-than-theme` and `clean: true` — that is an environment gap, and the
  default runner is the fix.

Output checks:

```bash
find <docs>/public -name '*.html' | wc -l                            # > 0
test -f <docs>/public/hugo.toml && echo BUG || echo OK               # config must not be published
grep -o '<title>[^<]*</title>' <docs>/public/<some-page>/index.html  # non-empty on both sides of '·'
grep -c '<a href="[^"]*"></a>' <docs>/public/index.html || true      # 0; no blank link text
ls <docs>/public | grep -E '^(categories|tags)$' && echo BUG || echo OK
test -d dist && echo BUG || echo OK                                  # no repository-root output
find <docs>/public -name '*.md' | wc -l                              # 0; no raw Markdown published
```

A blank `<title>` (`· Site`) or blank link text means the title fallback partial
is missing or not wired into the layout — that regression is what
`partials/title.html` exists to prevent.

### Navigation completion (book mode)

The report is the first check — `nav.sections` must list every Markdown-bearing
directory (nested ones included), and `nav.generated_indexes` every one of those
without an `index.md`:

```bash
python3 "${SKILL_HOME}/scripts/scaffold-hugo.py" --action check --root . \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['theme']['mode'], d['nav'])"
```

Then assert the rendered sidebar (run inside the CI image if the local Hugo is
too old). Everything below was verified against hugo-book `v0.14.0`:

```bash
python3 - <<'PY'
import html, re
home = open("<docs>/public/index.html", encoding="utf-8").read()
nav = home[home.find("book-menu"):home.find("book-page")]
labels = [html.unescape(t.strip()) for t in re.findall(r">\s*([^<>]{2,60}?)\s*<", nav) if t.strip()]
print("labels:", labels)
assert not re.findall(r"<a (?![^>]*href)[^>]*>", nav), "dead sidebar entry: section page has no content"
assert not [l for l in labels if l.endswith("#")], "heading-anchor artifact in a label"
body = home[home.find("book-article"):]
assert re.findall(r'href="?\.?/?[a-z]', body), "home page is blank: no generated child index"
PY
```

Expected: labels are document H1s (or generated section labels), the first
entries follow the reading order (`concepts` … not `archive`), nested directories
appear as their own groups, and no entry is a dead link. A section page of an
index-less directory (`<docs>/public/<nested>/index.html`) must exist and list
its children.

## Stage 3 — Pages 服务

### local

```bash
IMAGE=$(python3 "${SKILL_HOME}/scripts/scaffold-hugo.py" --action image --root . \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["image"])')
docker run -d --name hugo-serve -p 1313:1313 -v "$PWD:/workspace" -w "/workspace/<docs>" \
  "$IMAGE" hugo server --bind 0.0.0.0
curl -sf http://localhost:1313/ > /dev/null && echo OK
docker rm -f hugo-serve
```

Expected: HTTP 200 on the home page and live reload on edit — in the same Hugo CI
uses. Nothing is written to disk by this target. A host `hugo server` is the
fallback; note in the report which one served.

### Hosting platform (aoneci / github)

```bash
bash "${SKILL_HOME}/scripts/scaffold-ci.sh" --site-name <name> --platform aoneci
python3 -c "import yaml;d=yaml.safe_load(open('.aoneci/deploy-pages.yaml'));print(d['jobs']['deploy']['steps'][2]['inputs']['deploy-dir'])"
```

Expected: JSON reports the CI file `created` (or `skipped` when it already
exists — never silently overwritten), the file parses as YAML, and `deploy-dir`
is `<docs>/public/`. A platform without a template (`github` today) must report a
warning and create nothing.

Container build test — proves the pipeline's build step works in the CI image. Stage
2's `--action build` already runs in that image, so this narrows to the pipeline's own
guard-and-publish wrapper:

```bash
docker run --rm -v "$PWD:/workspace" -w /workspace <image> \
  sh -c 'if [ -d <docs> ]; then (cd <docs> && hugo --minify); fi; mkdir -p <docs>/public; ls <docs>/public | head'
```

**Fallback** for sandbox docker daemons where host mounts are invisible inside
containers (observed in this environment):

```bash
docker run -d --name hugo-verify <image> sleep 600
tar czf /tmp/site.tar.gz <docs>
docker cp /tmp/site.tar.gz hugo-verify:/tmp/
docker exec hugo-verify sh -c 'mkdir -p /w && tar xzf /tmp/site.tar.gz -C /w && cd /w/<docs> && hugo --minify'
```

### No-docs guard test

Simulate the CI run block exactly (never `bash` the YAML file itself — it is not
executable):

```bash
mv <docs> <docs>.bak
if [ -d <docs> ]; then (cd <docs> && hugo --minify); fi
mkdir -p <docs>/public
ls <docs>/public          # expect: empty directory, exit 0
rm -rf <docs> && mv <docs>.bak <docs>
```

Expected: no build attempt, an empty publish directory created, exit code 0.

## Cleanup

```bash
docker rm -f hugo-verify        # if the fallback container was used
rm -rf <docs>/public            # build artifact; gitignored by the scaffold
```

The vendored theme (`<docs>/themes/book`) is **not** a verification artifact: it is
required at build time and must stay committed.
