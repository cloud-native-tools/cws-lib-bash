# excalidraw-render-server — self-hosted Excalidraw render service
# POST scene JSON / Mermaid text -> SVG/PNG, driven by the real
# @excalidraw/excalidraw export pipeline inside headless Chromium.
#
# Build & run:
#   docker build -t excalidraw-render .
#   docker run -d --name excalidraw-render -p 8383:8383 excalidraw-render
#
# Used by the draw-excalidraw skill (render-excalidraw.sh, EXCALIDRAW_SERVER).

FROM node:22-bookworm-slim

# Chromium (renderer) + CJK/emoji fonts (diagram text) + curl (healthcheck).
RUN apt-get update && apt-get install -y --no-install-recommends \
      chromium \
      fonts-noto-cjk \
      fonts-noto-color-emoji \
      curl \
    && rm -rf /var/lib/apt/lists/*

ENV EXCALIDRAW_CHROMIUM_PATH=/usr/bin/chromium \
    EXCALIDRAW_HOST=0.0.0.0 \
    EXCALIDRAW_PORT=8383

WORKDIR /app

COPY package.json ./
RUN npm install --no-audit --no-fund

COPY build.mjs server.mjs ./
COPY static ./static
RUN npm run build

EXPOSE 8383
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fs http://127.0.0.1:8383/health || exit 1

CMD ["node", "server.mjs"]
