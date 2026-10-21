# git-delta 安装与配置

> `code-review` Skill 的核心渲染引擎。`diff`/`review` 子命令依赖 delta；`note`/`report` 不需要。
> 原则：环境缺失时**报错 + 给出安装命令后停止**，由用户安装，脚本不自动安装。

## 一、安装

| 平台 | 命令 |
|------|------|
| macOS (Homebrew) | `brew install git-delta` |
| Debian/Ubuntu | `sudo apt install git-delta`（或下载 `.deb`：`dpkg -i git-delta_*.deb`） |
| Alpine | `apk add delta`（community 仓库）或用下方预编译包 |
| Cargo | `cargo install git-delta` |
| 预编译包 | 从 <https://github.com/dandavison/delta/releases> 下载对应架构 tar.gz，解压后将 `delta` 放入 `PATH` |

验证：`delta --version`。

## 二、推荐 git 全局配置

让原生 `git diff`/`git log` 也走 delta 渲染（脚本之外同样受益）：

```bash
git config --global core.pager "delta"
git config --global delta.side-by-side true        # 左右分栏（接近 GitHub PR 视图）
git config --global delta.line-numbers true        # 行号
git config --global delta.navigate true            # n/N 在文件间跳转
git config --global interactive.diffFilter "delta --color-only"
git config --global merge.conflictStyle "diff3"
```

终端宽度不足时 side-by-side 会自动回退为行内模式；可临时用 `git-delta-review.sh diff`（不带 `-s`）强制行内。

## 三、容器集成（Dockerfile 片段）

```dockerfile
FROM alpine:3.20
RUN apk add --no-cache git bash curl
# 单二进制安装 delta (~12MB)
RUN curl -sL https://github.com/dandavison/delta/releases/download/0.18.2/delta-0.18.2-x86_64-unknown-linux-musl.tar.gz \
    | tar xz -C /usr/local/bin --strip-components=1
# 安装 skill 脚本
COPY git-delta-review.sh /usr/local/bin/git-delta-review
RUN chmod +x /usr/local/bin/git-delta-review
WORKDIR /workspace
```

使用：`docker run --rm -it -v $(pwd):/workspace <image>`，容器内 `git-delta-review review --since main`。

## 四、故障排查

| 症状 | 原因 | 处理 |
|------|------|------|
| `delta not found` | 未安装或不在 `PATH` | 按上表安装；或用 `DELTA_BIN=/path/to/delta` 指定 |
| side-by-side 显示错乱 | 终端宽度不足 / 非 UTF-8 locale | 加宽终端；`export LANG=C.UTF-8`；或去掉 `--side-by-side` |
| CI 中输出卡在分页器 | stdout 是 tty 时分页器等待输入 | CI 使用 `note`/`report`（无 delta 依赖），或设 `GIT_PAGER=cat` |
| `基准引用不存在: main` | 仓库主分支名不是 main | `--since master` 或 `GIT_BASE=master` |
| diff 无颜色 | 非 tty 输出 | 正常现象（delta 自动关色）；强制：`--color-only` 场景除外 |
| `cargo install git-delta` 报 `edition2024` / lock file version 4 | 系统 cargo 过旧，依赖解析漂移到需新版 Rust 的版本 | 配置 rsproxy 镜像；从 `~/.cargo/registry/src/*/git-delta-<旧版本>/` 复制源码后 `cargo install --path . --locked`（crate 自带 v3 lockfile 锁定旧依赖，兼容老 cargo；本环境 cargo 1.75 + delta 0.18.2 验证通过） |
