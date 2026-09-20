# Platform: github (structural stub — no implementation yet)

This directory reserves the structure for GitHub-hosted deployments
(GitHub Actions + GitHub Pages / `gh-pages`). Only the structure exists; the
concrete template is intentionally NOT implemented, because the action
versions it needs must be checked against current GitHub documentation
before they are written down. When implementing, follow the contract below
so `scaffold-ci.sh` can pick it up without code changes.

`scaffold-ci.sh --platform github` therefore writes nothing today and warns
that the workflow must be authored manually per this file.

## Expected template file

- Name: `deploy-pages.yaml.tpl` (`scaffold-ci.sh` looks for exactly this name).
- Rendered to: `.github/workflows/deploy-pages.yaml` (already registered in
  `ci_target_for_platform`, so no script change is needed).

## Placeholder contract (shared by every platform template)

`scaffold-ci.sh` substitutes these tokens before writing:

| Placeholder | Meaning |
|-------------|---------|
| `__SITE_NAME__` | Deploy site name (`--site-name`) |
| `__BRANCH__` | Production branch (`--branch`) |
| `__IMAGE__` | Hugo build image (`--image`) |
| `__DOCS_DIR__` | Docs directory (`--docs-dir`) |

`__IMAGE__` is a container image and only applies to platforms that run the
job in one; a GitHub Actions workflow installs Hugo with an action step
instead and may leave the token unused.

## Mandatory pipeline semantics (mirror the aoneci template)

1. Trigger on push to the repository.
2. Build step guarded by a docs-directory existence check
   (`if [ -d __DOCS_DIR__ ]`), followed by an unconditional
   `mkdir -p __DOCS_DIR__/public` so the publish step always finds its
   artifact directory.
3. Build by running Hugo **from inside the docs directory** — that directory
   is the Hugo project root (`hugo.toml` lives there), so the invocation is
   `(cd __DOCS_DIR__ && hugo --minify)`. Never render from the repository
   root and never stage a copy of the Markdown tree.
4. Publish `__DOCS_DIR__/public/` to the platform's pages service, pinned to
   `__BRANCH__` for production. Pass `--baseURL` when the site is served from
   a sub-path.
5. Write nothing outside the docs directory except this workflow file itself.

A starting point for the build/publish steps (Hugo install action, artifact
upload, `baseURL` handling) is kept as guidance in
`../../references/hugo-site.md` § CI guidance — verify each action version
against current GitHub documentation before turning it into a template.
