# CI platform templates — registry

Stage 3 (pages service) of `create-pages`. Stage 2 already made the docs
directory a Hugo project that builds to `<docs-dir>/public`; each
subdirectory here is one **hosting platform**, and
`scaffold-ci.sh --platform <name>` renders that platform's pipeline so the
platform publishes that build output.

Platform vocabulary: **aoneci** is the Alibaba-internal, GitLab-like hosting
platform (implemented). **gitlab** would mean the open-source GitLab project
and its hosting service — not usable here, and therefore not a platform in
this registry. **github** means GitHub Actions + GitHub Pages (`gh-pages`).
The `local` target needs no pipeline at all (`hugo serve`), so it has no
entry here.

## Platform registry

| Platform | Subdirectory | Rendered CI file | Status |
|----------|--------------|------------------|--------|
| aoneci | `aoneci/` | `.aoneci/deploy-pages.yaml` | implemented |
| github | `github/` | `.github/workflows/deploy-pages.yaml` | stub (structure only — see its README) |

## Extension contract (adding a new platform)

1. Create `<platform>/deploy-pages.yaml.tpl` using the shared placeholder
   tokens (`__SITE_NAME__`, `__BRANCH__`, `__IMAGE__`, `__DOCS_DIR__`) and the
   mandatory pipeline semantics (push trigger, docs-dir guarded build,
   unconditional `mkdir -p <docs>/public`, publish `<docs>/public`, build by
   running Hugo from inside the docs directory). Contract details:
   `github/README.md` doubles as the reference spec.
2. Register the platform's rendered-file path in `scaffold-ci.sh`
   (`ci_target_for_platform`).
3. Add a row to the registry table above.
4. Optional: a `<platform>/README.md` with platform-specific notes.

Platforms without a `.tpl` file write nothing: `scaffold-ci.sh` warns and
directs the user to author the CI file manually. The rendered CI file is the
only artifact this skill places outside the docs directory, because hosting
platforms discover pipelines at a fixed repository-root path.
