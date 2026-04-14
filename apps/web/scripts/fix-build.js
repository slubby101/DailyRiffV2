// OPT-IN workaround for OneDrive EIO errors during `next build` cleanup.
// Next.js fails to rmdir .next/export on OneDrive-synced paths even when
// the build itself succeeded. This script is invoked ONLY via the
// `pnpm --filter web build:onedrive` script — NEVER from the main `build`
// script and NEVER in CI. CI runs plain `next build` so real failures
// surface correctly. Do not wire this into the primary build chain.
const fs = require("fs");
const path = require("path");

const dotNext = path.join(__dirname, "..", ".next");

if (!fs.existsSync(path.join(dotNext, "BUILD_ID"))) {
  console.error("Build failed — BUILD_ID not found");
  process.exit(1);
}

function retryRm(dir, retries) {
  for (let i = 0; i < retries; i++) {
    try {
      if (fs.existsSync(dir)) {
        fs.rmSync(dir, { recursive: true, force: true });
      }
      return;
    } catch {
      if (i < retries - 1) {
        const { execSync } = require("child_process");
        execSync("sleep 1");
      }
    }
  }
  // If we still can't remove it, that's okay — it won't break next start
}

retryRm(path.join(dotNext, "export"), 3);

const manifest = path.join(dotNext, "prerender-manifest.json");
if (!fs.existsSync(manifest)) {
  fs.writeFileSync(
    manifest,
    JSON.stringify({
      version: 4,
      routes: {
        "/": {
          initialRevalidateSeconds: false,
          srcRoute: "/",
          dataRoute: null,
        },
        "/404": {
          initialRevalidateSeconds: false,
          srcRoute: "/404",
          dataRoute: null,
        },
      },
      dynamicRoutes: {},
      notFoundRoutes: [],
      preview: {
        previewModeId: "disabled",
        previewModeSigningKey: "disabled",
        previewModeEncryptionKey: "disabled",
      },
    })
  );
}

console.log("Build artifacts recovered successfully");
