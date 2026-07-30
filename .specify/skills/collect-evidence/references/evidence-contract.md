# Evidence Contract — findings.json 人读版

> 机器合同:`.specify/specs/034-evidence-infra/contracts/findings-contract.md`(C-F1…C-F14);本文为消费者速览。

## 存储布局

```text
.specify/memory/evidence/
├── index.json                       # 存储索引(store/updated/entries[])
└── ev-<YYYYMMDD>-<HHMMSS>-<slug>/   # 一次证据运行(不可变)
    ├── findings.json                # 证据合同(下述)
    ├── manifest.json                # 运行元数据(泳道状态+reason、引擎信息、digest)
    ├── lanes/<lane>.json            # 各执行泳道的原始 envelope(已脱敏)
    └── intervention.json            # (可选)消费层写入的干预台账
```

## findings.json 顶层字段(白名单,不多不少)

| 字段 | 含义 |
|------|------|
| `schemaVersion` | 固定 1 |
| `kind` | 固定 `"speckit.evidence-findings"` |
| `target` | 目标单元:`skill:<name>` / `/speckit.<cmd>` / `project` |
| `runId` | `ev-<date>-<time>-<slug>`,与目录名一致 |
| `window` | `{since, until}`(可空 = 全量) |
| `platforms` | 本次实际采集到数据的平台 |
| `lanes` | 五泳道状态:`available` / `partial` / `unavailable`(unavailable 的 reason 在 manifest) |
| `evidence` | 证据条目数组(可为空——空证据源合法,不编造) |
| `findingsDigest` | `sha256:<hex>`,对 evidence 数组计算,与 manifest 交叉一致 |

## 证据条目字段

| 字段 | 含义 |
|------|------|
| `id` | `ev-NNN`,运行内从 001 连续 |
| `lane` | `session` / `project` / `assets` / `runs` / `feedback` |
| `evidenceState` | 七态之一(语义见 evidence-discipline.md) |
| `summary` | 脱敏语义摘要(禁含原文 prompt/命令/私有绝对路径/密钥) |
| `evidenceRefs` | 不可逆哈希 或 仓库相对路径 |
| `signals` | 数值信号(计数只路由,不产生发现) |
| `privacyNote` | session 泳道必带(标注脱敏方式) |

## 合同红线

- **裁决字段禁令**:全文档递归不得出现 `severity` / `score(s)` / `aiFixPrompt` / `recommendation` / `supportTrack` / `priority`——严重度与建议属于消费层,不属于证据。
- **七态封闭**:evidenceState 只能取七态词汇,消费方不得裁剪或重定义语义。
- **隐私双闸**:引擎侧脱敏漏斗(privacy-safe-text / semantic-facets)+ Python 侧落盘前二次过滤(密钥模式、绝对路径掩码)。
- **打包排除**:`.specify/memory/evidence/` 不进入 feedback package zip。

## 五泳道

| 泳道 | 实现 | 内容 |
|------|------|------|
| session | Node 引擎 | 会话执行行为:Task Episode、返工/修正、工具失败 |
| project | Node 引擎 | 仓库结构/历史信号(+ 可选依赖治理) |
| assets | Node 引擎 | 已配置资产清单与 lint/inventory/integrity 三信封 |
| runs | 纯 Python | teams 运行工件:runs/ 报告、STATE.md Critique、run-log.jsonl |
| feedback | 纯 Python | feedback 条目;重复优化点带 `recurrence` 信号 |

无 Node 环境时前三泳道显式降级,后两泳道保底可用。
