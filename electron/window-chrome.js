function isMacPlatform(platform = process.platform) {
  return platform === "darwin";
}

function buildWindowChromeOptions(platform = process.platform) {
  const isMac = isMacPlatform(platform);

  return {
    frame: isMac,
    transparent: true,
    backgroundColor: "#00000000",
    titleBarStyle: isMac ? "hiddenInset" : undefined,
    vibrancy: isMac ? "sidebar" : undefined,
    visualEffectState: isMac ? "active" : undefined,
    roundedCorners: true,
    resizable: true,
    fullscreenable: false,
    maximizable: false,
    minimizable: false,
    skipTaskbar: true,
  };
}

function applyWindowChrome(window, platform = process.platform) {
  if (!isMacPlatform(platform)) {
    return;
  }

  window.setWindowButtonVisibility(true);
}

module.exports = {
  applyWindowChrome,
  buildWindowChromeOptions,
};
