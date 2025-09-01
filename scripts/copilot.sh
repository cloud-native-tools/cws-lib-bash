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

# 规则文件编写请遵循以下做法：
# 保持简洁明确：保持规则简洁、明确、具体。过长或含糊不清的规则可能会让模型感到困惑。
# 结构化表达：使用项目符号、编号列表和 Markdown 格式来格式化您的规则。与长段落相比，这些格式更易于模型理解。
# 提供示例：在规则中提供“好的代码示例”，这能极大地帮助模型理解您的意图。
# 迭代优化：创建规则后，通过实际的代码生成和问答来测试其效果，并根据模型的反馈不断迭代和优化您的规则描述。

  mkdir -p .ai
  if [ ! -f .ai/instructions.md ]; then
    cat <<'EOF' >.ai/instructions.md
# 项目开发指导文档

## 核心原则

### 1. 信息优先级
1. **项目根目录 README.md** - 了解项目基本信息、技术栈和使用方法
2. **docs/ 目录文档** - 详细的技术文档和开发指南  
3. **现有代码模式** - 保持与项目现有代码风格的一致性

### 2. 开发工作流
- **任务分解**: 复杂任务先创建 `TODO.md` 文件，列出具体步骤和计划
- **脚本优先**: 复杂的批量操作优先生成脚本文件再执行
- **小步迭代**: 功能开发采用小增量，频繁提交，及时反馈

## 编码规范

### 通用代码标准
- **命名规范**: 遵循项目现有的命名约定（camelCase、snake_case 或 PascalCase）
- **文件大小**: 单个代码文件超过 1500 行时考虑拆分重构
- **注释规范**: 复杂逻辑必须添加清晰的注释说明
- **编码一致性**: 保持与项目现有代码风格一致

### 错误处理标准
- **显式检查**: 对所有外部输入和依赖进行验证
- **适当传播**: 合理的错误信息传递和包装
- **日志记录**: 重要错误必须记录到日志系统
- **用户友好**: 面向用户的错误信息要清晰易懂

### 日志记录规范
- **级别使用**: ERROR（系统错误）、WARN（警告）、INFO（重要流程）、DEBUG（调试信息）
- **结构化**: 使用结构化日志格式，便于查询和分析
- **敏感信息**: 避免记录密码、令牌等敏感数据
- **上下文**: 提供足够的上下文信息便于问题定位

## 项目结构管理

### 目录组织原则
- **按功能模块**: 相关功能的文件组织在一起
- **分离关注点**: 配置、业务逻辑、工具函数分别存放
- **清晰层次**: 避免过深的目录嵌套（建议不超过 4 层）

### 配置管理
- **环境分离**: 开发、测试、生产环境配置分离
- **敏感信息**: 使用环境变量或密钥管理系统
- **默认值**: 为配置项提供合理的默认值
- **验证机制**: 启动时验证必要的配置项

## 测试策略

### 测试类型
- **单元测试**: 测试单个函数或类的功能
- **集成测试**: 测试模块间的交互
- **端到端测试**: 测试完整的用户场景
- **性能测试**: 对关键路径进行性能验证

### 测试要求
- **覆盖率**: 核心业务逻辑测试覆盖率应达到 80% 以上
- **边界条件**: 测试输入的边界值和异常情况
- **可维护性**: 测试代码要清晰易懂，便于维护
- **独立性**: 测试之间不应相互依赖

## 依赖管理

### 依赖选择原则
- **成熟稳定**: 优先选择维护活跃、社区成熟的库
- **轻量化**: 避免引入过重的依赖包
- **安全性**: 定期检查和更新依赖的安全漏洞
- **兼容性**: 确保依赖版本之间的兼容性

### 版本管理
- **锁定版本**: 使用 package-lock.json、poetry.lock 等锁定依赖版本
- **定期更新**: 建立依赖更新的定期检查机制
- **影响评估**: 更新前评估对现有功能的影响

## 代码质量保证

### 代码审查
- **功能正确性**: 验证代码是否实现了预期功能
- **性能影响**: 评估代码对系统性能的影响
- **安全性**: 检查潜在的安全漏洞
- **可维护性**: 确保代码易于理解和修改

### 自动化工具
- **代码格式化**: 使用 Prettier、Black 等工具统一代码格式
- **静态分析**: 使用 ESLint、Pylint 等工具检查代码质量
- **类型检查**: 对支持类型的语言启用类型检查
- **持续集成**: 配置 CI/CD 流水线自动化测试和部署

## 文档维护

### 文档类型
- **README.md**: 项目概述、安装和基本使用方法
- **API 文档**: 接口的详细说明和示例
- **开发文档**: 开发环境搭建和贡献指南
- **架构文档**: 系统设计和技术决策说明

### 文档标准
- **及时更新**: 代码变更时同步更新相关文档
- **示例丰富**: 提供充足的代码示例和使用场景
- **结构清晰**: 使用合理的标题层次和导航结构
- **多语言**: 根据项目需要提供中英文文档

## 语言使用规范

- **文档语言**: 中文（便于团队理解）
- **代码注释**: 英文（国际化标准）
- **日志信息**: 英文（便于系统集成）
- **变量命名**: 英文（编程通用标准）

## 版本控制

### 提交规范
- **原子提交**: 每次提交只包含一个逻辑变更
- **清晰信息**: 提交信息要准确描述变更内容
- **约定格式**: 使用 Conventional Commits 等标准格式

**提交信息示例**:
```
feat: add user authentication module
fix: resolve memory leak in data processing
docs: update API documentation for v2.0
refactor: optimize database query performance
test: add unit tests for user service
```

### 分支策略
- **main/master**: 稳定的生产代码
- **develop**: 集成开发分支
- **feature/***: 功能开发分支
- **hotfix/***: 紧急修复分支
- **release/***: 发布准备分支
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
