function copilot_generate_instructions() {
  local lang=${1:-cn}

  if [ "${lang}" != "en" ] && [ "${lang}" != "cn" ]; then
    log error "lang must be 'en' or 'cn'"
    return 1
  fi

  touch .copilotignore

  mkdir -pv docs
  if [ ! -f docs/instructions.cn.md ]; then
    cat <<EOF >docs/instructions.cn.md
## 代码生成规范
- 参考目录中README.md文件内容，如果存在docs目录参考其中的内容
- 复杂任务先创建TODO.md列出步骤，在任务结束之后再检查TODO.md中是否都完成
- 文档使用中文，代码注释和日志使用英文
EOF
  fi
  if [ ! -f docs/instructions.en.md ]; then
    cat <<EOF >docs/instructions.en.md
## Code Generation Guidelines
- Refer to the contents of the README.md file in the directory, if there is a docs directory, refer to the contents of the file in the docs directory
- For complex tasks, create a TODO.md file to list the steps first, and then check whether all the steps in TODO.md are completed after the task is finished
- Documentation is in Chinese, code comments and logs are in English
EOF
  fi

  mkdir -p .clinerules
  pushd .clinerules
  ln -sfv ../docs/instructions.${lang}.md project_rules.md
  popd

  mkdir -p .github
  pushd .github
  ln -sfv ../docs/instructions.${lang}.md copilot-instructions.md
  popd

  mkdir -p .lingma/rules
  pushd .lingma/rules
  ln -sfv ../../docs/instructions.${lang}.md project_rule.md
  popd

  mkdir -p .trae/rules
  pushd .trae/rules
  ln -sfv ../../docs/instructions.${lang}.md project_rules.md
  popd
}
