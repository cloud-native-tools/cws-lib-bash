# 自部署共享渲染服务（Self-Deploy the Shared Render Service）

> **⚠️ 环境特定信息（environment-specific）。** 本文件描述的渲染后端地址
> `xuanji-render.aliyun-inc.com:9696-9701` 是**某一个具体执行环境**里自部署的共享渲染服务，
> **并非所有执行环境都能访问该地址**（它依赖该环境的内网 DNS / `/etc/hosts` 映射与运行该服务的主机）。
> 换一个环境时该地址很可能不可达——此时按本指南**自部署**一份等价服务，并把
> `xuanji-render.aliyun-inc.com` 映射到自部署服务即可。本文件是 draw-diagram 前门的**附件参考**，
> 不改变前门「只建模、路由、委派、验收，不渲染」的边界。

## 0. 这是什么

六个绘图引擎共用**一个**多引擎渲染服务，内部由两个程序组成（一个进程管理器统一拉起）：

- `plantuml-server`（JVM / Spring Boot）——plantuml 引擎，端口 9696
- `render-server`（仓库自有 Node 服务）——mermaid / excalidraw / drawio / echarts / d3 五个引擎，端口 9697-9701

**访问模型：一引擎一专用端口，无网关 / 无聚合 / 无代理**——消费方直接按端口访问对应引擎。
该服务的「权威打包形态」是 `xuanji-images` 镜像工厂构建的 `images/service/observability/render/<dist>`
镜像（把下述所有运行时依赖封装在一起）；但**自部署不限于 docker 容器一种形态**——见第 3 节按运行环境选型。

## 1. 渲染后端契约（endpoint contract，与部署形态无关）

无论用哪种形态部署，服务都必须在 `xuanji-render.aliyun-inc.com` 上按下列端口提供**同一套契约**。
被委派的 draw-* 引擎技能按此发请求；前门只用它做**可用性 preflight** 与**部署后验收**。

| 引擎 | 端口 | 程序 | 产物形态 | 请求 |
|------|------|------|----------|------|
| plantuml | 9696 | plantuml-server (JVM) | image | `GET /plantuml/svg/{enc}`、`GET /plantuml/png/{enc}`（PlantUML 编码；app 自带 `/plantuml` 前缀） |
| mermaid | 9697 | render-server (Node) | image | `GET /svg/pako:{state}`、`GET /img/pako:{state}?type=png\|jpeg\|webp`（mermaid.ink 兼容；pako = base64url(zlib(JSON{code,mermaid}))） |
| excalidraw | 9698 | render-server (Node) | image | `POST /svg`、`POST /png`，body = Excalidraw scene JSON（`{elements:[...],appState,files}`） |
| drawio | 9699 | render-server (Node) | image | `POST /svg`、`POST /png`，body = drawio XML（`<mxfile>…`）；服务端用 `xvfb-run -a drawio --export` 无头导出 |
| echarts | 9700 | render-server (Node) | served-HTML | `POST /`，body = ECharts option JSON → 返回自包含交互 HTML；**无图像端点**（`GET /png` → 404） |
| d3 | 9701 | render-server (Node) | served-HTML | `POST /`，body = D3 可视化 JS 片段 → 返回自包含交互 HTML；**无图像端点**（`GET /png` → 404） |

- 五个 Node 引擎端口（9697–9701）均提供 `GET /healthz` → `ok`（存活探针）。
- 渲染器不可用返回 **503 `renderer unavailable: …`**，输入非法返回 **4xx**，**绝不**返回空白 200。
- 产物形态与端口绑定（modality exclusivity）：image 端口不返回 HTML，served-HTML 端口不返回图像。

## 2. 可用性 preflight（每次绘图执行前先探测）

```bash
curl -sf --max-time 5 http://xuanji-render.aliyun-inc.com:9697/healthz && echo OK || echo UNAVAILABLE
```

- **OK** → 后端可用，按既定流程委派引擎渲染，**不做任何部署动作**。
- **UNAVAILABLE**（DNS 不解析 / 超时 / 非 200）→ 进入第 3 节自部署评估；前门此时**提示用户并中断**本次渲染委派
  （不静默降级、不即兴用本地工具自渲染），提示末尾附「要不要考虑自部署?」选项（流程见 SKILL.md Step 2.5）。

## 3. 自部署第 0 步：分析运行环境，选择部署形态（**不要默认 docker**）

自部署的**形态取决于当时的运行环境**——先探测环境能力，再据此选型，并把**推荐形态 + 可选备选**一并交给用户决定。

### 3.1 环境探测清单

```bash
command -v docker  && docker info >/dev/null 2>&1 && echo "docker: usable"   || echo "docker: no/daemon-down"
command -v podman  && echo "podman: present"                                 || echo "podman: absent"
command -v kubectl && kubectl cluster-info >/dev/null 2>&1 && echo "k8s: reachable" || echo "k8s: no"
command -v java    && java -version 2>&1 | head -1                           || echo "java: absent"
command -v node    && node --version                                         || echo "node: absent"
command -v npm     && npm --version                                          || echo "npm: absent"
command -v Xvfb xvfb-run drawio 2>/dev/null                                  || echo "xvfb/drawio: absent"
# registry / 镜像工厂可达性（决定能否 pull 或 build）
getent hosts workspace.code-workspace.cloud reg.docker.alibaba-inc.com 2>/dev/null
ls -d <xuanji-images 仓库根> 2>/dev/null && echo "image factory repo: present" || echo "image factory repo: absent"
```

### 3.2 形态选择矩阵

| 运行环境特征 | 推荐形态 | 一句话理由 |
|--------------|----------|-----------|
| docker 守护进程可用 | **A. docker 容器（最优，默认推荐）** | 一条命令拉起全部依赖（JVM+Node+Chromium+Xvfb+drawio+字体），与权威镜像一致 |
| 无 docker，但有 podman | **B. podman（rootless 容器）** | docker CLI 基本兼容，可 rootless，无需守护进程 |
| 有可达的 k8s 集群 | **C. Kubernetes（Deployment + Service）** | 声明式、可编排/自愈；适合已有集群的环境 |
| 仅裸机 + 包管理器，无任何容器运行时 | **D. 裸机进程（systemd / supervisord）** | 在执行环境自装运行时依赖后直接跑两个程序；最复杂、最后选 |

> **最优是 A（docker 容器化）**：所有运行时依赖都封装在镜像里，部署=拉镜像+起容器，最省心、最可复现。
> B/C 复用同一镜像，差别只在编排方式。**D（裸机）是没有任何容器运行时时的兜底**——需要在执行环境逐项满足
> 第 7 节的依赖清单（这正是镜像本已封装好的东西），最易出错。无论选哪种，**第 1 节的端口契约与第 8/9 节的
> hosts 映射、验收都完全一致**。让用户在「推荐 A + 环境允许的备选」中拍板。

## 4. 形态 A：docker 容器（最优，推荐）

### 4.A.1 取得镜像

**A1 —— 镜像构建（image-build，从 `xuanji-images` 工厂自建；用户偏好的自部署方式）**

```bash
cd <xuanji-images 仓库根>            # 本环境为 /storage/project/kangaroo-xuanji/xuanji-images
source bin/cws_images_env && source .venv/bin/activate && cws_images_resolve_tag
cws_py_cmd cmdline-generate-docker-build                 # 生成 Dockerfile / docker-build.sh
cd images/service/observability/render/<dist> && bash docker-build.sh   # <dist>: ubuntu-jammy / alios-8 / alinux-3
```

- 构建依赖链须先可构建/可拉取：`images-daemon-<dist>`、`images-fetcher-language-java-jdk-21-dragonwell`、
  `images-project-sig-cloud-native-tools-plantuml-server-<dist>`、`images-shared-project-...-plantuml-server`、
  `images-fetcher-language-javascript-nodejs-<ver>`、`images-fetcher-language-javascript-ms-playwright`、
  `images-shared-observability-render`、`images-fetcher-observability-drawio-desktop`。
- **drawio 依赖**：`images-fetcher-observability-drawio-desktop` 需从 github 下载 draw.io Desktop 四个包
  （amd64/arm64 的 .deb/.rpm，约 119MB/个）。github release 资产直连可能极慢——优先走仓库的 **DockerHost 镜像
  加速机制**（fetcher 目录 `DockerHost.workspace.tpl` 把 `github.com` 等映射到内网 mirror，生成的 `docker-build.sh`
  带 `--add-host`）；mirror 缺件时先把包同步到 mirror 再构建。
- 产物镜像名形如 `reg.docker.alibaba-inc.com/cws-images/images-service-observability-render-<dist>:<tag>`。

**A2 —— 从 registry 拉取（若该环境 registry 可达，更快）**

```bash
docker pull workspace.code-workspace.cloud/cws-images/images-service-observability-render-<dist>:<tag>
# 或 reg.docker.alibaba-inc.com/cws-images/images-service-observability-render-<dist>:<tag>（需先 docker login）
```

### 4.A.2 启动容器（只发布 9696-9701）

```bash
docker rm -f render >/dev/null 2>&1
docker run -d --name render --restart unless-stopped \
  -p 9696:9696 -p 9697:9697 -p 9698:9698 -p 9699:9699 -p 9700:9700 -p 9701:9701 \
  <image>
docker exec render supervisorctl -c /etc/supervisor/supervisord.ini status   # plantuml-server / render-server 均 RUNNING
```

- **只发布 9696-9701**：daemon 层还含 sshd(10022) 等；若主机 80/443/10022 已被占用，不要发布它们。
- 若主机已有**旧单引擎 plantuml 容器**占用 9696：本服务的 plantuml 与其**字节级等价**（同 jar、同 `/plantuml`
  前缀、同端口），可**可逆地**停掉旧容器再起 render（`docker stop <旧容器>`，保留以便回滚），plantuml 消费方无感知。

## 5. 形态 B：podman（rootless，无 docker 时）

与形态 A 几乎一致（podman CLI 兼容 docker），差别是无守护进程、默认 rootless：

```bash
# 取得镜像：podman pull <registry>/<image>:<tag>；或在 xuanji-images 工厂用 podman 作为构建引擎构建
podman rm -f render >/dev/null 2>&1
podman run -d --name render --restart=always \
  -p 9696:9696 -p 9697:9697 -p 9698:9698 -p 9699:9699 -p 9700:9700 -p 9701:9701 \
  <image>
podman exec render supervisorctl -c /etc/supervisor/supervisord.ini status
```

- rootless 下发布 <1024 端口需额外配置；本服务端口均 >1024，无此问题。
- drawio 的 `xvfb-run` 在 rootless 容器内同样可用（镜像已含 Xvfb）。

## 6. 形态 C：Kubernetes（已有集群时）

用同一镜像跑一个 Deployment，Service 暴露 9696-9701（NodePort 或 LoadBalancer），再把
`xuanji-render.aliyun-inc.com` 映射到节点/LB 的可达 IP：

```yaml
# render.yaml（示意；<image> 用 registry 上的渲染镜像）
apiVersion: apps/v1
kind: Deployment
metadata: { name: render }
spec:
  replicas: 1
  selector: { matchLabels: { app: render } }
  template:
    metadata: { labels: { app: render } }
    spec:
      containers:
        - name: render
          image: <image>
          ports: { containerPort: 9696 }, { containerPort: 9697 }, { containerPort: 9698 },
                 { containerPort: 9699 }, { containerPort: 9700 }, { containerPort: 9701 }
          readinessProbe: { httpGet: { path: /healthz, port: 9697 } }
---
apiVersion: v1
kind: Service
metadata: { name: render }
spec:
  type: NodePort            # 或 LoadBalancer
  selector: { app: render }
  ports:
    - { name: plantuml,   port: 9696, targetPort: 9696, nodePort: 30696 }
    - { name: mermaid,    port: 9697, targetPort: 9697, nodePort: 30697 }
    - { name: excalidraw, port: 9698, targetPort: 9698, nodePort: 30698 }
    - { name: drawio,     port: 9699, targetPort: 9699, nodePort: 30699 }
    - { name: echarts,    port: 9700, targetPort: 9700, nodePort: 30700 }
    - { name: d3,         port: 9701, targetPort: 9701, nodePort: 30701 }
```

```bash
kubectl apply -f render.yaml && kubectl rollout status deploy/render
# NodePort 形态下消费方端口=nodePort（30696-30701）：要么让消费方用 nodePort，要么在节点上用
# socat/iptables 把 9696-9701 转发到对应 nodePort，使第 1 节契约端口保持不变（推荐后者，契约稳定）。
```

> 注意：契约端口（9696-9701）是消费方依赖的稳定面。k8s NodePort 落在 30000+ 段，需用转发把节点上的
> 9696-9701 指到对应 nodePort，或改用 LoadBalancer/hostPort 直接呈现 9696-9701，避免改动消费方契约。

## 7. 形态 D：裸机进程（无任何容器运行时；最复杂，兜底）

没有容器运行时时，需在执行环境**手工补齐镜像本已封装的运行时依赖**，再用进程管理器拉起两个程序。

### 7.1 运行时依赖清单

| 程序 | 依赖 | 安装/取得 |
|------|------|-----------|
| plantuml-server (9696) | JDK 21；graphviz(`dot`)；freetype+fontconfig+CJK 字体；`plantuml.jar` | 包管理器装 JDK21/graphviz/字体；jar 从 plantuml-server 构建镜像 `docker cp` 取出，或从源码构建，或上游 release |
| render-server (9697-9701) | Node.js ≥18（镜像用 25.9.0）；render-server 源码 + `npm install --omit=dev`；headless Chromium + 其共享库；`CHROME_PATH`/`PUPPETEER_EXECUTABLE_PATH` 指向 chromium | Node 官网/包管理器；源码取 `xuanji-images` 仓库 `images/shared/observability/render/render-server/`；Chromium 用 `npx playwright install --with-deps chromium` 或系统 chromium |
| drawio 引擎 (9699) | `xvfb` + `xauth`；draw.io Desktop（提供 `drawio` 可执行） | 包管理器装 xvfb/xauth；draw.io Desktop 装 github release 的 .deb/.rpm（或 mirror），确保 `command -v drawio` |

> 没有 drawio/xvfb 时，drawio 引擎会在 `:9699` 返回 503/422（其余五引擎不受影响）；可先部署五引擎，drawio 后补。

### 7.2 拉起两个程序（systemd 或 supervisord 或 nohup）

```bash
# plantuml-server（9696）
PLANTUML_HTTP_SERVER_PORT=9696 java -jar /opt/render/plantuml.jar &
# render-server（9697-9701）；CHROME_PATH 指向已安装的 chromium
cd /opt/render/render-server && npm install --omit=dev
CHROME_PATH="$(command -v chromium || command -v chromium-browser)" \
PUPPETEER_EXECUTABLE_PATH="$CHROME_PATH" node server.js &
```

- 生产化建议用 **systemd 两个 unit** 或 **supervisord**（与镜像内一致：`[program:plantuml-server]` +
  `[program:render-server]`）托管，获得开机自启/自愈/统一日志。
- 两个程序都监听 `0.0.0.0`，端口即第 1 节契约端口；无需网关。

## 8. 通用收尾：把 `xuanji-render.aliyun-inc.com` 指向自部署服务（所有形态）

确定自部署服务的**可达 IP `<RENDER_IP>`**（运行 draw-diagram 的执行环境要能访问到它；docker/podman=宿主机 IP，
k8s=节点或 LB IP，裸机=该主机 IP），然后在**执行 draw-diagram 的环境**写入 hosts 映射：

```bash
echo "<RENDER_IP>  xuanji-render.aliyun-inc.com" | sudo tee -a /etc/hosts
getent hosts xuanji-render.aliyun-inc.com   # 应解析到 <RENDER_IP>
```

> 写完后，**后续每次绘图都从第 2 节 preflight 直接命中可用后端，不再重复部署**——这正是把消费方契约名固定成
> `xuanji-render.aliyun-inc.com` 的目的：契约不变，真实后端落在哪台主机/哪种形态由 hosts 映射兜底。

## 9. 通用验收：六引擎逐一渲染（所有形态）

```bash
H=xuanji-render.aliyun-inc.com
curl -sf --max-time 5 http://$H:9697/healthz                                                       # -> ok
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' "http://$H:9696/plantuml/svg/<enc>"        # -> 200 image/svg+xml
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' "http://$H:9697/svg/pako:<state>"          # -> 200 image/svg+xml
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' -X POST --data-binary @scene.json   "http://$H:9698/svg"  # -> 200 image/svg+xml
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' -X POST --data-binary @diag.drawio  "http://$H:9699/svg"  # -> 200 image/svg+xml
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' -X POST --data-binary @option.json  "http://$H:9700/"     # -> 200 text/html
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' -X POST --data-binary @viz.js      "http://$H:9701/"     # -> 200 text/html
```

六项全 200 且 content-type 与产物形态一致即部署成功；任一失败先查服务日志（docker/podman: `docker logs render`；
k8s: `kubectl logs deploy/render`；裸机: 对应 systemd/journal 或 stdout 日志）。

## 10. 回滚与清理

- docker/podman：`docker rm -f render`（如停过旧 plantuml：`docker start <旧容器>` 恢复）。
- k8s：`kubectl delete -f render.yaml`。
- 裸机：停掉两个进程 / `systemctl disable --now plantuml-server render-server`。
- 撤销 hosts 映射：从 `/etc/hosts` 删除 `xuanji-render.aliyun-inc.com` 那一行。

## 11. 红线（MUST NOT）

- 后端不可达时**不得**静默降级为「用本地 mermaid-cli / plantuml.jar 即兴自渲染」绕过——这会脱离统一渲染后端、
  产物不可对照契约验收。正确做法：preflight 失败 → 提示用户并中断 → 提供自部署选项。
- **不得**默认假定 docker 一定可用而跳过第 3 节的环境分析；形态须按当时运行环境选型，docker 只是**最优默认**而非唯一。
- **不得**把环境特定地址 `xuanji-render.aliyun-inc.com` 当作「所有环境都可达」的硬编码前提；它只是由 hosts 映射兜底的
  稳定消费方契约名，真实后端主机/形态随环境而变。
- 自部署**不得**改动 draw-* 引擎技能源码或前门路由逻辑——它只提供一个与第 1 节契约等价的渲染后端。
