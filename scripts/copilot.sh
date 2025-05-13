function copilot_generate_instructions() {
  mkdir -p config
  touch config/instructions.md

  mkdir -p .clinerules
  pushd .clinerules
  ln -sf ../config/instructions.md project_rules.md
  popd

  mkdir -p .github
  pushd .github
  ln -sf ../config/instructions.md copilot-instructions.md
  popd

  mkdir -p .lingma/rules
  pushd .lingma/rules
  ln -sf ../../config/instructions.md project_rule.md
  popd

  mkdir -p .trae/rules
  pushd .trae/rules
  ln -sf ../../config/instructions.md project_rules.md
  popd
}
