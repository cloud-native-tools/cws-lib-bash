function copilot_generate_instructions() {
  mkdir -pv docs
  if [ ! -f docs/instructions.md ]; then
    if [ -f config/instructions.md ]; then
      mv -fv config/instructions.md docs/instructions.md
    else
      cat <<EOF >docs/instructions.md
## 代码生成规范
- 参考目录中README.md文件内容
- 复杂任务先创建TODO.md列出步骤
- 大型文件生成后无需错误修复
- 文档使用中文，代码注释和日志使用英文
EOF
    fi
  fi

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
