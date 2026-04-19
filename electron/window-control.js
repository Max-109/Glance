const REVEAL_WORKSPACE_RESET_DELAY_MS = 120;

function focusApp(app, platform) {
  if (typeof app.focus !== "function") {
    return;
  }

  if (platform === "darwin") {
    app.focus({ steal: true });
    return;
  }

  app.focus();
}

function revealWindow(
  app,
  window,
  {
    applyBounds,
    bounds,
    focus = false,
    platform = process.platform,
    scheduler = setTimeout,
    workspaceResetDelay = REVEAL_WORKSPACE_RESET_DELAY_MS,
  } = {},
) {
  if (typeof applyBounds === "function") {
    applyBounds(window, bounds);
  }

  const shouldSpanWorkspaces =
    platform === "darwin" &&
    typeof window.setVisibleOnAllWorkspaces === "function";

  if (shouldSpanWorkspaces) {
    window.setVisibleOnAllWorkspaces(true, {
      visibleOnFullScreen: true,
    });
  }

  if (!window.isVisible()) {
    window.show();
  }

  if (focus) {
    focusApp(app, platform);
    if (typeof window.moveTop === "function") {
      window.moveTop();
    }
    window.focus();
  }

  if (!shouldSpanWorkspaces) {
    return;
  }

  scheduler(() => {
    if (typeof window.isDestroyed === "function" && window.isDestroyed()) {
      return;
    }
    window.setVisibleOnAllWorkspaces(false, {
      visibleOnFullScreen: true,
    });
  }, workspaceResetDelay);
}

module.exports = {
  REVEAL_WORKSPACE_RESET_DELAY_MS,
  revealWindow,
};
