const { contextBridge, ipcRenderer } = require("electron");

const bridgeUrl = process.env.GLANCE_BRIDGE_URL || "";

async function request(path, options = {}) {
  const response = await fetch(`${bridgeUrl}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || `Bridge request failed for ${path}.`);
  }
  return payload.state;
}

contextBridge.exposeInMainWorld("glanceBridge", {
  getState: () => request("/api/state", { method: "GET" }),
  getAudioState: () => request("/api/audio-state", { method: "GET" }),
  setSection: (section) =>
    request("/api/section", {
      method: "POST",
      body: JSON.stringify({ section }),
    }),
  setField: (fieldName, value) =>
    request("/api/field", {
      method: "POST",
      body: JSON.stringify({ fieldName, value }),
    }),
  runAction: (action, payload = {}) =>
    request("/api/action", {
      method: "POST",
      body: JSON.stringify({ action, ...payload }),
    }),
  assignKeybind: (fieldName, keybind) =>
    request("/api/keybind", {
      method: "POST",
      body: JSON.stringify({ fieldName, keybind }),
    }),
  hideWindow: () => ipcRenderer.invoke("glance:window-control", "hide"),
  focusWindow: () => ipcRenderer.invoke("glance:window-control", "focus"),
  getSystemTheme: () => ipcRenderer.invoke("glance:system-theme"),
});
