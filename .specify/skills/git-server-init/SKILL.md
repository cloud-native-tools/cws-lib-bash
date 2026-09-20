---
name: git-server-init
description: |
  Provision a plain SSH server into a Git server: create the git user, create bare repositories under the git home, authorize local public keys, and add the matching Host entry to the local ssh config. Use this when the user mentions ["git server", "git server init", "bare repository", "git init --bare", "git user", "self-hosted git", "ssh git remote", "git 服务器", "搭建git服务", "裸仓库", "创建git用户", "配置git远程", "git remote 服务器", "authorized_keys git"]
skill_id: "<SKILL:.specify/skills/git-server-init/SKILL.md>"
---

# git-server-init

## Overview

把一台只有 SSH 的普通服务器置备成 Git 服务器。技能是**调谐引擎**（reconcile），
遵循 [`.specify/shared/patterns/reconcile-pattern.md`](../../shared/patterns/reconcile-pattern.md)：
期望态由四项声明组成，每次调用都先观察、再比对、只收敛缺口，重复执行安全。

```
期望态 D1  git 用户存在（home = git home，shell = /bin/bash）
期望态 D2  裸仓库存在于 <git-home>/<namespace>/<repo>.git，属主为 git，
           HEAD 指向 refs/heads/<initial-branch>
期望态 D3  本机公钥已进入 <git-home>/.ssh/authorized_keys（按指纹去重），
           目录与文件权限满足 sshd StrictModes
期望态 D4  本机 ssh config 中存在 Host <alias> 条目，且 `ssh -G <alias>`
           解析出的 user / hostname 与期望一致
```

四项都收敛后，`git clone git@<alias>:<namespace>/<repo>.git` 即可用。

**这个技能的价值不在"会敲 useradd 和 git init"**——那些命令人尽皆知。价值在于
D4：ssh config 的 first-match-wins 语义会让一条写对了 `User git` 的条目静默
解析成别的用户，连接照样成功、`whoami` 却是错的。见
[`references/ssh-config-entry.md`](./references/ssh-config-entry.md)。

## Portability contract

本技能属于可移植的公开下层，**MUST NOT** 内嵌任何机器特定事实：

- 不含主机清单、IP 地址、内部主机名、绝对用户目录
- 服务器身份一律由调用方以 `--host <ssh-alias|user@host>` 传入
- 本机 ssh config 路径由调用方传入或经 `--verify` 探测，不假定 `~/.ssh/config`
- 待授权公钥默认从 `ssh -G <host>` 解析出的 identityfile 推导（即"这台机器本来
  就会拿去认证的那几把"），可用 `--pubkey` 覆盖

部署环境若有私有约定（固定的 ssh config 分层、通配块、命名规范），应由该环境的
前门技能承载，本技能只接受参数。

## Workflow

### 0. 收集输入（判断类，与用户确认）

必需：

| 输入 | 说明 | 示例 |
|------|------|------|
| 管理入口 | 有 root 或 sudo 权限的 SSH 目标 | `myserver-admin` |
| 命名空间 | 裸仓库的父目录，决定 remote URL 路径 | `team-alpha` |
| 仓库名 | 一个或多个 | `infra`、`docs` |
| git 别名 | 本机 ssh config 中的 Host 名 | `myserver_git` |

可选（有默认值）：git 用户名 `git`、git home `/home/git`、初始分支 `main`、
本机 ssh config 路径、待授权公钥。

命名空间与仓库名共同决定远端路径，映射关系是固定的：

```
--repo team-alpha/infra   →   <git-home>/team-alpha/infra.git
                          →   git@<git-alias>:team-alpha/infra.git
```

### 1. 观察（只读，两侧各一次）

先跑观察，把缺口摊开，再决定动不动手。**这一步不修改任何东西。**

```bash
# 远端：D1/D2/D3 缺口报告。退出码 0=已收敛，3=有缺口，2=前置条件不满足
bash "${SKILL_HOME}/scripts/provision-git-server.sh" \
  --host <admin-target> --repo <namespace>/<repo> --check
```

```bash
# 本机：D4 现状。--check 只观察不写
python3 "${SKILL_HOME}/scripts/ssh_config_insert.py" \
  --config <ssh-config-path> --alias <git-alias> \
  --hostname <server-ip-or-fqdn> --user git --check --verify
```

观察结果里要特别读三件事：

1. **git 用户已存在但 home 不是期望值** → 脚本报告但不自动纠正，需人工确认
2. **仓库已存在但 HEAD 不是期望分支** → 脚本会纠正（`symbolic-ref`，无损）
3. **`--verify` 报标量选项（user/hostname/port）不符** → 冲突块在 Include 链更靠前的
   文件里，在本文件内重排解决不了。注：`identityfile` 多行是**正常**的——
   `IdentityFile` 是列表型选项，跨块累加而非覆盖，判据是期望的 key 在不在
   列表里。两类选项的区别见 references 第 2 节

### 2. 收敛服务器（D1/D2/D3）

管理入口需要 root 或 sudo。首次对某台主机置备前，**MUST 先把第 1 步的缺口报告
呈现给用户**再执行——这是在别人机器上建系统用户、改认证材料，即便动作是加法且
幂等，也不该静默发生。

```bash
bash "${SKILL_HOME}/scripts/provision-git-server.sh" \
  --host <admin-target> \
  --repo <namespace>/<repo> \
  [--pubkey <path>]... \
  [--git-user git] [--git-home /home/git] [--initial-branch main]
```

脚本行为（全部幂等，不销毁任何东西）：

- 用户不存在才 `useradd --create-home`；已存在则只读校验并报告 home/shell 偏差
- `authorized_keys` 按**指纹**去重后追加，不重复、不覆盖既有条目；写入走
  `install -o -g -m 600` 一步落定属主与权限
- 仓库目录不存在才 `git init --bare`；git ≥ 2.28 用 `-b <branch>`，更老版本
  回退为 `init` + `symbolic-ref`
- 权限收敛为 `<git-home>`=700、`.ssh`=700、`authorized_keys`=600，属主 git

先用 `--dry-run` 打印将要送到远端执行的完整脚本，确认无误再实跑。

### 3. 收敛本机 ssh config（D4）——本技能的关键约束

```bash
python3 "${SKILL_HOME}/scripts/ssh_config_insert.py" \
  --config <ssh-config-path> \
  --alias <git-alias> \
  --hostname <server-ip-or-fqdn> \
  --port 22 --user git --identities-only yes \
  [--identity-file <path>] \
  [--comment 'for git clone'] \
  --verify
```

脚本不把条目追加到文件末尾，而是**计算插入位置**：找到文件中最早一个
「匹配该别名 且 声明了本条目也要声明的**首值生效类**选项」的 `Host`/`Match` 块，
插到它前面，并打印为什么是那个位置。没有冲突块才追加到末尾。

`IdentityFile` 等**列表型**选项被排除在冲突判定之外：它们跨匹配块累加，
相对顺序不会让我们的值丢失，为它们提前插入位置只会产生噪声。

若该别名的精确 `Host` 块已存在，脚本默认**只报告 drift、不改写**；要收敛既有块
需显式加 `--update`。绝不制造第二个同名块。

### 4. 端到端验证（强制门禁，不可跳过）

配置写对不等于能用。**MUST 依次跑完三关**，任何一关不过都不算完成：

```bash
# 关 1：ssh 自己怎么解析这个别名（唯一权威视角，别用读文件代替）
ssh -G <git-alias> | grep -Ei '^(user|hostname|port|identityfile|identitiesonly) '
#    期望 user=git；若是别的值 → 回到第 3 步查 Include 链冲突

# 关 2：认证与 git 协议通路（空裸仓库返回 0 且无输出，即为正常）
git ls-remote git@<git-alias>:<namespace>/<repo>.git

# 关 3：写路径（二选一，见下）
```

**关 3a（首选）——本机真实 push：**

```bash
d=$(mktemp -d) && git init -q -b main "$d/t" \
  && git -C "$d/t" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init \
  && git -C "$d/t" remote add s "git@<git-alias>:<namespace>/<repo>.git" \
  && git -C "$d/t" push -q s main && echo "PUSH OK" && rm -rf "$d"
```

**关 3b（回退）——从服务端验证写路径。** 本机存在阻止外推的安全软件时
（见下方「关 3a 失败的归因纪律」），关 3a 在任何自建 server 上都会失败，
此时改用服务端判据，它同样能证明 D2/D3 正确：

```bash
# git 用户对裸仓库可写（push 真正需要的能力）
ssh <git-alias> 'cd <git-home>/<namespace>/<repo>.git && touch .wtest && rm -f .wtest \
  && echo "WRITABLE as $(whoami)"'

# receive-pack 能正常广告（push 的远端半边），喂 EOF 避免挂住
ssh -n <git-alias> "git-receive-pack '<git-home>/<namespace>/<repo>.git'" </dev/null | head -2
#   期望看到 capabilities^{}report-status ... agent=git/<ver>；随后的
#   「远端意外挂断」是 EOF 导致的预期结果，不是故障

# 命名空间目录属主必须是 git（否则 git 用户无法在该命名空间下建新仓库）
ssh <admin-target> "stat -c '%U:%G %n' <git-home>/<namespace>"
```

关 3a/3b 都会往裸仓库写入内容或触碰其目录。若目标仓库是**已有内容**的仓库而非
新建空仓库，关 3a 跳过，只跑关 2 + 关 3b 的只读部分。

### 关 3a 失败的归因纪律

`fatal: Could not read from remote repository.` 是个**高度歧义**的报错：服务器端
配置错误与客户端安全软件拦截给出的是同一句话。**MUST 做对照实验区分两者**，
不得直接判定置备失败：

| 观测 | 结论 |
|------|------|
| 关 1、关 2 通过，且 `git clone` 同一 server 成功，仅 push 失败 | 读路径与认证均正常 → 写路径被客户端拦截 |
| 向**另一台已知稳定的** git server push 也同样失败 | 决定性证据：客户端环境问题，与本次置备无关 |
| `GIT_TRACE_PACKET=1 git push` 显示 `start_command` 后**零个数据包**、且无 ssh 任何输出（连 host key 警告都没有） | ssh 子进程被安全软件在启动阶段即终止 |
| 纯本地 push（`git init --bare` 到本地路径）成功 | git 自身机制正常，排除 git 损坏 |
| 远端 `git-receive-pack` 手工调用能正常广告 refs | 服务端写路径完好 |

已知的真实成因：工作站上的 DLP / 代码防泄漏类安全软件（云壳等）会拦截
「git 向远端服务器推送代码」，但放行 fetch/clone。这类拦截**不在 git 也不在 ssh
的配置里**，无法通过改配置绕过，也不该尝试绕过——它是公司的安全策略。
此时关 3b 是唯一可行的验收路径，且**必须在报告里显式声明关 3a 未执行及原因**，
不得静默略过。

## Loop Card

| Field | Value |
|-------|-------|
| WHEN  | 用户要把某台 SSH 服务器变成 Git 服务器；或已置备的服务器出现 D1–D4 任一项漂移 |
| SEE   | 第 1 步两侧观察输出：远端 `--check` 缺口报告 + 本机 `--check --verify` 现状 |
| DO    | 收敛一个缺口批次：先远端 D1/D2/D3，再本机 D4（顺序不可颠倒——D4 的 `--verify` 需要远端已可认证） |
| CHECK | 第 4 步三关门禁：`ssh -G` 解析值 → `git ls-remote` → 写路径（关 3a 真实 push，客户端禁推时回退关 3b 服务端验证） |
| STOP  | 三关全绿即停。任一环失败最多重试 2 轮；仍失败则停下报告，不反复改写 ssh config |
| LEAVE | 收敛后的服务器状态 + 本机 ssh config 条目 + 三关验证输出；未收敛项显式列出，不静默略过 |

## Hard rules

**MUST**

- 用 `ssh -G <alias>` 判定生效配置。它是唯一权威视角，会完整评估 Include 链与
  `Match exec`；读配置文件肉眼判断块顺序**必然**漏判
- 新增 `Host` 条目插入到任何「匹配该别名且声明同名**首值生效类**选项」的块
  **之前**；列表型选项（`IdentityFile` 等）不构成顺序冲突
- 改完 ssh config 后跑全量回归：枚举同文件其他 Host，确认未声明 `User` 的条目
  仍取到它们原本的默认值（插入位置错误会连带打挂别的条目）
- 按指纹去重公钥；重复执行不得产生重复条目
- 首次置备某主机前，把 `--check` 缺口报告呈现给用户
- 收敛远端前确认目标主机身份，避免在错误的机器上建用户

**MUST NOT**

- 不用 `echo >>` 直接追加 `authorized_keys` 而不重设属主与权限——sshd
  StrictModes 下权限过宽会被静默拒绝认证
- 不替换、不删除已存在的 git 用户、裸仓库、公钥条目；只报告偏差
- 不改动其他用户的 `authorized_keys`
- 不给 `--repo` 传绝对路径或带 `.git` 后缀的值（脚本会拒绝）
- 不硬编码 git 用户 uid/gid。参考环境里是 1000，那只是"该机第一个普通用户"
  的巧合，换台机器就不同
- 不在未跑第 4 步验证的情况下宣称完成
- 关 3a 失败时先做对照实验归因（见第 4 步表），区分「服务器没配对」与
  「客户端安全软件拦截」；后者改跑关 3b 并在报告中显式声明
- 命名空间目录（`<git-home>/<namespace>`）属主必须是 git 用户。它由 sudo
  `mkdir -p` 创建，不显式 chown 就会留下 root 属主：仓库本身能用，但 git
  用户再也无法在该命名空间下自建仓库

## Resources

### Scripts (`${SKILL_HOME}/scripts/`)

- `provision-git-server.sh` — 远端置备调谐器。`--check` 观察 / 默认收敛 /
  `--dry-run` 打印将执行的远端脚本。经单条 ssh 会话投递整段脚本，
  一次往返完成 D1/D2/D3
- `ssh_config_insert.py` — 本机 ssh config 插入器。解析块结构与 glob/否定模式，
  按 first-match-wins 计算插入位置，`--verify` 用 `ssh -G` 断言生效值

### References (`${SKILL_HOME}/references/`)

- [`ssh-config-entry.md`](./references/ssh-config-entry.md) — D4 详解：
  first-match-wins 语义、Include 链读取顺序、条目模板、验证协议，
  以及一个"写对了 `User git` 却登录成 root"的真实案例
- [`troubleshooting.md`](./references/troubleshooting.md) — 按症状定位：
  认证被拒、用户错、push 报权限、老版本 git、SELinux、仓库路径与 URL 不匹配
- [`reference-architecture.md`](./references/reference-architecture.md) —
  置备完成的目标态规格（用户/权限/裸仓库内部结构/authorized_keys 形态），
  作为 `--check` 输出的对照基线

### Assets (`${SKILL_HOME}/assets/`)

- 无。产出是服务器状态与 ssh config 条目，不生成文件

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:git-server-init" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
