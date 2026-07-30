---
name: collect-evidence
description: Public evidence-collection orchestration skill (consumer-neutral evidence layer). Runs the deterministic evidence engine (evidence-utils.py) to gather normalized findings.json evidence across five lanes (session/project/assets via Node engine; runs/feedback native Python) for a target unit, presents capability tables and evidenceState distributions, and declares observation boundaries. Never interprets evidence or emits improvement suggestions. Use when the user mentions ["collect evidence", "evidence collection", "采集证据", "证据采集", "findings.json", "证据泳道", "evidence lanes", "doctor 能力表"]
skill_id: "<SKILL:.specify/skills/collect-evidence/SKILL.md>"
---

# collect-evidence

## Goal

为任意目标单元(技能/命令/整仓)执行一次**证据采集编排**,产出统一规范化的 `findings.json` 证据(七态 evidenceState、五泳道、脱敏),并如实申明观察边界。本技能是公共证据层的对话入口:**只采集、只呈现、只申明边界——不解读证据、不提优化建议**(证据层中立红线)。

## Path Conventions

- 引擎:`.specify/scripts/python/evidence-utils.py`(镜像 `scripts/python/`)
- 采集子集:`scripts/js/better-harness/`(镜像 `.specify/scripts/js/better-harness/`,溯源见其 `UPSTREAM.md`)
- 证据存储:`.specify/memory/evidence/<run-id>/{findings.json,manifest.json,lanes/}`+ `index.json`
- 消费约定(供 improve-* 等引用,本技能不执行):`.specify/shared/workflow/evidence-step.md`

## Workflow

### 1. 范围解析

从用户输入解析:

- **目标单元**(必填):`skill:<name>` / `/speckit.<cmd>` / `project`(整仓;缺省值)
- **泳道**:`session,project,assets,runs,feedback` 的子集或 `all`(缺省 all)
- **时间窗**:`--since/--until`(ISO 8601,可缺省)
- **深度**:`quick|normal`(缺省 normal;normal 含依赖治理信号)
- **平台**:`qoder|codex|claude|...`(缺省 qoder;影响 session/assets 泳道)

### 2. doctor — 能力表

```bash
python3 .specify/scripts/python/evidence-utils.py --action doctor
```

向用户呈现:Node 可用性与版本符合性(`satisfies` 为 false 时如实提示但不阻断)、引擎子集在位性(含上游基线 commit)、八工具本地会话落盘探测结果、五泳道可用性。探测不到的能力如实呈现 `not-detected` / `unavailable`,不推断、不虚构。

### 3. collect — 采集与呈现

```bash
python3 .specify/scripts/python/evidence-utils.py --action collect \
  --target <unit-id> --lanes <lanes> [--since ... --until ...] [--depth ...] [--platform ...]
```

呈现采集结果:run 目录路径、各泳道状态(available/partial/unavailable)、证据条数、findingsDigest,以及**按 evidenceState 分布的摘要**(七态各多少条)。单泳道失败是显式降级而非错误——manifest 中带 reason,照常继续。

复用场景:目标单元 7 天内已有证据时可先 `--action latest`;返回 `stale: true` 时必须向用户转述超龄警告,由用户决定复用或重采。

### 4. 边界申明

在输出结尾**如实列出**:

- 全部 `Unobserved` 证据项(未观察 ≠ 不存在;禁止推断);
- 全部 `unavailable`/`partial` 泳道及其 reason;
- 本次未覆盖的平台(doctor 探测 not-detected 的工具)。

红线:本技能的全部输出不得含解读性表述(缺陷判定、修复建议、等级评判)。证据如何消费由调用方(如 improve-* 技能按 evidence-step.md)决定。

## Resources

- `references/evidence-contract.md` — findings.json 证据合同人读版(字段、词汇、红线)
- `references/evidence-discipline.md` — 四条证据纪律 + evidenceState 七态定义(全部消费方共享的语义源)

## Dependencies

- Python 3.8+(引擎 stdlib-only,零第三方依赖)
- Node.js ≥22.20.0(仅 session/project/assets 三泳道;缺失时该三泳道显式降级,runs/feedback 泳道仍可用)

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, perform the agent self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. Gate on qualification & completion; skip trivial/no-op runs.
2. Reflect without user input; produce a short review plus ≥1 concrete optimization point, or exactly `No significant optimization points identified this run.`
3. Scope guard: `scope: local`, this skill only.
4. Dedup via stable `run_id`.
5. Persist:

   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "skill:collect-evidence" --unit-type skill \
     --run-id "<stable-run-id>" \
     --review "<review prose>" --points-file "<points file>"
   ```

6. If `should_prompt` is true, surface the consolidated submission prompt; below threshold, do not prompt.

Abort/partial rule: if the run failed before wrap-up, skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
