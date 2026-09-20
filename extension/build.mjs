import { build } from "esbuild";
import { cpSync, mkdirSync, rmSync } from "fs";

rmSync("dist", { recursive: true, force: true });
mkdirSync("dist", { recursive: true });

await build({
  entryPoints: {
    background: "src/background.ts",
    "content/index": "src/content/index.ts",
    "popup/main": "src/popup/main.tsx",
  },
  bundle: true,
  outdir: "dist",
  format: "esm",
  target: "chrome110",
  sourcemap: true,
});

cpSync("manifest.json", "dist/manifest.json");
cpSync("src/popup/index.html", "dist/popup/index.html");
// no icons yet — fine for `chrome://extensions` "Load unpacked" (dev/testing),
// but add manifest.icons + real PNGs before a Chrome Web Store submission.

console.log("Built extension into dist/");
