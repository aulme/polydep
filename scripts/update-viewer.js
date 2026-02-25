import { copyFileSync } from "node:fs";

copyFileSync(
  "node_modules/fishtail/dist/viewer.bundle.js",
  "src/polydep/static/viewer.bundle.js",
);

console.log("Updated src/polydep/static/viewer.bundle.js from fishtail npm package.");
