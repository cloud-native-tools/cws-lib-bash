# CWS-Lib-Bash Bash 函数库开发指南

## 项目概述

CWS-Lib-Bash 是一个用于云原生环境操作、系统管理和开发工作流的 Bash 工具函数库。该库提供了一套全面的工具函数，用于云原生环境中的常见操作，使日常运维和开发工作更加高效。

## 核心特性

- **模块化设计**：按技术领域组织的函数库
- **跨平台兼容**：支持 Linux 和 macOS 系统
- **统一日志记录**：标准化的日志和错误处理机制
- **一致的编码风格**：统一的命名规范和代码结构
- **自动化交互**：支持脚本化的交互操作

## 项目结构

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

## 快速开始

### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/cloud-native-tools/cws-lib-bash.git
cd cws-lib-bash

# 运行安装脚本
./bin/cws_setup
```

### 使用方法

```bash
# 在当前 Shell 会话中加载库
source ./bin/cws_env

# 或使用 cws_run 执行命令
./bin/cws_run <function_name> [arguments...]
```

## 函数开发规范

### 命名规则

- 使用 `snake_case` 格式，带有域前缀
- 函数格式：`function name() { ... }`
- 变量：函数内变量始终使用 `local` 声明
- 参数验证：检查空值，提供默认值

### 错误处理

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

### 日志记录

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

## 扩展开发

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

## 代码生成规范

- 参考项目 README.md 了解基本信息
- 复杂任务先创建 TODO.md 文件规划步骤
- 复杂文件操作优先使用脚本执行
- 文档使用中文，代码注释使用英文
- 代码文件超过 1000 行时进行拆分
