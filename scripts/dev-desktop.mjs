import { spawn } from "node:child_process";

const host = process.env.GLANCE_DEV_HOST || "127.0.0.1";
const port = process.env.GLANCE_DEV_PORT || "3000";
const devUrl = `http://${host}:${port}`;
const bunCommand = process.env.BUN_BIN || "bun";
const pythonCommand = process.env.GLANCE_PYTHON || "./venv/bin/python";
const supportsProcessGroups = process.platform !== "win32";

let shuttingDown = false;
let desktopProcess = null;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForServer(url, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, { redirect: "manual" });
      if (response.ok || response.status === 404) {
        return;
      }
    } catch {
      // Keep polling until the dev server is ready.
    }
    await sleep(350);
  }
  throw new Error(`Next.js dev server did not become ready at ${url} in time.`);
}

function terminateChild(child, signal = "SIGTERM") {
  if (!child || child.exitCode !== null || child.pid === undefined) {
    return;
  }

  if (supportsProcessGroups) {
    try {
      process.kill(-child.pid, signal);
      return;
    } catch (error) {
      if (!(error instanceof Error) || error.code !== "ESRCH") {
        throw error;
      }
      return;
    }
  }

  child.kill(signal);
}

function forwardExit(code) {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;
  terminateChild(desktopProcess);
  terminateChild(nextProcess);
  process.exit(code);
}

const nextProcess = spawn(
  bunCommand,
  ["run", "dev", "--", "--hostname", host, "--port", port],
  {
    stdio: "inherit",
    detached: supportsProcessGroups,
    env: process.env,
  },
);

nextProcess.on("error", (error) => {
  console.error(
    error instanceof Error ? error.message : "Could not start the Next.js dev server.",
  );
  forwardExit(1);
});

nextProcess.on("exit", (code, signal) => {
  if (shuttingDown) {
    return;
  }
  if (signal) {
    forwardExit(1);
    return;
  }
  forwardExit(code ?? 0);
});

process.on("SIGINT", () => forwardExit(0));
process.on("SIGTERM", () => forwardExit(0));

try {
  await waitForServer(devUrl);
  desktopProcess = spawn(pythonCommand, ["main.py"], {
    stdio: "inherit",
    detached: supportsProcessGroups,
    env: {
      ...process.env,
      GLANCE_NEXT_DEV_URL: devUrl,
      GLANCE_AUTO_OPEN: "1",
    },
  });
} catch (error) {
  console.error(
    error instanceof Error ? error.message : "Desktop dev launcher failed.",
  );
  forwardExit(1);
}

desktopProcess.on("error", (error) => {
  console.error(
    error instanceof Error ? error.message : "Could not start the Python desktop app.",
  );
  forwardExit(1);
});

desktopProcess.on("exit", (code, signal) => {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;
  terminateChild(nextProcess);
  if (signal) {
    process.exit(1);
    return;
  }
  process.exit(code ?? 0);
});
