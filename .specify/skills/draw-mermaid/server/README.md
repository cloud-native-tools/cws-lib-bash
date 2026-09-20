# Mermaid 渲染服务器（内网自建部署）

> 仿照 `xuanji-images/.../plantuml-server` 的容器化模式，为 draw-mermaid 技能提供**自建的 mermaid.ink 兼容渲染服务器**。协议与 `render-mermaid.sh` 的远端后端完全一致，部署后只需 `export MERMAID_SERVER=http://<内网地址>:9696` 即可切换。

## 1. 协议（与 mermaid.ink 一致）

| 端点 | 说明 |
|------|------|
| `GET /svg/pako:{base64}` | 返回 SVG |
| `GET /img/pako:{base64}?type=png\|jpeg\|webp` | 返回位图（默认 png） |
| `GET /healthz` | 健康检查（Docker HEALTHCHECK 用） |

`base64 = zlib(JSON {"code": "<图表源码>", "mermaid": {"theme": ..., "themeVariables": ...}})`（即 mermaid.ink 官方 `pako:` state 协议；也兼容裸 base64 JSON / 裸 base64 源码）。`render-mermaid.sh` 的 `mermaid_state_encode()` 已按此编码，开箱即用。

## 2. 构建镜像

```bash
cd skills/draw-mermaid/server
docker build -t reg.docker.alibaba-inc.com/cws-images/images-mermaid-server:1.0.0 .
# 内网镜像仓库（如 alibaba-inc registry）：
docker push reg.docker.alibaba-inc.com/cws-images/images-mermaid-server:1.0.0
```

- 基础镜像 `node:20-slim`；若需与 xuanji cws 管道对齐，可把 `FROM` 换成内部 node 基础镜像，并把构建产物并入 fetcher/shared/project 三层（与 `plantuml-server` 的 `alinux-3/Dockerfile` 同构：`COPY --from=fetcher ... mermaid-server` + 运行层）。
- **Chromium 与 Noto CJK 字体通过 apt 安装**（`chromium` + `fonts-noto-cjk`），构建/运行均不下载 Chrome，内网 apt 镜像即可满足。

## 3. 运行

```bash
# 简单方式（等价于 plantuml-server 的 docker-run.sh 简化版）
bash skills/draw-mermaid/server/docker-run.sh            # 默认 9696
# 或手动：
docker run -d --name mermaid-server --restart unless-stopped \
  -p 9696:9696 reg.docker.alibaba-inc.com/cws-images/images-mermaid-server:1.0.0
```

## 4. 接入 draw-mermaid（render-mermaid.sh）

```bash
export MERMAID_SERVER=http://<内网主机>:9696
bash skills/draw-mermaid/scripts/render-mermaid.sh figure.mmd figures/ figure
# → 走内网服务器渲染（默认后端即 server，远端优先）
```

如需带上下文路径（如 `/mermaid/`，仿 plantuml 的 `/plantuml/`），用 nginx 反代并**剥离前缀**：

```nginx
location /mermaid/ {
    proxy_pass http://127.0.0.1:9696/;   # 末尾 / 表示剥离 /mermaid/ 前缀
    proxy_read_timeout 120s;
}
# 然后 export MERMAID_SERVER=http://<nginx主机>/mermaid
```

## 5. 验证

```bash
# 1) 健康检查
curl -s http://<host>:9696/healthz           # → ok
# 2) 用技能脚本直出（最直接）：先 export MERMAID_SERVER，再跑 render-mermaid.sh，Read 检查产物
# 3) 手工协议验证（python 生成 pako state）：
python3 - <<'EOF'
import json, zlib, base64, urllib.request
code = "flowchart TD\nA[开始] --> B{条件}\nB -- 是 --> C[处理]"
state = base64.b64encode(zlib.compress(json.dumps({"code": code, "mermaid": {"theme": "default"}}).encode())).decode()
print(urllib.request.urlopen(f"http://<host>:9696/svg/pako:{state}").status)
EOF
```

## 6. 备选方案：社区自托管镜像

- **ghcr.io/jihchi/mermaid.ink**（mermaid.ink 社区自托管版，端口 3000）：`docker run --cap-add=SYS_ADMIN -p 3000:3000 ghcr.io/jihchi/mermaid.ink`。**部署前先验证其协议与本技能一致**（用 §5 第 3 步的 pako 请求测 `/svg/` 与 `/img/`）；若一致即可直接 `export MERMAID_SERVER=http://<host>:3000`，否则用本目录的自研镜像。

## 7. 生产注意

- 本服务器无鉴权——只暴露在内网 / 加 nginx 访问控制；
- `MAX_STATE_BYTES`（默认 1MB）防大状态滥用；`RENDER_TIMEOUT`（默认 60s）防慢图挂死；
- 并发高时给容器限资源（`--cpus` / `--memory`），必要时前置队列；
- 图表源码会明文到达本服务器——内网部署可避免图源出网（与 plantuml-server 同理由）。
