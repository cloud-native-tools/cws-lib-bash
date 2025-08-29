function copilot_generate_instructions() {
  # Create .copilotignore based on .gitignore
  if [ ! -f .copilotignore ]; then
    log info "Creating .copilotignore"

    # Start with .gitignore content if exists
    if [ -f .gitignore ]; then
      log info "Using .gitignore as base for .copilotignore"
      cat .gitignore >.copilotignore
    else
      log warn ".gitignore not found, creating basic .copilotignore"
      touch .copilotignore
    fi

    # Add additional patterns that should be ignored by Copilot
    cat <<EOF >>.copilotignore

# Additional patterns for Copilot indexing exclusion
.clinerules/
.github/
.lingma/
.trae/

EOF
  else
    log info ".copilotignore already exists, skipping"
  fi

# 为了帮助通义灵码有效地遵守您的规则，规则文件编写请遵循以下做法：
# 保持简洁明确：保持规则简洁、明确、具体。过长或含糊不清的规则可能会让通义灵码感到困惑。
# 结构化表达：使用项目符号、编号列表和 Markdown 格式来格式化您的规则。与长段落相比，这些格式更易于通义灵码理解。
# 提供示例：在规则中提供“好的代码示例”，这能极大地帮助模型理解您的意图。
# 迭代优化：创建规则后，通过实际的代码生成和问答来测试其效果，并根据模型的反馈不断迭代和优化您的规则描述。

  mkdir -p .ai
  if [ ! -f .ai/instructions.md ]; then
    cat <<EOF >.ai/instructions.md
# 项目开发指导文档

## 开发工作流

### 信息优先级
1. 项目根目录README.md文件内容，以此了解项目基本信息
2. docs/目录中的相关文档
3. 现有代码模式和结构

### 任务管理
- 复杂任务先创建TODO.md文件列出计划和步骤，然后一步一步执行，每完成一项更新TODO.md中对应的记录，任务结束后检查是否都完成
- 复杂文件操作先生成Python或Shell脚本，然后通过执行脚本来进行操作
- 开发模式：小迭代，及时提交

### 语言标准
- 文档使用中文
- 代码注释和日志使用英文
- 编程语言代码文件（*.go、*.java、*.py、*.ts、*.js、*.c、*.cpp、*.cs、*.php、*.rb、*.rs等）超过1500行时需要拆分以提高可维护性和可读性，数据文件（*.json、*.yaml、*.csv、*.xml等）不受此限制

## 设计原则

### 分层设计
- 应用层：处理用户交互
- 业务逻辑层：核心业务规则  
- 公共服务层：通用工具和服务
- 基础设施层：数据访问和外部集成

### API设计原则
- 在服务层封装分页
- 统一错误类型，包含上下文
- 验证外部服务响应的业务错误
- API包中的类型定义不应包含通信协议相关的请求或响应类型

## 编码标准

### 错误处理标准
- 显式错误检查
- 适当的错误传播
- 使用上下文包装错误信息
- 避免在库代码中使用panic

### 日志记录标准
- ERROR: 需要立即处理的系统错误
- WARN: 可能影响功能的警告信息
- INFO: 重要的业务流程信息
- DEBUG: 详细的调试信息

### 资源管理标准
- 立即设置清理机制
- 实现适当的关闭接口
- 使用上下文进行超时控制

## 质量保证

### 代码质量
- 遵循项目代码格式标准
- 优先使用强类型而非弱类型
- 谨慎使用高级语言特性

### 文档要求
- 每个公开接口有清晰说明
- 提供使用示例
- 维护更新日志

## 外部服务集成

### 通用原则
- 稳定的外部接口：屏蔽底层变化
- 封装服务细节：隐藏具体实现
- 统一错误处理：标准化错误类型
- 必须调试日志：便于问题排查

### 最佳实践
- 调用前后记录日志
- 避免日志中的敏感数据
- 一致的错误模式
- 性能感知的调试日志

## 版本控制

### 提交规范
- 小步快跑，及时提交
- 清晰的提交信息
- 相关变更一起提交

### 分支管理
- 功能开发使用特性分支
- 定期合并主分支变更
- 重要版本打标签
EOF
  fi

  mkdir -p .clinerules
  pushd .clinerules
  ln -sfv ../.ai/instructions.md project_rules.md
  popd

  mkdir -p .github
  pushd .github
  ln -sfv ../.ai/instructions.md copilot-instructions.md
  popd

  mkdir -p .lingma/rules
  pushd .lingma/rules
  ln -sfv ../../.ai/instructions.md project_rule.md
  popd

  mkdir -p .trae/rules
  pushd .trae/rules
  ln -sfv ../../.ai/instructions.md project_rules.md
  popd

  ln -sf .ai/instructions.md QWEN.md
  ln -sf .ai/instructions.md CLAUDE.md
  ln -sf .ai/instructions.md IFLOW.md
}
