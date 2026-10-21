const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const poseScript = fs.readFileSync(
  path.join(__dirname, "../frontend/static/js/pose.js"),
  "utf8",
);

function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function makePoseResult() {
  const point = { x: 0.5, y: 0.5, visibility: 0.9, presence: 0.9 };
  return { width: 640, height: 360, landmarks: Array(33).fill(point) };
}

function makeResponse(result, status = 200) {
  return { ok: status === 200, status, json: async () => result };
}

function createPosePage(options = {}) {
  const calls = [];
  const timers = new Map();
  const dots = [];
  let timerId = 0;
  const message = { textContent: "Body detection is off." };
  const video = { videoWidth: 1280, videoHeight: 720 };
  const drawing = {
    clearRect() {},
    beginPath() {},
    moveTo() {},
    lineTo() {},
    stroke() {},
    fill() {},
    arc(x, y) {
      dots.push([x, y]);
    },
  };
  const overlay = { width: 0, height: 0, getContext: () => drawing };
  const capture = {
    width: 0,
    height: 0,
    getContext: () => ({ drawImage() {} }),
    toBlob(callback, type) {
      if (options.encode) {
        options.encode(callback);
        return;
      }
      callback(new Blob(["dummy frame"], { type }));
    },
  };
  const elements = {
    "#camera-video": video,
    "#pose-overlay": overlay,
    "#pose-message": message,
  };
  const context = vm.createContext({
    document: {
      querySelector: (selector) => elements[selector],
      createElement: () => capture,
    },
    AbortController,
    fetch(url, request) {
      calls.push({ url, request });
      return options.fetch
        ? options.fetch(url, request)
        : Promise.resolve(makeResponse(makePoseResult()));
    },
    setTimeout(callback, delay) {
      const id = ++timerId;
      timers.set(id, { callback, delay });
      return id;
    },
    clearTimeout(id) {
      timers.delete(id);
    },
  });
  vm.runInContext(poseScript, context);

  return {
    calls, timers, dots, message, video, overlay, capture,
    start: () => context.startPoseDetection(),
    stop: () => context.stopPoseDetection(),
  };
}

test("loading the pose script does not send a frame", () => {
  const page = createPosePage();
  assert.equal(page.calls.length, 0);
});

test("frames preserve aspect ratio and only go to the local API", async () => {
  const page = createPosePage();
  await page.start();
  assert.equal(page.calls.length, 1);
  assert.equal(page.calls[0].url, "/api/pose");
  assert.equal(page.calls[0].request.mode, "same-origin");
  assert.equal(page.calls[0].request.cache, "no-store");
  assert.equal(page.calls[0].request.credentials, "omit");
  assert.equal(page.calls[0].request.headers["X-Coach-Camera"], "1");
  assert.equal(page.capture.width, 640);
  assert.equal(page.capture.height, 360);
  assert.equal(page.dots.length, 33);
  assert.deepEqual(page.dots[0], [320, 180]);
  assert.match(page.message.textContent, /Body detected/);
  page.stop();
});

test("no second frame is scheduled while a request is in flight", async () => {
  const response = createDeferred();
  const page = createPosePage({ fetch: () => response.promise });
  const starting = page.start();
  await Promise.resolve();
  assert.equal(page.calls.length, 1);
  assert.equal([...page.timers.values()].some((timer) => timer.delay === 200), false);
  response.resolve(makeResponse(makePoseResult()));
  await starting;
  assert.equal([...page.timers.values()].some((timer) => timer.delay === 200), true);
  page.stop();
});

test("an empty result shows no-body guidance instead of a pose", async () => {
  const page = createPosePage({
    fetch: async () => makeResponse({ width: 640, height: 360, landmarks: [] }),
  });
  await page.start();
  assert.equal(page.dots.length, 0);
  assert.match(page.message.textContent, /No visible body/);
  page.stop();
});

test("low-confidence or out-of-frame landmarks are not drawn", async () => {
  const result = makePoseResult();
  result.landmarks = result.landmarks.map((point) => ({ ...point, visibility: 0.1 }));
  result.landmarks[0] = { x: 2, y: 0.5, visibility: 1, presence: 1 };
  const page = createPosePage({ fetch: async () => makeResponse(result) });
  await page.start();
  assert.equal(page.dots.length, 0);
  page.stop();
});

test("stop aborts requests, clears sampled pixels, and ignores late results", async () => {
  const response = createDeferred();
  const page = createPosePage({ fetch: () => response.promise });
  const starting = page.start();
  await Promise.resolve();
  page.stop();
  assert.equal(page.calls[0].request.signal.aborted, true);
  assert.equal(page.capture.width, 0);
  assert.equal(page.capture.height, 0);
  response.resolve(makeResponse(makePoseResult()));
  await starting;
  assert.equal(page.dots.length, 0);
  assert.equal(page.timers.size, 0);
  assert.equal(page.message.textContent, "Body detection is off.");
});

test("stopping during JPEG encoding prevents the frame upload", async () => {
  let finishEncoding;
  const page = createPosePage({ encode: (callback) => {
    finishEncoding = callback;
  } });
  const starting = page.start();
  page.stop();
  finishEncoding(new Blob(["late frame"]));
  await starting;
  assert.equal(page.calls.length, 0);
  assert.equal(page.timers.size, 0);
});

test("an unavailable model stops retries and provides a setup message", async () => {
  const page = createPosePage({
    fetch: async () => makeResponse({ detail: "Run python download_model.py." }, 503),
  });
  await page.start();
  assert.equal(page.timers.size, 0);
  assert.match(page.message.textContent, /download_model.py/);
  page.stop();
});

test("a busy response schedules a slower retry", async () => {
  const page = createPosePage({
    fetch: async () => makeResponse({ detail: "Detector busy." }, 429),
  });
  await page.start();
  assert.equal([...page.timers.values()].some((timer) => timer.delay === 1000), true);
  page.stop();
});

test("network errors show a local-server message and allow retry", async () => {
  const page = createPosePage({ fetch: async () => {
    throw new Error("offline");
  } });
  await page.start();
  assert.match(page.message.textContent, /Python server/);
  assert.equal([...page.timers.values()].some((timer) => timer.delay === 1000), true);
  page.stop();
});

test("video metadata must be ready before a frame is sampled", async () => {
  const page = createPosePage();
  page.video.videoWidth = 0;
  page.video.videoHeight = 0;
  await page.start();
  assert.equal(page.calls.length, 0);
  assert.equal(page.timers.size, 1);
  page.stop();
});
