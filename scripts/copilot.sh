function copilot_generate_instructions() {
  mkdir -pv docs
  if [ ! -f docs/instructions.md ]; then
    if [ -f config/instructions.md ]; then
      mv -fv config/instructions.md docs/instructions.md
    else
      cat <<EOF >docs/instructions.md
## 代码生成
- 如果目录中包含README.md文件需要参考其内容
- 如果需要完成的动作较多，就先把需要做的动作写入一个TODO.md文件中,然后再进行代码生成
- 如果文件比较大，生成代码之后不需要进行错误修复
- 生成文档用中文，生成代码注释和日志用英文
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
