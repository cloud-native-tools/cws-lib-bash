// build.mjs — bundle the in-browser render entry (Excalidraw export utils) into
// a single IIFE script served by server.mjs. Run: npm run build
import * as esbuild from "esbuild";
import { mkdirSync } from "node:fs";

mkdirSync(new URL("./static/dist/", import.meta.url), { recursive: true });

await esbuild.build({
  entryPoints: [new URL("./static/render-entry.js", import.meta.url).pathname],
  bundle: true,
  format: "iife",
  outfile: new URL("./static/dist/render.js", import.meta.url).pathname,
  assetNames: "assets/[name]-[hash]",
  loader: {
    ".woff2": "file",
    ".woff": "file",
    ".ttf": "file",
    ".otf": "file",
    ".png": "file",
  },
  define: {
    "process.env.NODE_ENV": '"production"',
    global: "window",
  },
  minify: true,
  sourcemap: false,
  logLevel: "info",
});

console.log("[build] done -> static/dist/render.js");
