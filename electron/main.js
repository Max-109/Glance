const path = require("node:path");
const fs = require("node:fs");
const http = require("node:http");
const { app, BrowserWindow, ipcMain, nativeTheme } = require("electron");
const { revealWindow } = require("./window-control");

const DEFAULT_WIDTH = Number.parseInt(process.env.GLANCE_WINDOW_WIDTH || "924", 10);
const DEFAULT_HEIGHT = Number.parseInt(
  process.env.GLANCE_WINDOW_HEIGHT || "741",
  10,
);
const NEXT_DEV_URL = process.env.GLANCE_NEXT_DEV_URL || "";

let mainWindow = null;
let isQuitting = false;
let stdinBuffer = "";
let staticServer = null;
let staticServerUrl = "";
let appReady = false;
const pendingCommands = [];

const CONTENT_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

function emit(payload) {
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

function buildWindow() {
  const vibrancy = process.platform === "darwin" ? "under-window" : undefined;
  const visualEffectState = process.platform === "darwin" ? "active" : undefined;

  const window = new BrowserWindow({
    show: false,
    width: DEFAULT_WIDTH,
    height: DEFAULT_HEIGHT,
    minWidth: 640,
    minHeight: 500,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    vibrancy,
    visualEffectState,
    roundedCorners: true,
    resizable: true,
    fullscreenable: false,
    maximizable: false,
    minimizable: false,
    skipTaskbar: true,
    title: "Glance",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      sandbox: false,
      spellcheck: false,
    },
  });

  loadRenderer(window).catch((error) => {
    emit({
      type: "error",
      message: error instanceof Error ? error.message : String(error),
    });
  });

  window.on("show", () => emit({ type: "visible", visible: true }));
  window.on("hide", () => emit({ type: "visible", visible: false }));
  window.on("moved", () => emitBounds(window));
  window.on("resized", () => emitBounds(window));
  window.on("close", (event) => {
    if (isQuitting) {
      return;
    }
    event.preventDefault();
    window.hide();
  });

  return window;
}

async function loadRenderer(window) {
  if (NEXT_DEV_URL) {
    await window.loadURL(NEXT_DEV_URL);
    return;
  }

  const staticOutDir = path.join(process.cwd(), "out");
  const staticIndexPath = path.join(staticOutDir, "index.html");
  if (fs.existsSync(staticIndexPath)) {
    const localUrl = await ensureStaticServer(staticOutDir);
    await window.loadURL(localUrl);
    return;
  }

  const message = [
    "<html><body style='font-family:-apple-system,system-ui;background:#0b0d12;color:#f4f7fb;padding:32px'>",
    "<h1 style='margin:0 0 12px'>Glance UI is not built yet.</h1>",
    "<p style='color:rgba(244,247,251,.72)'>Run <code>next build</code> to generate the static Next.js shell, or launch Electron with <code>GLANCE_NEXT_DEV_URL</code> pointed at your dev server.</p>",
    "</body></html>",
  ].join("");
  await window.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(message)}`);
}

function resolveStaticPath(rootDir, requestPath) {
  const pathname = decodeURIComponent(requestPath.split("?")[0] || "/");
  const relativePath =
    pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  const candidatePath = path.resolve(rootDir, relativePath);
  const requestsNamedAsset = path.extname(relativePath) !== "";
  const isOutsideRoot = path.relative(rootDir, candidatePath).startsWith("..");
  if (isOutsideRoot) {
    return null;
  }
  if (fs.existsSync(candidatePath) && fs.statSync(candidatePath).isFile()) {
    return candidatePath;
  }
  if (requestsNamedAsset) {
    return null;
  }
  return path.join(rootDir, "index.html");
}

function ensureStaticServer(rootDir) {
  if (staticServerUrl) {
    return Promise.resolve(staticServerUrl);
  }

  return new Promise((resolve, reject) => {
    const server = http.createServer((request, response) => {
      try {
        const filePath = resolveStaticPath(rootDir, request.url || "/");
        if (!filePath) {
          response.writeHead(404, {
            "Content-Type": "text/plain; charset=utf-8",
          });
          response.end("Not found.");
          return;
        }
        const extension = path.extname(filePath).toLowerCase();
        const contentType =
          CONTENT_TYPES[extension] || "application/octet-stream";

        response.writeHead(200, { "Content-Type": contentType });
        fs.createReadStream(filePath).pipe(response);
      } catch (error) {
        response.writeHead(500, {
          "Content-Type": "text/plain; charset=utf-8",
        });
        response.end(
          error instanceof Error ? error.message : "Static server failed.",
        );
      }
    });

    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        reject(new Error("Could not start the static UI server."));
        return;
      }
      staticServer = server;
      staticServerUrl = `http://127.0.0.1:${address.port}`;
      resolve(staticServerUrl);
    });
  });
}

function emitBounds(window) {
  const bounds = window.getBounds();
  emit({
    type: "bounds",
    bounds: {
      x: bounds.x,
      y: bounds.y,
      width: bounds.width,
      height: bounds.height,
    },
  });
}

function ensureWindow() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    return mainWindow;
  }
  mainWindow = buildWindow();
  return mainWindow;
}

function applyBounds(window, bounds) {
  if (!bounds) {
    return;
  }

  const nextBounds = {
    x: Number.parseInt(bounds.x, 10),
    y: Number.parseInt(bounds.y, 10),
    width: Number.parseInt(bounds.width, 10),
    height: Number.parseInt(bounds.height, 10),
  };

  if (
    [nextBounds.x, nextBounds.y, nextBounds.width, nextBounds.height].some(
      (value) => Number.isNaN(value),
    )
  ) {
    return;
  }

  window.setBounds(nextBounds, false);
  emitBounds(window);
}

function handleCommand(payload) {
  if (!appReady) {
    pendingCommands.push(payload);
    return;
  }
  const command = String(payload.type || "").trim();
  const window = ensureWindow();

  if (command === "show") {
    revealWindow(app, window, {
      applyBounds,
      bounds: payload.bounds,
      focus: Boolean(payload.focus),
    });
    return;
  }

  if (command === "hide") {
    window.hide();
    return;
  }

  if (command === "focus") {
    revealWindow(app, window, { focus: true });
    return;
  }

  if (command === "terminate") {
    isQuitting = true;
    app.quit();
  }
}

function handleStdinChunk(chunk) {
  stdinBuffer += chunk;
  let newlineIndex = stdinBuffer.indexOf("\n");
  while (newlineIndex >= 0) {
    const line = stdinBuffer.slice(0, newlineIndex).trim();
    stdinBuffer = stdinBuffer.slice(newlineIndex + 1);
    if (line) {
      try {
        handleCommand(JSON.parse(line));
      } catch (error) {
        emit({
          type: "error",
          message: error instanceof Error ? error.message : String(error),
        });
      }
    }
    newlineIndex = stdinBuffer.indexOf("\n");
  }
}

ipcMain.handle("glance:window-control", async (_event, action) => {
  const window = ensureWindow();
  if (action === "hide") {
    window.hide();
    return { ok: true };
  }
  if (action === "focus") {
    revealWindow(app, window, { focus: true });
    return { ok: true };
  }
  return { ok: false };
});

ipcMain.handle("glance:system-theme", async () =>
  nativeTheme.shouldUseDarkColors ? "dark" : "light",
);

app.on("window-all-closed", (event) => {
  event.preventDefault();
});

app.on("before-quit", () => {
  if (staticServer) {
    staticServer.close();
    staticServer = null;
    staticServerUrl = "";
  }
});

app.whenReady().then(() => {
  appReady = true;
  ensureWindow();
  emit({ type: "ready" });
  while (pendingCommands.length > 0) {
    handleCommand(pendingCommands.shift());
  }
});

process.stdin.setEncoding("utf8");
process.stdin.on("data", handleStdinChunk);
process.stdin.on("end", () => {
  isQuitting = true;
  app.quit();
});
