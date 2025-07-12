# CWS-Lib-Bash Bash 函数库指导文档

## 项目概述

CWS-Lib-Bash 是一个用于云原生环境操作、系统管理和开发工作流的 Bash 工具函数库。该库提供了一套全面的工具函数，用于云原生环境中的常见操作，使日常运维和开发工作更加高效。

## 核心特性

- 按技术领域组织的模块化函数库设计
- 支持 Linux 和 macOS 系统的跨平台兼容性
- 统一的日志记录和错误处理机制
- 一致的命名规范和编码风格
- 自动化交互脚本支持
- 标准化的返回码和错误处理

## 项目结构

```
cws-lib-bash/
├── bin/              # 可执行脚本，用于设置和使用库
│   ├── cws_env      # 环境初始化脚本
│   ├── cws_run      # 命令执行入口脚本
│   └── cws_setup    # 安装设置脚本
// ...rest of code...
```

## 快速开始

### 安装步骤

1. **克隆仓库：**

   ```bash
   git clone https://github.com/cloud-native-tools/cws-lib-bash.git
   cd cws-lib-bash
   ```

2. **运行安装脚本：**
   ```bash
   ./bin/cws_setup
   ```

### 使用方法

1. **在当前 Shell 会话中加载库：**

   ```bash
   source ./bin/cws_env
   ```

2. **或使用 `cws_run` 执行命令：**
   ```bash
   ./bin/cws_run <function_name> [arguments...]
   ```

## 函数开发规范

### 命名规则

- 使用 `snake_case` 格式，带有域前缀（如：`git_clone`、`docker_build`）
- 函数格式：`function name() { ... }`
- 变量：函数内变量始终使用 `local` 声明
- 参数：验证空值，适当时提供默认值

### 错误处理

- 使用 `${RETURN_SUCCESS}` (0) 和 `${RETURN_FAILURE}` (1)
- 通过返回码传递函数执行结果
- 使用描述性错误消息

### 函数示例

```bash
function git_clone_into() {
  local dir=${1}
  local url=${2}
  if [ -z "${dir}" ] || [ -z "${url}" ]; then
    log error "Usage: git_clone_into <dir> <url>"
// ...rest of code...
```

## 引用行为

- `/scripts/` 目录中的文件会自动被引用
- 将逻辑封装在函数中
- 不要在函数外直接执行代码
- 使用模块化设计，按功能域组织函数

## 变量规范

- 使用小写字母和下划线
- 始终使用 `${variable}` 带大括号的格式
- 使用 `${var:-default}` 设置默认值
- 局部变量使用 `local` 声明

## 日志记录

使用 `log` 函数，支持以下级别：

- `log info` - 一般信息
- `log notice` - 注意事项
- `log warn` - 警告信息
- `log error` - 错误信息
- `log fatal` - 致命错误

示例：

```bash
log info "Starting deployment process"
log warn "Configuration file not found, using defaults"
log error "Failed to connect to database"
```

## 命令可用性检查

使用 `have` 函数进行工具可用性测试：

```bash
if ! have docker; then
  log error "Docker command not found"
  return ${RETURN_FAILURE}
fi

// ...rest of code...
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

### Kubernetes 操作

- `k8s_apply_manifest` - 应用 Kubernetes 清单
- `k8s_get_pods` - 获取 Pod 列表
- `k8s_wait_for_ready` - 等待资源就绪

### 网络工具

- `network_test_connectivity` - 测试网络连接
- `network_get_ip` - 获取 IP 地址
- `network_port_check` - 检查端口状态

# 测试单个函数
./bin/cws_run git_clone_into /tmp/test https://github.com/example/repo.git

# 检查返回码
echo $?
```

## 扩展开发

### 添加新函数

// ...rest of code...
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

  # Implementation here
  log info "Processing ${param}"
  return ${RETURN_SUCCESS:-0}
}
EOF
```

## 代码生成规范

- 参考项目目录中的 README.md 文件内容，以此了解项目的基本信息，如果项目根目录下存在 docs 目录，则参考其中的内容。
- 复杂任务先创建 TODO.md 文件列出计划和步骤，然后一步一步执行，每完成一项更新一次 TODO.md 文档中对应的记录，在任务结束之后再检查 TODO.md 中是否都完成。
// ...rest of code...