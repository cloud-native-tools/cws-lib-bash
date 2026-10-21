# 置备完成的目标态规格

`provision-git-server.sh --check` 的输出应与本文档描述的状态一致。这里给出的是
**规格**（应该长什么样），不是某台具体机器的快照——所有标识符均为占位符。

规格来源：对两台已稳定运行一年以上的自建 Git 服务器做逆向采集，取其规范形态。
采集时观察到同一逻辑状态存在"规范"与"能用但不规范"两种落地形式，下文对两者都
做了标注，**脚本一律收敛到规范形态**。

## 1. git 用户

```console
$ getent passwd git
git:x:<uid>:<gid>::/home/git:/bin/bash

$ id git
uid=<uid>(git) gid=<gid>(git) 组=<gid>(git)
```

| 属性 | 规范值 | 说明 |
|------|--------|------|
| home | `/home/git` | 决定 remote URL 的路径基准：`git@alias:ns/repo.git` → `/home/git/ns/repo.git` |
| shell | `/bin/bash` | **不要用 `git-shell`**，除非明确只要 git 协议、不给交互登录。用 `git-shell` 时 `ssh <alias> whoami` 会被拒绝，D4 的验证方式要相应改变 |
| uid/gid | 由系统分配 | **不要硬编码**。参考环境里恰好是 1000，那只是"该机第一个普通用户"的巧合 |
| 组 | 与用户同名 | 脚本用 `id -gn` 读取实际主组，不假定等于用户名 |

## 2. 目录与权限

```console
$ ls -ld /home/git /home/git/.ssh /home/git/.ssh/authorized_keys
drwx------  <uid> git git  /home/git
drwx------  <uid> git git  /home/git/.ssh
-rw-------  <uid> git git  /home/git/.ssh/authorized_keys
```

| 路径 | 规范 | 采集到的不规范变体 | 为什么变体也能用 |
|------|------|---------------------|------------------|
| `/home/git` | `700` git:git | — | — |
| `/home/git/.ssh` | `700` git:git | `755` git:git；`755` root:root | sshd `StrictModes` 只拒绝**group/other 可写**，755 不可写故通过；属主非 git 也不影响读取 |
| `authorized_keys` | `600` git:git | `644` root:root | 同上，644 无写位故通过 |

不规范变体能工作，但把认证材料的属主留给 root 会让 git 用户自己无法维护它
（例如日后由 git 用户身份的钩子或服务追加 key）。脚本一律收敛为 git:git + 700/600。

`StrictModes` 的判定口径是「不可被他人写」，不是「必须 700/600」。理解这点有助于
排查：权限"看起来还行"却被拒时，先查有没有写位，再查属主链上每一级目录。

## 3. 裸仓库

### 3.1 布局

```
/home/git/
├── <namespace-a>/
│   ├── <repo-1>.git/
│   └── <repo-2>.git/
└── <namespace-b>/
    └── <repo-3>.git/
```

命名空间就是仓库的父目录，与 remote URL 的路径部分一一对应：

| remote URL | 远端路径 |
|------------|----------|
| `git@<alias>:<ns-a>/<repo-1>.git` | `/home/git/<ns-a>/<repo-1>.git` |
| `git@<alias>:<ns-b>/<repo-3>.git` | `/home/git/<ns-b>/<repo-3>.git` |

git 把 URL 里 `:` 之后的部分当作**相对于 git 用户 home 的路径**解析。这就是为什么
`--repo` 必须是 `<namespace>/<name>` 形式且不带绝对路径前缀。

### 3.2 仓库内部

```console
$ ls -la /home/git/<ns>/<repo>.git/
drwxr-xr-x  branches/
-rw-r--r--  config
-rw-r--r--  description
-rw-r--r--  HEAD
drwxr-xr-x  hooks/
drwxr-xr-x  info/
drwxr-xr-x  objects/
drwxr-xr-x  refs/

$ git --git-dir=/home/git/<ns>/<repo>.git config --local --list
core.repositoryformatversion=0
core.filemode=true
core.bare=true

$ cat /home/git/<ns>/<repo>.git/HEAD
ref: refs/heads/main
```

要点：

- 就是 `git init --bare` 的原始产物，**无自定义 hooks**（`hooks/` 下只有
  `*.sample`）、无 `core.sharedrepository`、无额外 config
- `HEAD` 指向 `refs/heads/<initial-branch>`。采集环境的 git 是 2.43.x，其
  `init.defaultBranch` 未设置时默认仍为 `master`，而实际 HEAD 是 `main` ——
  说明当初是**显式指定**的。脚本因此总是显式传分支名，不依赖远端默认值
- `description` 保持 `git init` 的默认占位文本，无需改写

### 3.3 属主

仓库整棵树**以及它的命名空间父目录**属主必须是 git 用户：

```bash
chown -R git:git /home/git/<ns>/<repo>.git
chown git:git /home/git/<ns>          # 容易遗漏的一层
```

两层各有不同的失败模式：

| 层级 | 属主不是 git 时的后果 |
|------|----------------------|
| 仓库内部（`objects/`、`refs/`） | git 用户 push 时无法写入，报权限错误 |
| 命名空间目录（`<ns>`） | 仓库本身能用，但 git 用户无法在该命名空间下**新建**仓库 |

命名空间目录由 sudo `mkdir -p` 创建，不显式 chown 就会留下 root 属主——这是
本技能开发期间实测捕获并修复的真实缺陷（新建的服务器上是 `root:root`，
而两台参考机均为 `git:git`）。

采集时还发现有仓库父目录属主混杂（namespace 目录 `git:root`）的历史残留，
这类问题会在新建同级仓库时才暴露。

## 4. authorized_keys

```console
$ ssh-keygen -lf /home/git/.ssh/authorized_keys
4096 SHA256:<fp-1> <comment-1> (RSA)
4096 SHA256:<fp-2> <comment-2> (RSA)
4096 SHA256:<fp-3> <comment-3> (RSA)
```

采集到的规范形态包含**三类**公钥：

| 类别 | 来源 | 作用 |
|------|------|------|
| 工作站默认私钥 | `~/.ssh/id_rsa.pub` | 日常 git 操作 |
| 工作站场景私钥 | 该项目/环境专用的另一把 | 多身份隔离场景 |
| 服务器自身公钥 | 远端 git 或 root 用户自己的 `id_rsa.pub` | 服务器向外部 Git 平台（如企业代码托管）推拉时需要 |

第三类是否安装取决于该服务器是否需要主动访问外部 Git 平台。本技能默认只装
**本机侧**的公钥（从 `ssh -G <host>` 的 identityfile 推导），服务器自身公钥不在
默认范围内 —— 需要时用 `--pubkey` 显式追加。

去重按**指纹**而非整行字符串比较。理由：同一把 key 可能带不同 comment、
不同换行/尾随空白，字符串比较会误判为两把并追加重复条目。

```bash
# 正确的去重口径
ssh-keygen -lf authorized_keys | awk '{print $2}'
```

## 5. 服务端前置条件

| 项 | 要求 | 检查方式 |
|----|------|----------|
| sshd | `PubkeyAuthentication yes`；`AuthorizedKeysFile` 含 `.ssh/authorized_keys` | `grep -Ei '^(PubkeyAuthentication\|AuthorizedKeysFile)' /etc/ssh/sshd_config` |
| sshd 访问控制 | `AllowUsers` / `AllowGroups` / `DenyUsers` 若存在，**必须**包含 git 用户或其所属组 | `grep -Ei '^(AllowUsers\|AllowGroups\|DenyUsers)' /etc/ssh/sshd_config` |
| git | 已安装；`-b` 选项需 ≥ 2.28（更老版本脚本自动回退） | `git --version` |
| 管理通道 | root 或 sudo 可用（建用户必需） | `id -u`；`command -v sudo` |

`AllowUsers` 是最容易被忽略的前置条件：它存在且未列出 git 时，前面 4 项全对，
认证仍会被拒，且客户端只看到 `Permission denied (publickey)` —— 与"公钥没装对"
的症状完全相同。排查顺序见 [`troubleshooting.md`](./troubleshooting.md)。

## 6. 验收判据

置备完成 = 以下全部成立：

```bash
# 1. 远端收敛，无缺口
provision-git-server.sh --host <admin> --repo <ns>/<repo> --check   # exit 0

# 2. 本机解析正确
ssh -G <git-alias> | grep -E '^user '        # user git

# 3. 身份正确
ssh <git-alias> whoami                        # git

# 4. git 协议通路
git ls-remote git@<git-alias>:<ns>/<repo>.git # exit 0（空仓库无输出）

# 5. 写路径（二选一）
#    5a：本机真实 push——客户端无安全软件拦截时首选
git push <git-alias 形式的 remote> <branch>   # 成功
#    5b：服务端写路径判据——本机 DLP 类软件禁推时的回退
ssh <git-alias> 'cd /home/git/<ns>/<repo>.git && touch .w && rm -f .w && echo WRITABLE'
ssh <admin> "stat -c '%U:%G' /home/git/<ns>"            # 应为 git:git
```

第 1、2 项是**静态**判据，3–5 是**动态**判据。只过静态判据就宣称完成是本技能
明令禁止的——采集期间发现的 root/git 缺陷恰好就是"静态看起来对、动态身份错"
的典型（配置文件里明明写着 `User git`）。

若第 5a 项因客户端安全软件拦截而无法执行，**必须改跑 5b 并在报告里显式声明**；
归因对照实验见 [`troubleshooting.md`](./troubleshooting.md) 症状 3b。
