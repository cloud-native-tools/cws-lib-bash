# CWS-Lib-Bash 指南

一个为云原生操作提供实用功能的 Bash 库。

## 结构

- `/bin/`: 可执行脚本
- `/expect/`: Expect 脚本
- `/profile.d/`: 核心 shell 初始化
- `/scripts/`: 领域特定工具

## 函数风格

- 使用带领域前缀的 `snake_case` 名称（例如 `git_clone`）
- 格式：`function name() { ... }`
- 必须进行参数验证
- 每个函数单一职责

示例：
```bash
function git_clone_into() {
  local dir=${1}
  local url=${2}
  if [ -z "${dir}" ] || [ -z "${url}" ]; then
    log error "Usage: git_clone_into <dir> <url>"
    return ${RETURN_FAILURE:-1}
  fi
  # 实现
}
```

## 变量

- 使用小写加下划线
- 函数中的所有变量使用 `local` 声明
- 使用带花括号的变量引用 `${variable}`
- 可选参数默认值：`${var:-default}`

## 错误处理

- 使用 `${RETURN_SUCCESS}` (0) 和 `${RETURN_FAILURE}` (1)
- 验证必需参数
- 使用 `|| return ${RETURN_FAILURE}` 模式

## 日志记录

- 使用带级别的 `log`：`info`, `notice`, `warn`, `error`, `fatal`
- 包含描述性消息
- 错误消息中包含使用方法

## 跨平台

考虑 macOS 和 Linux 的差异：
```bash
if command -v nproc >/dev/null 2>&1; then
  nproc  # Linux
elif command -v sysctl >/dev/null 2>&1 && [[ "$(uname)" == "Darwin" ]]; then
  sysctl -n hw.ncpu  # macOS
else
  echo "1"  # 默认值
fi
```

## 添加函数时

1. 放在适当的领域文件中
2. 遵循领域前缀约定
3. 使用 `function name() { ... }` 格式
4. 使用 `local` 声明变量
5. 验证参数
6. 提供默认值
7. 正确处理错误
8. 考虑跨平台兼容性
9. 记录目的和用法
10. 处理边缘情况