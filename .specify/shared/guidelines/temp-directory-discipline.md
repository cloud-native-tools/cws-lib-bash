# Temporary Directory Discipline(临时目录纪律)

Agent 创建的临时目录的唯一真源。规范:**临时目录 MUST 落在受制裁的根下,且在首次写入前 MUST 已被 `.gitignore` 匹配;MUST NOT 使用裸系统临时目录或 ad-hoc 目录。**

本文件由指令文件的 `## Temporary Directory Discipline` 章节以指针引用;该章节只承载摘要,细则归此处。

## 1. 允许的落点

| 场景 | 落点 | 忽略要求 |
|---|---|---|
| 跨仓库 / 用户级临时数据 | `~/tmp/<project>/<purpose>/` | 不在 git 仓库内,不适用 `.gitignore` |
| 仓库内临时数据 | `<project>/.specify/.tmp/<purpose>/` | MUST 被 `.specify/.gitignore` 的 `.tmp/` 规则匹配 |
| 框架自有运行时工作区 | `.specify/history/.work/`、`.specify/teams/.work/`、`.specify/agents/execution/logs/`、`.specify/state/` | 由各自 owner 授权,不属本纪律改造范围（技能自有的运行期根由 `.specify/shared/guidelines/directory-governance.md` §5 登记；`.specify/state/` 为长期状态，不随工作项清理） |

`<purpose>` MUST 是稳定、可读的短名(如 `merge-skills`、`feedback`),使同一工作项的临时物聚在一起,便于清理。

## 2. 禁止的形态

- 裸 `/tmp/...`、`/var/tmp/...`,以及 `${TMPDIR:-/tmp}` 一类回退。
- 仓库根或任意子目录下的 ad-hoc `tmp/`、`scratch/`、`${SKILL_WORKDIR}/tmp/...`。
- 以 `~/scratch`、`~/temp` 等自造目录替代上述两个受制裁根。
- 在未校验忽略状态前写入仓库内临时目录。

## 3. 写入前检查

仓库内落点 MUST 在首次写入前校验:

```bash
git check-ignore -q .specify/.tmp || {
  # 该项目的 .specify/.gitignore 缺少 .tmp/ 规则:先补规则,或改用 ~/tmp。
  printf '\n# Agent-created scratch\n.tmp/\n' >> .specify/.gitignore
}
```

`.specify/.gitignore` 由 init 安装并含 `.tmp/`;旧项目若缺失该规则,MUST 先补规则再写入,或改用 `~/tmp/`。

## 4. 清理

- 临时目录 MUST 在工作项结束时删除;shell 脚本 MUST 用 `trap 'rm -rf "$tmp_dir"' EXIT` 覆盖失败路径。
- 需要保留为证据时,MUST 明确说明保留原因与位置,并确保该位置可被下一回合找到。
- 清理是删除 scratch,不是归档;与 `.specify/shared/patterns/reconcile-pattern.md` 的 archive-not-delete 不冲突。

## 5. 例外

以下情形 MAY 不使用上述两个根,但 MUST 在使用处注明理由,并在同一次操作内清理:

- **原子写临时文件**:必须与目标同盘、同目录、点号前缀,并在写入成功后 rename 或删除;它是实现细节,不是 scratch 目录。
- **库/OS 管理的临时目录**:`tempfile.TemporaryDirectory()`、构建工具 staging、第三方文档工具(如 LibreOffice socket/profile)。
- **容器内路径**:Docker 容器内的 `/tmp` 不是宿主机临时目录;宿主机侧仍按本纪律。

## 6. 扫描器边界

`.specify/scripts/python/scan-temp-usage.py` 是确定性守卫,扫描本框架自有文档与 shell 片段中的裸 `/tmp`、`${TMPDIR:-/tmp}`、`mktemp -d` 与 `/var/tmp`;白名单条目 MUST 携带理由。它不做 Python `mkdtemp` / `TemporaryDirectory` 的静态判定——合法用法太多,运行时由本文件的例外条款治理。

## 7. 与相邻纪律的边界

- `.specify/shared/guidelines/confirmation-gates.md`:删除 scratch 属于可逆动作,按该文件的判据自动执行并报告;本纪律不新增门控。
- `.specify/shared/patterns/reconcile-pattern.md`:scratch 清理是建议而非归档义务;本纪律不改变 reconcile 的 archive-not-delete。
- `.specify/shared/guidelines/user-facing-comprehension.md`:向用户呈现临时目录决策时,措辞归该文件;本纪律只裁落点与清理。
