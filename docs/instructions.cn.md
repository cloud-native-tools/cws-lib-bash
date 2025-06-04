# CWS-Lib-Bash 指导规范

## 代码生成规范

- 参考项目目录中的 README.md 文件内容，以此了解项目的基本信息，如果项目根目录下存在 docs 目录，则参考其中的内容。
- 复杂任务先创建 TODO.md 文件列出计划和步骤，然后一步一步执行，每完成一项更新一次 TODO.md 文档中对应的记录，在任务结束之后再检查 TODO.md 中是否都完成。
- 生成文档时使用中文，生成代码中的注释和日志使用英文。

## 函数规范

- **命名规则**: 使用 `snake_case` 格式，带有域前缀（如：`git_clone`）
- **格式**: `function name() { ... }`
- **变量**: 函数内变量始终使用 `local` 声明
- **参数**: 验证空值，适当时提供默认值
- **错误处理**: 使用 `${RETURN_SUCCESS}` (0) 和 `${RETURN_FAILURE}` (1)

## 函数示例

```bash
function git_clone_into() {
  local dir=${1}
  local url=${2}
  if [ -z "${dir}" ] || [ -z "${url}" ]; then
    log error "Usage: git_clone_into <dir> <url>"
    return ${RETURN_FAILURE:-1}
  fi
  # Implementation
}
```

## 引用行为

- `/scripts/` 目录中的文件会自动被引用
- 将逻辑封装在函数中
- 不要在函数外直接执行代码

## 变量规范

- 使用小写字母和下划线
- 始终使用 `${variable}` 带大括号的格式
- 使用 `${var:-default}` 设置默认值

## 日志记录

- 使用 `log` 函数，支持级别：`info`、`notice`、`warn`、`error`、`fatal`
- 错误信息中包含描述性消息和使用方法

## 命令可用性检查

- 使用 `have` 函数进行测试：

```bash
if ! have expect; then
  log error "expect command not found"
  return ${RETURN_FAILURE}
fi
```
