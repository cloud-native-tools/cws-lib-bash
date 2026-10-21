# D4 详解：ssh config 条目与 first-match-wins

本文档是 SKILL.md 第 3 步「收敛本机 ssh config」的展开。D4 是四项期望态里唯一
**会静默失败**的一项——D1/D2/D3 出问题会报错，D4 出问题连接照样成功，只是登进了
错误的用户。

## 1. first-match-wins 语义

ssh 读取配置时，对**每一个选项独立**取「首次获得的值」：

> For each parameter, the first obtained value will be used.

当多个 `Host` / `Match` 块匹配同一个别名时，**位置靠前**的块提供的值胜出，靠后的
同名选项被静默丢弃。这不是"具体优先于通配"，而纯粹是**顺序**优先——ssh 不知道
`Host workspace_*` 比 `Host workspace_foo_git` 更"宽泛"。

### 真实案例

一台服务器上要建 git 用户，本机 ssh config 里原本有一段通配兜底：

```sshconfig
# 文件顶部
Host workspace_*
  User root

# ……中间是若干具体主机……

# 文件后部
Host workspace_docker_baremetal_8_git
  # for git clone
  Port 22
  User git
  IdentitiesOnly yes
  Hostname 192.0.2.196
```

`workspace_docker_baremetal_8_git` 同时匹配这两个块。通配块在前，于是：

```console
$ ssh -G workspace_docker_baremetal_8_git | grep -E '^(user|hostname) '
user root                        ← 不是配置里写的 git
hostname 192.0.2.196

$ ssh workspace_docker_baremetal_8_git whoami
root                             ← 连接成功，用户错了
```

因为本机默认私钥恰好也在远端 root 的 `authorized_keys` 里，认证顺利通过，
**没有任何报错**。这个缺陷在该仓库里存在了一年多，直到有人问"为什么 whoami 是 root"
才被发现。

同一文件里全部 4 个 `*_git` 别名都受影响，其中若干注释写着 `# for git clone`
——意味着历史上经它们 checkout 的仓库属主可能是 root，后续以普通用户操作会撞权限。

### 修复

把通配兜底块整体移到文件末尾（具体块在前、通配在后），并就地留注释说明约束：

```sshconfig
# 通配兜底块：必须置于文件末尾（first-match-wins），给上方未显式声明 User
# 的主机提供默认值 root，同时不影响已声明 User git 的 *_git 主机。
Host workspace_*
  User root
```

修复后回归验证（9 个 Host 全量枚举）：5 个未声明 `User` 的仍取 `root`，
4 个 `*_git` 转为 `git`，hostname 无一错位。

### 对本技能的约束

`ssh_config_insert.py` **不把新条目追加到文件末尾**，而是计算插入位置：

```
插入点 = 文件中最早一个满足以下两条的块的起始行
         (a) 该块的 Host glob（含 ! 否定）/ Match 条件匹配目标别名
         (b) 该块声明了本条目也要声明的至少一个选项
若无这样的块 → 追加到文件末尾
```

脚本会打印它选了哪个位置、为什么：

```console
state  : inserting BEFORE line 65  (host workspace_*)
reason : that block matches "workspace_docker_baremetal_9_git" and declares
         user — under first-match-wins it would override ours
```

条件 (b) 是**按选项交集**判断的，不是"只要有块匹配就插到最前面"。一个只声明
`ServerAliveInterval` 的匹配块不构成冲突，无需插到它前面。

## 2. 两类选项：首值生效 vs 累加

first-match-wins 是**默认**规则，但不是所有选项都遵循它。ssh_config(5) 里有一类
**列表型**选项，多个匹配块的声明会**累加**而非互相覆盖：

| 类别 | 选项（不完全枚举） | 多块同时声明时 | `ssh -G` 输出 |
|------|--------------------|----------------|---------------|
| **首值生效** | `User`、`Hostname`、`Port`、`IdentitiesOnly`、`ProxyJump`、`ForwardAgent`、`StrictHostKeyChecking` 等绝大多数 | 只有最靠前的值生效，其余静默丢弃 | 一行 |
| **列表型（累加）** | `IdentityFile`、`CertificateFile`、`LocalForward`、`RemoteForward`、`DynamicForward`、`SendEnv`、`SetEnv`、`GlobalKnownHostsFile`、`UserKnownHostsFile` | 全部生效，按出现顺序依次尝试 | **多行**，一行一个值 |

`IdentityFile` 是这里最要紧的一个。ssh_config(5) 原文：

> It is possible to have multiple identity files specified in configuration
> files; all these identities will be tried in sequence.

实测：主配置 `Host *` 声明了一把，被 Include 的具体条目又声明了另一把，
`ssh -G` 给出**两行**，两把都会被尝试：

```console
$ ssh -G <git-alias> | grep -i '^identityfile'
identityfile ~/.ssh/id_rsa
identityfile ~/.ssh/keys/<scenario>_id_rsa
```

推论有两条：

1. **只有列表型选项时不构成顺序冲突。** 一个仅声明 `IdentityFile` 的匹配块不会
   让后写的 `IdentityFile` 失效，无需插到它前面。`ssh_config_insert.py` 的
   `LIST_OPTIONS` 就是为此把这些选项从冲突判定里排除
2. **验证必须按集合判定，不能只看首行。** `ssh -G` 对列表型选项输出多行，
   取首行做等值比较会产生假阴性（我们声明的 key 明明在列表里却判失败）

`LIST_OPTIONS` 未收录的选项一律按首值生效处理——这是安全方向：多判一个冲突只是
让我们插得更靠前，而漏判会重现第 1 节的静默失败。

## 3. Include 链的读取顺序

`Include` 指令**就地展开**，所以生效顺序由「主配置里 Include 出现的位置」决定：

```sshconfig
# ~/.ssh/config
Host *
  User admin                        # ← 首值生效类选项，早于所有 Include 内容

Include ~/.ssh/conf.d/team-a        # ← 这里的块排在 Host * 之后
Include ~/.ssh/conf.d/team-b        # ← 更晚
```

后果：**主配置顶部的 `Host *` 会赢过任何被 Include 文件里的同名首值生效选项**。
上例中即便 `team-a` 的条目写了 `User git`，生效的仍是 `admin`。

这种情况**在本文件内重排解决不了**——冲突块根本不在同一个文件里。
`ssh_config_insert.py --verify` 会检出标量选项不符并报 `NOT-CONVERGED`，
此时要往 Include 链上游找。

处置选项（按优先级）：

1. **把条目写进更早被读取的文件**（主配置，或排序更靠前的 Include 目标）
2. **调整主配置里 `Include` 的位置**，把目标文件提到冲突块之前——影响面最大，
   改完必须对**所有**别名做全量回归
3. 若冲突选项是列表型（如 `IdentityFile`），**无需处置**：上游值与我们的值会
   一起生效，只要其中任一把被远端授权即可通过认证

定位谁在 Include 链里声明了某选项：

```bash
for f in ~/.ssh/config $(awk '/^[[:space:]]*Include/{print $2}' ~/.ssh/config | sed "s|~|$HOME|"); do
  [ -f "$f" ] && grep -Hn -i '<option>' "$f"
done
```

## 4. `Match` 块的保守处理

`Match` 的条件（`host` / `user` / `exec` / `canonical` / `all`）无法完全静态求值
——`exec` 要真的执行命令才知道结果。脚本采取保守策略：

- 有 `host` 条件 → 按 glob 列表测试是否匹配目标别名
- 无 `host` 条件（如 `Match all`、纯 `exec`）→ **视为可能匹配**，构成冲突

保守方向的代价只是"插得更靠前一点"，而 first-match-wins 下更靠前 = 更高优先级
= 我们的具体条目胜出，所以这个偏差是安全的。反之若漏判，就会重现第 1 节的静默
失败。

注：`ssh -G` 会**真实执行** `Match exec` 里的命令，所以它的输出已经反映了条件化
匹配的生效结果——这正是必须用 `ssh -G` 而非静态解析来验证的原因。

## 5. 条目模板

置备 Git 服务器所需的最小条目：

```sshconfig
# for git clone
Host <git-alias>
  Hostname <server-ip-or-fqdn>
  Port 22
  User git
  IdentitiesOnly yes
  IdentityFile <path-to-private-key>
```

各项作用：

| 选项 | 必要性 | 说明 |
|------|--------|------|
| `User git` | 必需 | 缺省会取当前本机用户名，或上游通配块的值 |
| `Hostname` | 必需 | git remote URL 用别名，靠这里解析到真实地址 |
| `IdentitiesOnly yes` | 强烈建议 | 只提供本条目声明的私钥。多密钥环境下避免把无关公钥挨个试一遍触发远端 `MaxAuthTries` 断开 |
| `IdentityFile` | 可选 | 列表型选项，与上游声明累加，不会因顺序丢失（见第 2 节） |
| `Port` | 非 22 时必需 | 显式写出便于阅读 |

`IdentityFile` 指向**私钥**，不是 `.pub`。ssh 会自行推导同目录同名 `.pub`。

## 6. 验证协议

配置写完必须验证，且**只能**用 `ssh -G`：

```bash
# 生效值（唯一权威）
ssh -G <git-alias> | grep -Ei '^(user|hostname|port|identityfile|identitiesonly) '
```

三条纪律：

1. **不要用读文件代替 `ssh -G`。** 文件里的字面量不等于生效值，Include 链与
   `Match exec` 都会改变结果
2. **不要只验证新条目。** 插入位置错误会连带打挂同文件其他条目，必须全量回归：

   ```bash
   for h in $(awk '/^Host /{for(i=2;i<=NF;i++) if($i !~ /[*!?]/) print $i}' <config>); do
     printf '%-45s user=%-8s host=%s\n' "$h" \
       "$(ssh -G "$h" 2>/dev/null | awk '/^user /{print $2}')" \
       "$(ssh -G "$h" 2>/dev/null | awk '/^hostname /{print $2}')"
   done
   ```

3. **配置对不等于能用。** 最后必须过 SKILL.md 第 4 步的关 2、关 3
   （`git ls-remote` 与真实 push），那才验证了认证与 git 协议通路

## 7. 编辑该文件的注意事项

- **硬链接**：ssh config 常与某个配置仓库里的文件互为硬链接（inode 相同）。
  编辑工具若走 atomic rename（写临时文件再 rename），会**断开硬链接**，
  两侧从此各自演化。改完核对 inode：

  ```bash
  ls -i <repo-path> <runtime-path>   # 两个数字应相同
  ```

  断了就用 `ln -f <repo-path> <runtime-path>` 重建

- **备份**：文件已被版本控制跟踪且工作区干净时，`git checkout -- <path>`
  已具备精确回滚能力；否则先 `cp <path> <path>.bak`

- **权限**：ssh 要求配置文件不可被他人写。保持 600 或 644，
  不要引入 group/other 可写位
