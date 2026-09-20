# mermaid-render-server — mermaid.ink 兼容渲染服务器（内网自建，仿照 plantuml-server 容器模式）
#
# 与 draw-mermaid 技能 render-mermaid.sh 的远端后端协议完全一致：
#   GET /svg/pako:{base64}                     -> SVG
#   GET /img/pako:{base64}?type=png|jpeg|webp  -> 位图（默认 png）
# 其中 base64 = zlib(JSON {code, mermaid:{theme, themeVariables, ...}})
#
# 构建（可推送到内网镜像仓库，如 reg.docker.alibaba-inc.com/...）：
#   docker build -t reg.docker.alibaba-inc.com/cws-images/images-mermaid-server:1.0.0 .
#
# 运行：
#   docker run -d --name mermaid-server --restart unless-stopped \
#     -p 9696:9696 reg.docker.alibaba-inc.com/cws-images/images-mermaid-server:1.0.0
#
# 说明：Chromium 与 Noto CJK 字体通过 apt 安装（内网 apt 镜像友好），
# 构建与运行均无需下载 Chrome。

FROM node:20-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      chromium \
      fonts-noto-cjk \
      fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev
COPY server.js ./

ENV PORT=9696 \
    CHROME_PATH=/usr/bin/chromium
EXPOSE 9696

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD node -e "require('http').get('http://127.0.0.1:'+(process.env.PORT||9696)+'/healthz',r=>process.exit(r.statusCode===200?0:1)).on('error',()=>process.exit(1))"

CMD ["node", "server.js"]
