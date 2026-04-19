const test = require("node:test");
const assert = require("node:assert/strict");

const {
  REVEAL_WORKSPACE_RESET_DELAY_MS,
  revealWindow,
} = require("../electron/window-control");

function createWindow({ visible = false, destroyed = false } = {}) {
  const calls = [];
  const window = {
    isVisible: () => visible,
    show: () => calls.push(["show"]),
    focus: () => calls.push(["focus"]),
    moveTop: () => calls.push(["moveTop"]),
    setVisibleOnAllWorkspaces: (flag, options) =>
      calls.push(["setVisibleOnAllWorkspaces", flag, options]),
    isDestroyed: () => destroyed,
  };

  return { calls, window };
}

test("revealWindow activates and rehomes the window on macOS", () => {
  const { calls, window } = createWindow();
  const focusCalls = [];
  const boundsCalls = [];
  const scheduled = [];

  revealWindow(
    {
      focus: (options) => focusCalls.push(options),
    },
    window,
    {
      applyBounds: (target, bounds) => boundsCalls.push([target, bounds]),
      bounds: { x: 24, y: 48, width: 700, height: 560 },
      focus: true,
      platform: "darwin",
      scheduler: (callback, delay) => scheduled.push({ callback, delay }),
    },
  );

  assert.deepEqual(boundsCalls, [
    [window, { x: 24, y: 48, width: 700, height: 560 }],
  ]);
  assert.deepEqual(focusCalls, [{ steal: true }]);
  assert.deepEqual(calls, [
    [
      "setVisibleOnAllWorkspaces",
      true,
      { visibleOnFullScreen: true },
    ],
    ["show"],
    ["moveTop"],
    ["focus"],
  ]);
  assert.equal(scheduled.length, 1);
  assert.equal(scheduled[0].delay, REVEAL_WORKSPACE_RESET_DELAY_MS);

  scheduled[0].callback();

  assert.deepEqual(calls[calls.length - 1], [
    "setVisibleOnAllWorkspaces",
    false,
    { visibleOnFullScreen: true },
  ]);
});

test("revealWindow skips workspace juggling outside macOS", () => {
  const { calls, window } = createWindow({ visible: true });
  const focusCalls = [];

  revealWindow(
    {
      focus: () => focusCalls.push("focused"),
    },
    window,
    {
      focus: true,
      platform: "linux",
      scheduler: () => {
        throw new Error("scheduler should not run outside macOS");
      },
    },
  );

  assert.deepEqual(focusCalls, ["focused"]);
  assert.deepEqual(calls, [["moveTop"], ["focus"]]);
});
