# CWS-Lib-Bash

CWS-Lib-Bash是一个用于云原生环境运维、系统管理和开发工作流的Bash工具库。它提供了一系列针对常见操作的实用函数，让日常运维和开发工作更加高效。

## 功能特点

- 模块化设计，按不同技术领域组织函数库
- 跨平台支持，兼容Linux和macOS系统
- 统一的日志和错误处理机制
- 统一的命名规范和代码风格

## 项目结构

```
.
├── bin/              # 可执行脚本，用于设置和使用库
├── expect/           # 自动化交互脚本
├── profile.d/        # shell初始化时加载的核心功能
└── scripts/          # 按技术领域组织的工具函数
```

## 快速开始

### 安装

1. 克隆仓库到本地：

```bash
git clone https://github.com/cloud-native-tools/cws-lib-bash.git
cd cws-lib-bash
```

2. 运行安装脚本：

```bash
./bin/cws_setup
```

### 使用方法

1. 在当前Shell会话中加载库：

```bash
source ./bin/cws_env
```

2. 或使用`cws_run`执行命令：

```bash
./bin/cws_run <function_name> [arguments...]
```

## 开发规范

- 函数命名使用snake_case并带有领域前缀
- 使用本地变量并正确引用(${variable})
- 使用标准的错误返回码(${RETURN_SUCCESS}和${RETURN_FAILURE})
- 使用日志函数(log info/notice/warn/error)记录重要信息

## 许可证

[MIT License](LICENSE)

## 贡献指南

欢迎提交问题报告和代码贡献。请确保遵循项目的代码风格和开发规范。

## 项目地址

https://github.com/cloud-native-tools/cws-lib-bash

