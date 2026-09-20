# 意图：装配与配置（agent setup）

用统一环境变量配置各 Agent CLI（收编自 agent-cli-setup）。

## 统一环境变量模型（推荐）

| 变量 | 必填 | 规则 |
|------|------|------|
| `AGENT_API_KEY` | 是 | 非空 |
| `AGENT_MODEL` | 是 | 非空 |
| `AGENT_BASE_URL` | 是 | `http(s)://` 开头，OpenAI 兼容端点 |
| `AGENT_ANTHROPIC_BASE_URL` | 条件 | 显式指定 `claude` 时必填 |

三步流程（详细规则与逐工具映射见 [../setup/unified-variables.md](../setup/unified-variables.md)）：

```bash
source ${SKILL_HOME}/scripts/config-agent.sh
config_agent_env_validate --all     # 1. 校验（不落盘）
config_agent_env_apply --all        # 2+3. 二次赋值 + 持久化各工具配置
config_agent_env_apply opencode     # 单工具
```

保证：fail-fast 无部分写入；幂等；非破坏（保留无关配置键）；输出无秘密。

## 逐工具持久化目标

| 工具 | 协议 | 配置文件 |
|------|------|----------|
| `claude` | anthropic | `~/.claude/settings.json` |
| `codex` | openai | `~/.codex/config.toml`（+ `auth.json` 存 key） |
| `qoder` | openai | `~/.qoder/config.json` |
| `opencode` | openai | `~/.config/opencode/config.json` |

> GitHub Copilot / Hermes（OAuth 订阅制）不在统一环境变量流程内。

## Legacy 四元组流程

`(tool, model, provider_url, provider_key)` 抽象与安装/启动助手仍在
`config-agent.sh` 中提供；支持矩阵见 [../setup/supported-tuples.md](../setup/supported-tuples.md)、
权限模式见 [../setup/permission-modes.md](../setup/permission-modes.md)、
调用示例见 [../setup/usage-examples.md](../setup/usage-examples.md)。
