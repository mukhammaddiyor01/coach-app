const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const cameraScript = fs.readFileSync(
  path.join(__dirname, "../frontend/static/js/camera.js"),
  "utf8",
);

// Browser and camera doubles let us verify cleanup without using a real device.
function createElement() {
  const listeners = new Map();

  return {
    hidden: false,
    disabled: false,
    textContent: "",
    dataset: {},
    srcObject: null,
    pause() {},
    async play() {},
    addEventListener(event, listener) {
      listeners.set(event, listener);
    },
    emit(event) {
      return listeners.get(event)?.();
    },
  };
}

function createStream() {
  const track = createElement();
  track.stopCount = 0;
  track.readyState = "live";
  track.stop = () => {
    track.stopCount += 1;
    track.readyState = "ended";
  };

  return {
    track,
    getTracks: () => [track],
    getVideoTracks: () => [track],
  };
}

function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function createPage(options = {}) {
  const ids = [
    "camera-video", "camera-placeholder", "camera-title", "camera-message",
    "camera-status", "camera-status-text", "start-camera", "stop-camera",
  ];
  const elements = Object.fromEntries(ids.map((id) => [id, createElement()]));
  const pageEvents = new Map();
  const documentEvents = new Map();
  const stream = createStream();
  let permissionRequests = 0;
  let constraints;

  if (options.play) {
    elements["camera-video"].play = options.play;
  }

  const mediaDevices = {
    getUserMedia(requestedConstraints) {
      permissionRequests += 1;
      constraints = requestedConstraints;
      return options.getUserMedia ? options.getUserMedia() : Promise.resolve(stream);
    },
  };

  const document = {
    hidden: false,
    querySelector: (selector) => elements[selector.slice(1)],
    addEventListener: (event, listener) => documentEvents.set(event, listener),
  };

  vm.runInNewContext(cameraScript, {
    document,
    navigator: { mediaDevices: options.unsupported ? undefined : mediaDevices },
    window: { addEventListener: (event, listener) => pageEvents.set(event, listener) },
  });

  return {
    elements,
    stream,
    start: () => elements["start-camera"].emit("click"),
    stop: () => elements["stop-camera"].emit("click"),
    leave: () => pageEvents.get("pagehide")(),
    setTabHidden(hidden) {
      document.hidden = hidden;
      documentEvents.get("visibilitychange")();
    },
    get permissionRequests() {
      return permissionRequests;
    },
    get constraints() {
      return constraints;
    },
    get state() {
      return elements["camera-status"].dataset.state;
    },
    get message() {
      return elements["camera-message"].textContent;
    },
  };
}

test("loading the page does not request camera permission", () => {
  const page = createPage();
  assert.equal(page.permissionRequests, 0);
  assert.equal(page.elements["camera-video"].srcObject, null);
});

test("start attaches video without microphone access; stop releases it", async () => {
  const page = createPage();
  await page.start();

  assert.equal(page.state, "on");
  assert.equal(page.constraints.audio, false);
  assert.equal(page.elements["camera-video"].srcObject, page.stream);
  assert.equal(page.elements["camera-placeholder"].hidden, true);
  assert.equal(page.elements["start-camera"].disabled, true);
  assert.equal(page.elements["stop-camera"].disabled, false);

  page.stop();
  assert.equal(page.state, "off");
  assert.equal(page.stream.track.stopCount, 1);
  assert.equal(page.elements["camera-video"].srcObject, null);
  assert.equal(page.elements["camera-video"].hidden, true);
  assert.equal(page.elements["start-camera"].disabled, false);
  assert.equal(page.elements["stop-camera"].disabled, true);
});

test("repeated starts do not create extra camera requests", async () => {
  const permission = createDeferred();
  const page = createPage({ getUserMedia: () => permission.promise });
  const starting = page.start();
  await page.start();
  assert.equal(page.permissionRequests, 1);
  assert.equal(page.state, "starting");

  permission.resolve(page.stream);
  await starting;
  await page.start();
  assert.equal(page.permissionRequests, 1);
  page.stop();
});

test("stopping a pending request releases its late stream", async () => {
  const permission = createDeferred();
  const page = createPage({ getUserMedia: () => permission.promise });
  const starting = page.start();
  page.stop();
  permission.resolve(page.stream);
  await starting;

  assert.equal(page.state, "off");
  assert.equal(page.stream.track.stopCount, 1);
  assert.equal(page.elements["camera-video"].srcObject, null);
});

test("leaving the page closes the active camera", async () => {
  const page = createPage();
  await page.start();
  page.leave();
  assert.equal(page.stream.track.stopCount, 1);
  assert.equal(page.elements["camera-video"].srcObject, null);
  assert.equal(page.state, "off");
});

test("leaving while permission is pending cancels the late result", async () => {
  const permission = createDeferred();
  const page = createPage({ getUserMedia: () => permission.promise });
  const starting = page.start();
  page.leave();
  permission.resolve(page.stream);
  await starting;
  assert.equal(page.stream.track.stopCount, 1);
  assert.equal(page.state, "off");
});

const cameraErrorNames = [
  "NotAllowedError",
  "NotFoundError",
  "NotReadableError",
  "SecurityError",
  "OverconstrainedError",
  "AbortError",
];

for (const errorName of cameraErrorNames) {
  test(`${errorName} displays an error and allows retry`, async () => {
    let shouldFail = true;
    const page = createPage({
      getUserMedia: async () => {
        if (shouldFail) {
          throw { name: errorName };
        }
        return page.stream;
      },
    });

    await page.start();
    assert.equal(page.state, "error");
    assert.ok(page.message.length > 0);
    assert.equal(page.elements["start-camera"].disabled, false);
    shouldFail = false;
    await page.start();
    assert.equal(page.state, "on");
    page.stop();
  });
}

test("unsupported browsers display an error without requesting permission", async () => {
  const page = createPage({ unsupported: true });
  await page.start();
  assert.equal(page.permissionRequests, 0);
  assert.equal(page.state, "error");
});

test("video playback failure releases the acquired stream", async () => {
  const page = createPage({
    play: async () => {
      throw new Error("Playback failed");
    },
  });
  await page.start();
  assert.equal(page.stream.track.stopCount, 1);
  assert.equal(page.state, "error");
  assert.equal(page.elements["camera-video"].srcObject, null);
});

test("camera disconnection clears the preview and allows retry", async () => {
  const page = createPage();
  await page.start();
  page.stream.track.emit("ended");
  assert.equal(page.state, "error");
  assert.match(page.message, /disconnected/);
  assert.equal(page.elements["camera-video"].srcObject, null);
});

test("a stale rejected request cannot change a newer active camera", async () => {
  const oldPermission = createDeferred();
  let requests = 0;
  const page = createPage({
    getUserMedia: () => {
      requests += 1;
      return requests === 1 ? oldPermission.promise : Promise.resolve(page.stream);
    },
  });

  const oldStart = page.start();
  page.stop();
  await page.start();
  oldPermission.reject({ name: "NotAllowedError" });
  await oldStart;
  assert.equal(page.state, "on");
  assert.equal(page.elements["camera-video"].srcObject, page.stream);
  page.stop();
});

test("stopping during video startup cannot switch the preview back on", async () => {
  const playback = createDeferred();
  const page = createPage({ play: () => playback.promise });
  const starting = page.start();
  await Promise.resolve();
  page.stop();
  playback.resolve();
  await starting;
  assert.equal(page.state, "off");
  assert.equal(page.elements["camera-video"].srcObject, null);
});


test("a camera lost during startup is not reported as active", async () => {
  const playback = createDeferred();
  const page = createPage({ play: () => playback.promise });
  const starting = page.start();
  await Promise.resolve();
  page.stream.track.readyState = "ended";
  playback.resolve();
  await starting;
  assert.equal(page.state, "error");
  assert.match(page.message, /disconnected/);
  assert.equal(page.elements["camera-video"].srcObject, null);
});


test("switching away from the tab stops the active camera", async () => {
  const page = createPage();
  await page.start();
  page.setTabHidden(true);

  assert.equal(page.state, "off");
  assert.equal(page.stream.track.stopCount, 1);
  assert.equal(page.elements["camera-video"].srcObject, null);

  page.setTabHidden(false);
  assert.equal(page.permissionRequests, 1);
  assert.equal(page.state, "off");
});

test("hiding the tab cancels a pending camera request", async () => {
  const permission = createDeferred();
  const page = createPage({ getUserMedia: () => permission.promise });
  const starting = page.start();
  page.setTabHidden(true);
  permission.resolve(page.stream);
  await starting;

  assert.equal(page.stream.track.stopCount, 1);
  assert.equal(page.state, "off");
});

test("a visible-tab notification does not stop an active camera", async () => {
  const page = createPage();
  await page.start();
  page.setTabHidden(false);
  assert.equal(page.state, "on");
  assert.equal(page.stream.track.stopCount, 0);
  page.stop();
});
