# Ignore Patterns Reference

Technology-specific ignore file patterns for project setup verification during `/speckit.implement`.

## Detection & Creation Logic

- Check `git rev-parse --git-dir 2>/dev/null` → create/verify `.gitignore`
- If git repo, verify commit identity: `git config --get user.email` / `git config --get user.name`. If empty, HALT and prompt user.
- Check Dockerfile* exists or Docker in plan.md → `.dockerignore`
- Check .eslintrc* exists → `.eslintignore`
- Check eslint.config.* exists → ensure config's `ignores` entries cover required patterns
- Check .prettierrc* exists → `.prettierignore`
- Check .npmrc or package.json → `.npmignore` (if publishing)
- Check terraform files (*.tf) → `.terraformignore`
- Check helm charts → `.helmignore`

**If ignore file exists**: Verify essential patterns, append missing critical ones only.
**If missing**: Create with full pattern set for detected technology.

## Common Patterns by Technology

### Node.js / JavaScript / TypeScript
`node_modules/`, `dist/`, `build/`, `*.log`, `.env*`

### Python
`__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `dist/`, `*.egg-info/`

### Java
`target/`, `*.class`, `*.jar`, `.gradle/`, `build/`

### C# / .NET
`bin/`, `obj/`, `*.user`, `*.suo`, `packages/`

### Go
`*.exe`, `*.test`, `vendor/`, `*.out`

### Ruby
`.bundle/`, `log/`, `tmp/`, `*.gem`, `vendor/bundle/`

### PHP
`vendor/`, `*.log`, `*.cache`, `*.env`

### Rust
`target/`, `debug/`, `release/`, `*.rs.bk`, `*.rlib`, `*.prof*`, `.idea/`, `*.log`, `.env*`

### Kotlin
`build/`, `out/`, `.gradle/`, `.idea/`, `*.class`, `*.jar`, `*.iml`, `*.log`, `.env*`

### C++
`build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.so`, `*.a`, `*.exe`, `*.dll`, `.idea/`, `*.log`, `.env*`

### C
`build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.a`, `*.so`, `*.exe`, `Makefile`, `config.log`, `.idea/`, `*.log`, `.env*`

### Swift
`.build/`, `DerivedData/`, `*.swiftpm/`, `Packages/`

### R
`.Rproj.user/`, `.Rhistory`, `.RData`, `.Ruserdata`, `*.Rproj`, `packrat/`, `renv/`

### Universal
`.DS_Store`, `Thumbs.db`, `*.tmp`, `*.swp`, `.vscode/`, `.idea/`

## Tool-Specific Patterns

### Docker
`node_modules/`, `.git/`, `Dockerfile*`, `.dockerignore`, `*.log*`, `.env*`, `coverage/`

### ESLint
`node_modules/`, `dist/`, `build/`, `coverage/`, `*.min.js`

### Prettier
`node_modules/`, `dist/`, `build/`, `coverage/`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`

### Terraform
`.terraform/`, `*.tfstate*`, `*.tfvars`, `.terraform.lock.hcl`

### Kubernetes / k8s
`*.secret.yaml`, `secrets/`, `.kube/`, `kubeconfig*`, `*.key`, `*.crt`
