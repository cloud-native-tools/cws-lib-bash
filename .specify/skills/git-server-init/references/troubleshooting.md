# 故障排查

按**症状**组织。每条给出定位命令与处置，按出现频率排序。

排查总原则：**先分清是"认证层"还是"git 层"失败**。

```bash
ssh -v <git-alias> exit 2>&1 | grep -Ei 'offering|accepted|denied|Authenticated'
```

看到 `Authenticated to ... as git` 说明认证已过，问题在 git 层；停在
`Permission denied (publickey)` 则是认证层。

---

## 症状 1：`Permission denied (publickey)`

最常见的症状，但**成因有五种**，其中两种与公钥无关。按此顺序排查：

### 1a. sshd 访问控制没放行 git 用户

```bash
ssh <admin-target> "grep -Ei '^(AllowUsers|AllowGroups|DenyUsers|DenyGroups)' /etc/ssh/sshd_config"
```

有输出且不含 `git`（或其所属组）→ 这是根因。此时公钥、权限全对也照样被拒，
症状与"公钥没装"完全一致，是最容易误判的一项。处置：把 git 加入 `AllowUsers`，
然后 `systemctl reload sshd`（reload 而非 restart，避免切断现有会话）。

### 1b. 权限过宽被 StrictModes 拒绝

```bash
ssh <git-alias> 'ls -ld /home/git /home/git/.ssh; ls -l /home/git/.ssh/authorized_keys'
```

判定口径是「**不可被 group/other 写**」，不是「必须 700/600」。以下都会被拒：

- `/home/git` 或 `.ssh` 带 group/other 写位（如 `775`、`777`）
- `authorized_keys` 带 group/other 写位（如 `664`、`666`）

处置：

```bash
ssh <admin-target> 'chmod 700 /home/git /home/git/.ssh && chmod 600 /home/git/.ssh/authorized_keys && chown -R git:git /home/git/.ssh'
```

确认 StrictModes 是否开启：`sshd -T | grep -i strictmodes`。

### 1c. 本机提供的私钥不是被授权的那把

```bash
ssh -G <git-alias> | grep -Ei '^(identityfile|identitiesonly) '
```

`identityfile` 可能输出**多行**（列表型选项，跨块累加），判据是期望的 key
在不在列表里，而非是否为首行。期望的 key 不在列表里 → 见
[症状 5](#症状-5ssh--g-列出多个-identityfile或没有期望的那把)。

`identitiesonly yes` 时**只**提供配置里声明的私钥（不含 agent 里的）；
若期望的 key 不在列表里，认证必然失败。多密钥环境下的取舍见
[`ssh-config-entry.md`](./ssh-config-entry.md) 第 5 节。

### 1d. 公钥确实没装上 / 装错了

```bash
# 本机待装公钥的指纹
ssh-keygen -lf <path>.pub | awk '{print $2}'
# 远端已授权的指纹
ssh <admin-target> "ssh-keygen -lf /home/git/.ssh/authorized_keys | awk '{print \$2}'"
```

两侧比对。注意比对**指纹**而非整行——同一把 key 的 comment 可能不同。

### 1e. `Too many authentication failures`

```
Received disconnect from ... Too many authentication failures
```

本机私钥太多，ssh 在被授权的那把之前先试完了 `MaxAuthTries`（默认 6）。
处置：给该 Host 条目加 `IdentitiesOnly yes` 并只声明需要的 `IdentityFile`。

---

## 症状 2：连接成功但身份不对（`whoami` 不是 git）

**这是本技能重点防御的缺陷**，成因是 first-match-wins，不是认证问题。

```bash
ssh -G <git-alias> | grep -E '^user '
```

若显示的不是 `git`：

1. 找出谁抢先声明了 `User`。查目标 ssh config 中所有匹配该别名、且声明 `User`
   的块，按**出现顺序**排列，第一个就是胜出者：

   ```bash
   awk '/^[[:space:]]*(Host|Match)[[:space:]]/{blk=$0} /^[[:space:]]*User[[:space:]]/{print NR": "blk" -> "$0}' <config>
   ```

2. 若胜出者是通配块（如 `Host <prefix>_*`）→ 把新条目移到它前面，或把通配块移到
   文件末尾
3. 若胜出者在**另一个文件**（主配置或更靠前的 Include）→ 本文件内重排无效，见
   [`ssh-config-entry.md`](./ssh-config-entry.md) 第 3 节

修完必须全量回归：插入位置变动会影响同文件其他条目的解析结果。

**为什么这个缺陷危险**：本机默认私钥常常同时被授权给 root 和 git，所以登成 root
不会报错。若该别名用于 `git clone`，checkout 出的文件属主是 root，问题会延迟到
数周后以普通用户操作时才暴露。

---

## 症状 3：`git push` 报权限错误，但 clone/fetch 正常

典型的属主问题——读只需要目录可遍历，写需要 `objects/` 与 `refs/` 可写。

```bash
ssh <git-alias> 'ls -ld /home/git/<ns>/<repo>.git/{objects,refs} && id'
```

若属主不是 git，或存在 root 属主的子目录（历史上有人以 root 身份直接操作过该
仓库），处置：

```bash
ssh <admin-target> 'chown -R git:git /home/git/<ns>'
```

注意连**命名空间目录**一起 chown：采集时发现过 `namespace` 目录是 `git:root`
而仓库本身正常的情况，新建同级仓库时会失败。

---

## 症状 3b：clone / ls-remote 正常，但 push 报 `Could not read from remote repository`

与症状 3 的区别：症状 3 是服务端属主问题，本症状是**客户端安全软件拦截**。
两者的报错很可能相似，靠下面的对照实验区分。

### 定性特征

典型于工作站上的 DLP / 代码防泄漏类安全软件（云壳等）：它拦截
「git 向远端服务器推送代码」，但放行 fetch / clone。

关键证据链（逐项验证）：

```bash
# 1. 读路径是否正常（能读到 refs 就说明认证与 transport 完好）
git ls-remote git@<git-alias>:<ns>/<repo>.git
git clone git@<git-alias>:<ns>/<repo>.git /tmp/probe   # 能拿到内容即正常

# 2. 包级追踪：push 到底走到哪一步
GIT_TRACE_PACKET=1 GIT_TRACE=1 git push <remote> <branch> 2>&1 | head -20

# 3. 对照组：纯本地 push（不经 ssh）
git init -q --bare -b main /tmp/l.git && git init -q -b main /tmp/s \
  && git -C /tmp/s -c user.email=t@t -c user.name=t commit -q --allow-empty -m i \
  && git -C /tmp/s push /tmp/l.git main
```

判定为客户端拦截的特征：

| 证据 | 含义 |
|------|------|
| 第 2 步输出里 `start_command: /usr/bin/ssh ...` 之后**零个 `packet:` 行** | ssh 子进程未产生任何协议数据 |
| 连 `Warning: Permanently added ...` 都没有（而 clone 有） | ssh 在启动阶段就被终止 |
| `GIT_SSH_COMMAND="ssh -v"` 也拿不到任何 `debug1:` 输出 | 同上，进程未真正跑起来 |
| 第 3 步本地 push **成功** | git 自身机制正常，排除 git 损坏 |
| 向**另一台已知稳定运行多年的** server push 也同样失败 | 决定性：与服务器无关 |
| `git push --no-verify` 仍然失败 | 排除本地 pre-push 钩子 |
| `-c core.hooksPath=/dev/null` 仍然失败 | 同上，排除全局钩子目录 |

### 服务端写路径的独立验证

不依赖本机 push 也能证明服务端正确：

```bash
# git 用户对裸仓库可写
ssh <git-alias> 'cd <git-home>/<ns>/<repo>.git && touch .wtest && rm -f .wtest && echo WRITABLE'

# receive-pack 能正常广告（喂 EOF 避免挂住）
ssh -n <git-alias> "git-receive-pack '<git-home>/<ns>/<repo>.git'" </dev/null | head -2
```

第二条期望看到：

```
00b1<zeros>capabilities^{}report-status report-status-v2 delete-refs side-band-64k quiet atomic ofs-delta object-format=sha1 agent=git/<ver>
0000致命错误：远端意外挂断了
```

那句「远端意外挂断」是我们喂 `/dev/null` 导致 EOF 的**预期结果**，不是故障——
能力广告已经完整发出，说明服务端写路径完好。

> 注：直接跑 `ssh <alias> "git-receive-pack '<path>'"` 而不喂 EOF 会**挂住**
> （receive-pack 在等客户端发命令）。诊断时一律加 `</dev/null` 与 `-n`。

### 处置

这类拦截**不在 git 也不在 ssh 的配置里**，改配置无法绕过，也不应尝试绕过（它是
公司的安全策略）。正确做法：

1. 验收改用 SKILL.md 的**关 3b**（服务端写路径判据）
2. 在交付报告里**显式声明**关 3a（本机 push）未执行及原因，不静默略过
3. 需要真实 push 验证时，换一台未装该类安全软件的机器（或经跳板机）执行

---

## 症状 4：`does not appear to be a git repository`

```
fatal: '<ns>/<repo>.git' does not appear to be a git repository
```

remote URL 的路径与远端实际路径不一致。三者必须严格对应：

```
git@<alias>:<ns>/<repo>.git   →   /home/git/<ns>/<repo>.git
                └──── 相对于 git 用户 home ────┘
```

定位：

```bash
ssh <git-alias> 'echo HOME=$HOME; ls -d $HOME/<ns>/<repo>.git'
```

常见错法：

| 错误 URL | 问题 |
|----------|------|
| `git@alias:/home/git/ns/repo.git` | 绝对路径。能工作但换 home 就失效，且与规范不符 |
| `git@alias:ns/repo` | 少 `.git` 后缀 |
| `git@alias:repo.git` | 少命名空间层级 |
| `git@alias:~/ns/repo.git` | `~` 会被展开，但可读性差且部分客户端处理不一致 |

---

## 症状 5：`ssh -G` 列出多个 identityfile，或没有期望的那把

先记住一个事实：`IdentityFile` 是**列表型**选项，跨所有匹配块**累加**，
不适用 first-match-wins。`ssh -G` 对它会输出多行，多行都会依次尝试：

```bash
ssh -G <git-alias> | grep -i '^identityfile'
```

所以判据是「**期望的 key 在不在列表里**」，不是「它是不是第一行」。

| 现象 | 结论 | 处置 |
|------|------|------|
| 列表里**包含**期望的 key，但不在首行 | 正常。上游 `Host *` 也声明了一把，两把都会试 | 无需处置。只要其中任一把被远端 git 用户授权，认证就能通过 |
| 列表里**没有**期望的 key | 条目根本没生效 | 见下方三步 |
| 列表只有上游那把 | 我们的 `IdentityFile` 行未被读取 | 见下方三步 |

期望的 key 不在列表里时，按此顺序查：

```bash
# 1. 条目真的写进目标文件了吗？
grep -n -A8 "Host <git-alias>" <config>

# 2. 是不是被否定模式排除了？（Host a b !<alias> 形式）
awk '/^[[:space:]]*Host/{print NR": "$0}' <config> | grep '!'

# 3. 是不是 ssh 实际读的不是这个文件？（-F 指定了其他配置，或
#    运行时路径与本文件不是同一个 inode）
ls -i <repo-path> <runtime-path>
```

第 3 项是最阴的一种：本机 ssh config 常与配置仓库里的文件互为**硬链接**，
编辑工具走 atomic rename 会断链，之后改的是仓库副本、ssh 读的是运行时旧文件。
详见[症状 9](#症状-9编辑-ssh-config-后运行时未生效)。

验证某把 key 到底能不能认证，绕过配置直接实测：

```bash
ssh -o IdentitiesOnly=yes -i <privkey> git@<server-ip-or-fqdn> whoami
```

返回 `git` 即该 key 已被授权，问题在配置层；返回 `Permission denied` 则是
授权层（回到症状 1）。

---

## 症状 6：`git init --bare -b` 报未知选项

远端 git < 2.28。脚本已内置回退（`init` + `symbolic-ref`），手工操作时：

```bash
git init --bare /home/git/<ns>/<repo>.git
git --git-dir=/home/git/<ns>/<repo>.git symbolic-ref HEAD refs/heads/main
```

查版本：`ssh <admin-target> 'git --version'`。

不显式设 HEAD 的后果：默认 `master`，而本机 `git init` 默认 `main`，首次 push
会在远端产生两个分支且默认分支不是期望的那个。

---

## 症状 7：`useradd` 失败

| 报错 | 成因 | 处置 |
|------|------|------|
| `user 'git' already exists` | 已有同名用户 | 脚本会走"已存在"分支只读校验；若 home 不符，人工确认是复用还是改名（`--git-user`） |
| `cannot open /etc/passwd` | 权限不足 | 确认管理通道是 root 或 sudo 可用 |
| `group git already exists` | 已有同名组但无同名用户 | `useradd` 默认建同名组会冲突；用 `--gid <existing>` 复用既有组 |
| home 已存在且非空 | 目录被预先创建过 | `useradd -m` 不会覆盖既有内容，会告警但成功；确认既有内容属主并 chown |

容器/镜像环境里 `git` 用户可能已由基础镜像创建（home 可能是 `/home/git` 也可能
是 `/git`）。脚本对已存在用户**只报告 home 偏差、不自动纠正**——纠正 home 会牵动
既有仓库路径，必须人工决策。

---

## 症状 8：SELinux 环境认证失败

权限、公钥、sshd 配置全对仍被拒，且系统是 RHEL/CentOS/Alibaba Cloud Linux 系：

```bash
ssh <admin-target> 'getenforce; ls -Zd /home/git /home/git/.ssh; ls -Z /home/git/.ssh/authorized_keys'
```

期望 context 含 `ssh_home_t`（`.ssh` 目录与 `authorized_keys`）。不符时：

```bash
ssh <admin-target> 'restorecon -R -v /home/git'
```

`getenforce` 返回 `Enforcing` 才会真的拦截；`Permissive` 只记日志。查拦截记录：

```bash
ssh <admin-target> 'ausearch -m avc -ts recent 2>/dev/null | tail -20'
```

---

## 症状 9：编辑 ssh config 后运行时未生效

本机 ssh config 常与配置仓库里的文件互为**硬链接**。编辑工具若走 atomic rename
（写临时文件再 rename），会断开硬链接，运行时读到的仍是旧内容。

```bash
ls -i <repo-path> <runtime-path>   # 两个 inode 数字应相同
```

不同则重建：

```bash
ln -f <repo-path> <runtime-path>
```

另一种可能：改的是 `~/.ssh/config` 但实际生效的是 `-F` 指定的其他文件，或
`Include` 链里另有一份同名条目。用 `ssh -G` 确认生效值，不要假设。

---

## 附：一次性诊断脚本

把下面的块整体贴给管理通道，一次拿到全部判据：

```bash
ssh <admin-target> 'bash -s' <<'EOF'
set -u
echo "=== 身份 ==="; id; hostname
echo "=== git 用户 ==="; getent passwd git || echo "不存在"
echo "=== 目录权限 ==="
for p in /home/git /home/git/.ssh /home/git/.ssh/authorized_keys; do
  [ -e "$p" ] && stat -c '%A %U:%G %n' "$p" || echo "缺失: $p"
done
echo "=== 已授权指纹 ==="
ssh-keygen -lf /home/git/.ssh/authorized_keys 2>/dev/null || echo "无法读取"
echo "=== 裸仓库 ==="
find /home/git -maxdepth 3 -name '*.git' -type d 2>/dev/null | while read -r d; do
  printf '%s  HEAD=%s  owner=%s\n' "$d" \
    "$(cat "$d/HEAD" 2>/dev/null)" "$(stat -c '%U:%G' "$d" 2>/dev/null)"
done
echo "=== sshd 约束 ==="
grep -Ei '^(AllowUsers|AllowGroups|DenyUsers|DenyGroups|PubkeyAuthentication|AuthorizedKeysFile|StrictHostKeyChecking)' /etc/ssh/sshd_config 2>/dev/null || echo "(无显式约束)"
echo "=== SELinux ==="; getenforce 2>/dev/null || echo "(未启用)"
echo "=== git 版本 ==="; git --version 2>/dev/null || echo "git 未安装"
EOF
```
