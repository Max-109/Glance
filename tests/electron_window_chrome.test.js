const test = require("node:test");
const assert = require("node:assert/strict");

const {
  applyWindowChrome,
  buildWindowChromeOptions,
} = require("../electron/window-chrome");

test("buildWindowChromeOptions enables macOS chrome settings", () => {
  const options = buildWindowChromeOptions("darwin");

  assert.equal(options.frame, true);
  assert.equal(options.transparent, true);
  assert.equal(options.backgroundColor, "#00000000");
  assert.equal(options.titleBarStyle, "hiddenInset");
  assert.equal(options.vibrancy, "sidebar");
  assert.equal(options.visualEffectState, "active");
  assert.equal(options.skipTaskbar, true);
});

test("buildWindowChromeOptions leaves platform-specific chrome off outside macOS", () => {
  const options = buildWindowChromeOptions("linux");

  assert.equal(options.frame, false);
  assert.equal(options.transparent, true);
  assert.equal(options.titleBarStyle, undefined);
  assert.equal(options.vibrancy, undefined);
  assert.equal(options.visualEffectState, undefined);
  assert.equal(options.skipTaskbar, true);
});

test("applyWindowChrome enables native traffic lights on macOS", () => {
  const calls = [];
  const window = {
    setWindowButtonVisibility: (visible) =>
      calls.push(["setWindowButtonVisibility", visible]),
  };

  applyWindowChrome(window, "darwin");

  assert.deepEqual(calls, [["setWindowButtonVisibility", true]]);
});

test("applyWindowChrome skips native traffic lights outside macOS", () => {
  const calls = [];
  const window = {
    setWindowButtonVisibility: (visible) =>
      calls.push(["setWindowButtonVisibility", visible]),
  };

  applyWindowChrome(window, "win32");

  assert.deepEqual(calls, []);
});
