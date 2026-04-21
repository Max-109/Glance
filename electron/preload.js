const { contextBridge, ipcRenderer } = require("electron");

const bridgeUrl = process.env.GLANCE_BRIDGE_URL || "";
const runtimeStatusListeners = new Map();
let nextRuntimeSubscriptionId = 1;

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
  subscribeRuntimeStatus: (callback) => {
    const subscriptionId = nextRuntimeSubscriptionId;
    nextRuntimeSubscriptionId += 1;
    const listener = (_event, payload) => callback(payload);
    runtimeStatusListeners.set(subscriptionId, listener);
    ipcRenderer.on("glance:runtime-status", listener);
    return subscriptionId;
  },
  unsubscribeRuntimeStatus: (subscriptionId) => {
    const listener = runtimeStatusListeners.get(subscriptionId);
    if (!listener) {
      return;
    }
    runtimeStatusListeners.delete(subscriptionId);
    ipcRenderer.removeListener("glance:runtime-status", listener);
  },
});
