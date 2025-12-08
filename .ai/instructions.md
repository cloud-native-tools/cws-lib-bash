# CWS-Lib-Bash Copilot 指南

本指南帮助 AI 助手快速理解和贡献 cws-lib-bash 项目。

## 项目结构
- bin/: 安装、环境、执行脚本 (cws_bash_setup, cws_bash_env, cws_bash_run)
- profile.d/: Shell 启动时加载的核心函数
- scripts/: 按域分组的功能模块（如 network.sh、docker.sh）

## 核心模式
- 函数命名: snake_case，domain_action (示例: network_test_connectivity)
- 参数校验: `local var=${1:-}`；`[ -z "$var" ] && log error ... && return`
- 依赖检查: `have docker` 或 `have kubectl`，失败报错并 `return`
- 日志: `log info|notice|warn|error|fatal`
- 错误码: `return ${RETURN_SUCCESS:-0}` / `${RETURN_FAILURE:-1}`
- 目录切换: `safe_pushd dir || return` ... `safe_popd || return`

## 开发与调试
- 初始化: `./bin/cws_bash_setup`
- 加载环境: `source ./bin/cws_bash_env`
- 执行函数: `./bin/cws_bash_run <function> [args]`
- 语法检查: `bash -n scripts/<file>.sh`
- 代码检查: VS Code 任务 “shellcheck: current file”`

## 集成与扩展
- 新模块: 在 `scripts/<domain>.sh` 添加函数，遵循核心模式
- 脚本入口: 所有命令通过 `cws_bash_run` 调用
- 平台兼容: 使用 `is_linux()` / `is_macos()` 处理差异

## 示例函数
```bash
function example_clone() {
	local dir=${1:-}
	local url=${2:-}
	[ -z "$dir" ] || [ -z "$url" ] && { log error "Usage: example_clone <dir> <url>"; return ${RETURN_FAILURE:-1}; }
	have git || { log error "git not found"; return ${RETURN_FAILURE:-1}; }
	git_clone_into "$dir" "$url"
	return ${RETURN_SUCCESS:-0}
}
```

如有遗漏或疑问，请反馈以完善本指南。
