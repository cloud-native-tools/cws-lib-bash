// render-entry.js — bundled into static/dist/render.js and loaded by render.html.
// Exposes two functions on window for the render server to call via page.evaluate:
//   window.__renderScene(payload)  : Excalidraw scene JSON -> SVG string / PNG dataURL
//   window.__mermaidToScene(payload): Mermaid text -> Excalidraw { elements, files }
//
// Uses the REAL @excalidraw/excalidraw export pipeline (restore + exportToSvg /
// exportToBlob), so output is identical to excalidraw.com's own export.

import {
  exportToSvg,
  exportToBlob,
  restore,
  convertToExcalidrawElements,
} from "@excalidraw/excalidraw";
import { parseMermaidToExcalidraw } from "@excalidraw/mermaid-to-excalidraw";

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

// Normalize a (possibly partial, agent-generated) scene through Excalidraw's
// own restore(), which fills in defaults (seed, version, missing props).
function normalizeScene(payload) {
  const scene = payload.scene ?? payload;
  const data = restore(
    {
      type: "excalidraw",
      version: 2,
      elements: scene.elements ?? [],
      appState: scene.appState ?? {},
      files: scene.files ?? {},
    },
    null,
    null,
    true // refreshDimensions: recompute text metrics with real browser fonts;
         // also re-centers container-bound text
  );
  if (!data) throw new Error("restore() rejected the scene");
  return data;
}

window.__renderScene = async function (payload) {
  const { elements, appState, files } = normalizeScene(payload);
  const format = payload.format === "png" ? "png" : "svg";
  const scale = Number(payload.scale) > 0 ? Number(payload.scale) : 2;
  const opts = {
    elements,
    appState: {
      ...appState,
      exportBackground: payload.exportBackground ?? true,
      viewBackgroundColor:
        payload.viewBackgroundColor ?? appState.viewBackgroundColor ?? "#ffffff",
      exportWithDarkMode: payload.darkMode ?? false,
    },
    files,
    exportPadding: payload.padding ?? 16,
  };

  if (format === "svg") {
    const svg = await exportToSvg(opts);
    return { format: "svg", data: svg.outerHTML };
  }

  const blob = await exportToBlob({
    ...opts,
    mimeType: payload.mime === "image/jpeg" ? "image/jpeg" : "image/png",
    quality: 0.92,
    getDimensions: (w, h) => ({ width: w * scale, height: h * scale, scale }),
  });
  return { format: "png", data: await blobToDataUrl(blob) };
};

// Mermaid text -> normalized Excalidraw elements.
// parseMermaidToExcalidraw returns an intermediate format where labels live in
// a `label` sub-object; convertToExcalidrawElements turns them into proper
// bound-text elements (this is what excalidraw.com's own import does).
async function parseMermaid(payload) {
  const { elements: raw, files } = await parseMermaidToExcalidraw(
    payload.mermaid,
    payload.config ?? {}
  );
  return { elements: convertToExcalidrawElements(raw), files };
}

window.__mermaidToScene = async function (payload) {
  const { elements, files } = await parseMermaid(payload);
  return { elements, files };
};

// Mermaid text -> Excalidraw scene -> SVG/PNG in one page round-trip.
window.__renderMermaidScene = async function (payload) {
  const { elements, files } = await parseMermaid(payload);
  return window.__renderScene({
    scene: {
      elements,
      files,
      appState: { viewBackgroundColor: "#ffffff" },
    },
    format: payload.format,
    scale: payload.scale,
    padding: payload.padding,
    viewBackgroundColor: payload.viewBackgroundColor,
    darkMode: payload.darkMode,
    exportBackground: payload.exportBackground,
    mime: payload.mime,
  });
};

window.__renderReady = true;
