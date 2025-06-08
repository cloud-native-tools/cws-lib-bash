function copilot_generate_instructions() {
  local lang=${1:-cn}

  if [ "${lang}" != "en" ] && [ "${lang}" != "cn" ]; then
    log error "lang must be 'en' or 'cn'"
    return 1
  fi

  # Create .copilotignore based on .gitignore
  if [ -f .gitignore ]; then
    log info "Creating .copilotignore based on .gitignore"
    cat .gitignore >.copilotignore

    # Add additional patterns that should be ignored by Copilot but not git
    cat <<EOF >>.copilotignore

# Additional patterns for Copilot indexing exclusion
*.log
*.tmp
.DS_Store
Thumbs.db
.vscode/settings.json
.idea/
*.swp
*.swo
*~
.cache/
node_modules/
target/
build/
dist/
*.class
*.jar
*.war
*.ear
EOF
  else
    log warn ".gitignore not found, creating basic .copilotignore"
    cat <<EOF >.copilotignore
# Basic patterns for Copilot indexing exclusion
*.log
*.tmp
.DS_Store
Thumbs.db
.vscode/settings.json
.idea/
*.swp
*.swo
*~
.cache/
node_modules/
target/
build/
dist/
*.class
*.jar
*.war
*.ear
EOF
  fi

  mkdir -pv docs
  if [ ! -f docs/instructions.cn.md ]; then
    cat <<EOF >docs/instructions.cn.md
## 代码生成规范
- 参考项目目录中的README.md文件内容，以此了解项目的基本信息，如果项目根目录下存在docs目录，则参考其中的内容。
- 复杂任务先创建TODO.md文件列出计划和步骤，然后一步一步执行，每完成一项更新一次TODO.md文档中对应的记录，在任务结束之后再检查TODO.md中是否都完成。
- 在执行复杂的文件操作时，先生成一个python或者shell脚本，然后通过执行脚本来进行操作。
- 生成文档时使用中文，生成代码中的注释和日志使用英文。
EOF
  fi
  if [ ! -f docs/instructions.en.md ]; then
    cat <<EOF >docs/instructions.en.md
## Code Generation Guidelines
- Refer to the contents of the README.md file in the project directory to understand the basic information of the project. If there is a docs directory in the project root directory, refer to the contents within it.
- For complex tasks, create a TODO.md file first to list the plan and steps, then execute step by step. Update the corresponding records in the TODO.md document each time a step is completed, and check whether all items in TODO.md are completed after the task is finished.
- For complex file operations, first generate a Python or shell script, then perform the operations by executing the script.
- Generate documentation in English, and use English for code comments and logs.
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
