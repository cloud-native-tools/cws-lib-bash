# CWS-Lib-Bash 项目开发指导文档

## 项目概述

CWS-Lib-Bash 是一个用于云原生环境操作、系统管理和开发工作流的 Bash 工具函数库。该库提供了一套全面的工具函数，用于云原生环境中的常见操作，使日常运维和开发工作更加高效。

### 核心特性

- **模块化设计**：按技术领域组织的函数库
- **跨平台兼容**：支持 Linux 和 macOS 系统
- **统一日志记录**：标准化的日志和错误处理机制
- **一致的编码风格**：统一的命名规范和代码结构
- **自动化交互**：支持脚本化的交互操作

### 项目结构

```
cws-lib-bash/
├── bin/              # 可执行脚本
│   ├── cws_env      # 环境初始化脚本
│   ├── cws_run      # 命令执行入口
│   └── cws_setup    # 安装设置脚本
├── expect/          # 自动化交互脚本
├── profile.d/       # Shell 初始化时加载的核心功能
└── scripts/         # 按技术领域组织的工具函数
```

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
- Bash 脚本超过 1000 行时进行拆分

## Bash 函数开发规范

### 命名规则
- 使用 `snake_case` 格式，带有域前缀
- 函数格式：`function name() { ... }`
- 变量：函数内变量始终使用 `local` 声明
- 参数验证：检查空值，提供默认值

### Bash 错误处理规范
```bash
# 使用标准返回码
return ${RETURN_SUCCESS:-0}  # 成功
return ${RETURN_FAILURE:-1}  # 失败

# 示例函数
function git_clone_into() {
  local dir=${1}
  local url=${2}
  if [ -z "${dir}" ] || [ -z "${url}" ]; then
    log error "Usage: git_clone_into <dir> <url>"
    return ${RETURN_FAILURE:-1}
  fi
  # 实现逻辑
}
```

### Bash 日志记录规范
```bash
# 支持的日志级别
log info "一般信息"
log notice "注意事项"
log warn "警告信息"
log error "错误信息"
log fatal "致命错误"
```

### 工具可用性检查
```bash
# 检查命令是否可用
if ! have docker; then
  log error "Docker command not found"
  return ${RETURN_FAILURE:-1}
fi
```

## 常用功能模块

### Git 操作
- `git_clone_into` - 克隆仓库到指定目录
- `git_current_branch` - 获取当前分支名称
- `git_is_clean` - 检查工作目录是否干净

### Docker 操作
- `docker_build_image` - 构建 Docker 镜像
- `docker_run_container` - 运行容器
- `docker_cleanup` - 清理未使用的资源

### 网络工具
- `network_test_connectivity` - 测试网络连接
- `network_get_ip` - 获取 IP 地址
- `network_port_check` - 检查端口状态

## 扩展开发指南

### 添加新功能模块
```bash
# 创建新的功能模块
mkdir scripts/mymodule

# 添加函数文件
cat > scripts/mymodule/functions.sh << 'EOF'
#!/bin/bash

function mymodule_do_something() {
  local param=${1}
  if [ -z "${param}" ]; then
    log error "Usage: mymodule_do_something <param>"
    return ${RETURN_FAILURE:-1}
  fi

  log info "Processing ${param}"
  return ${RETURN_SUCCESS:-0}
}
EOF
```

### 使用示例
```bash
# 测试单个函数
./bin/cws_run git_clone_into /tmp/test https://github.com/example/repo.git

# 检查返回码
echo $?
```

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
