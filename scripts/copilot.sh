function copilot_generate_instructions() {
  mkdir -pv docs
  touch docs/instructions.md

  mkdir -p .clinerules
  pushd .clinerules
  ln -sfv ../docs/instructions.md project_rules.md
  popd

  mkdir -p .github
  pushd .github
  ln -sfv ../docs/instructions.md copilot-instructions.md
  popd

  mkdir -p .lingma/rules
  pushd .lingma/rules
  ln -sfv ../../docs/instructions.md project_rule.md
  popd

  mkdir -p .trae/rules
  pushd .trae/rules
  ln -sfv ../../docs/instructions.md project_rules.md
  popd
}
