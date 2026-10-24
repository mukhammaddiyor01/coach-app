const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const countCheckScript = fs.readFileSync(path.join(__dirname, "../frontend/static/js/count-check.js"), "utf8");

const workoutScript = fs.readFileSync(path.join(__dirname, "../frontend/static/js/workout.js"), "utf8");

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
  const reset = {
    disabled: true,
    addEventListener(event, callback) { this.click = callback; },
  };
  if (options.exercise) {
    Object.assign(elements, {
      "#workout-results": { dataset: { exercise: options.exercise } },
      "#rep-count": { textContent: "0" },
      "#rep-phase": { textContent: "Get ready" },
      "#elbow-angle": { textContent: "—" },
      "#body-angle": { textContent: "—" },
      "#workout-message": { textContent: "Start the camera." },
      "#reset-count": reset,
      "#posture-feedback": { dataset: {} },
      "#feedback-label": { textContent: "Not assessed" },
      "#feedback-message": { textContent: "Waiting for tracking." },
    });
  }
  if (options.exercise === "squats") {
    delete elements["#elbow-angle"];
    delete elements["#body-angle"];
    elements["#knee-angle"] = { textContent: "—" };
  } else if (options.exercise === "lunge") {
    delete elements["#elbow-angle"];
    delete elements["#body-angle"];
    elements["#left-knee-angle"] = { textContent: "—" };
    elements["#right-knee-angle"] = { textContent: "—" };
  }
  const comparisonEvents = new Map();
  if (options.countCheck) {
    Object.assign(elements, {
      "#count-check-form": { addEventListener: (name, callback) => comparisonEvents.set(name, callback) },
      "#manual-count": { value: "", disabled: true, reportValidity: () => true, addEventListener() {} },
      "#check-app-count": { textContent: "—" },
      "#compare-counts": { disabled: true },
      "#count-check-status": { textContent: "", dataset: {} },
    });
  }
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
  if (options.countCheck) {
    vm.runInContext(countCheckScript, context);
  }
  if (options.exercise) {
    vm.runInContext(workoutScript, context);
  }
  vm.runInContext(poseScript, context);

  return {
    calls, timers, dots, message, video, overlay, capture, elements, reset,
    compare: () => comparisonEvents.get("submit")({ preventDefault() {} }),
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
  assert.match(page.message.textContent, /Counting controls are unavailable/);
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


function workout(repCount = 0) {
  return {
    rep_count: repCount, phase: "up", status: "tracking", message: "Server guidance.",
    elbow_angle: 170, body_angle: 175,
  };
}

function createWorkoutPage(options = {}) {
  let sessionNumber = 0;
  const page = createPosePage({
    exercise: options.exercise || "pushup",
    countCheck: options.countCheck,
    fetch(url, request) {
      if (options.fetch) {
        const custom = options.fetch(url, request);
        if (custom) return custom;
      }
      if (request.method === "DELETE") return Promise.resolve({ ok: true, status: 204 });
      if (url.endsWith("/session")) {
        sessionNumber += 1;
        return Promise.resolve({ ok: true, status: 201, json: async () => ({
          session_id: String(sessionNumber).padStart(32, "0"), exercise_id: options.exercise || "pushup", workout: workout(),
        }) });
      }
      return Promise.resolve(makeResponse({ ...makePoseResult(), workout: workout(options.count || 0) }));
    },
  });
  page.count = page.elements["#rep-count"];
  page.workoutMessage = page.elements["#workout-message"];
  return page;
}

test("Push Up creates no session until camera starts and displays Python's count", async () => {
  const page = createWorkoutPage({ count: 7 });
  assert.equal(page.calls.length, 0);
  assert.equal(page.reset.disabled, true);
  await page.start();
  assert.equal(page.calls[0].url, "/api/pushup/session");
  assert.equal(page.calls[1].url, "/api/pushup/frame");
  assert.equal(page.calls[1].request.headers["X-Coach-Session"], "1".padStart(32, "0"));
  assert.equal(page.count.textContent, "7");
  assert.equal(page.elements["#elbow-angle"].textContent, "170°");
  assert.equal(page.workoutMessage.textContent, "Server guidance.");
  assert.doesNotMatch(page.message.textContent, /counting comes later/);
  assert.equal(page.reset.disabled, false);
  page.stop();
});

test("Push Up stop closes server state without putting its token in a URL", async () => {
  const page = createWorkoutPage({ count: 3 });
  await page.start();
  page.stop();
  const close = page.calls.at(-1);
  assert.equal(close.url, "/api/pushup/session");
  assert.equal(close.request.method, "DELETE");
  assert.equal(close.request.keepalive, true);
  assert.equal(close.request.headers["X-Coach-Session"], "1".padStart(32, "0"));
  assert.equal(page.count.textContent, "3");
  assert.equal(page.reset.disabled, true);
  assert.equal(page.elements["#elbow-angle"].textContent, "—");
  assert.match(page.workoutMessage.textContent, /Last received count/);
});

test("Push Up reset replaces the session and renders the new server count", async () => {
  let count = 4;
  const page = createWorkoutPage({ fetch(url) {
    if (url.endsWith("/frame")) return Promise.resolve(makeResponse({ ...makePoseResult(), workout: workout(count) }));
  } });
  await page.start();
  assert.equal(page.count.textContent, "4");
  count = 0;
  await page.reset.click();
  assert.equal(page.count.textContent, "0");
  assert.equal(page.calls.filter((call) => call.request.method === "DELETE").length, 1);
  assert.equal(page.calls.at(-1).request.headers["X-Coach-Session"], "2".padStart(32, "0"));
  page.stop();
});

test("a frame that finishes after Reset cannot restore the old count", async () => {
  const oldFrame = createDeferred();
  let frames = 0;
  const page = createWorkoutPage({ fetch(url) {
    if (url.endsWith("/frame") && ++frames === 1) return oldFrame.promise;
  } });
  const starting = page.start();
  for (let step = 0; step < 8; step += 1) await Promise.resolve();
  assert.equal(page.calls.at(-1).url, "/api/pushup/frame");
  const oldRequest = page.calls.at(-1).request;
  await page.reset.click();
  assert.equal(oldRequest.signal.aborted, true);
  oldFrame.resolve(makeResponse({ ...makePoseResult(), workout: workout(99) }));
  await starting;
  assert.equal(page.count.textContent, "0");
  assert.equal([...page.timers.values()].filter((timer) => timer.delay === 200).length, 1);
  page.stop();
});

test("a late session creation after Stop is closed without uploading a frame", async () => {
  const creation = createDeferred();
  const page = createWorkoutPage({ fetch(url, request) {
    if (url.endsWith("/session") && request.method === "POST") return creation.promise;
  } });
  const starting = page.start();
  page.stop();
  assert.equal(page.calls[0].request.signal.aborted, true);
  creation.resolve({ ok: true, status: 201, json: async () => ({ session_id: "1".padStart(32, "0"), workout: workout(8) }) });
  await starting;
  assert.equal(page.calls.length, 2);
  assert.equal(page.calls[1].request.method, "DELETE");
  assert.equal(page.count.textContent, "0");
  assert.equal(page.reset.disabled, true);
});

test("session creation failure leaves counting disabled and sends no frame", async () => {
  const page = createWorkoutPage({ fetch() {
    return Promise.resolve(makeResponse({ detail: "Capacity reached." }, 429));
  } });
  await page.start();
  assert.equal(page.calls.length, 1);
  assert.equal(page.reset.disabled, true);
  assert.match(page.message.textContent, /Could not start local counting/);
  assert.equal(page.timers.size, 0);
});

test("fatal Push Up analysis errors close the session and disable Reset", async () => {
  const page = createWorkoutPage({ fetch(url) {
    if (url.endsWith("/frame")) return Promise.resolve(makeResponse({ detail: "Model unavailable." }, 503));
  } });
  await page.start();
  await Promise.resolve();
  assert.match(page.message.textContent, /Model unavailable/);
  assert.equal(page.reset.disabled, true);
  assert.equal(page.calls.at(-1).request.method, "DELETE");
  assert.equal([...page.timers.values()].some((timer) => timer.delay === 200), false);
});

test("temporary frame errors mark displayed metrics as paused", async () => {
  const page = createWorkoutPage({ fetch(url) {
    if (url.endsWith("/frame")) return Promise.reject(new Error("offline"));
  } });
  await page.start();
  assert.match(page.workoutMessage.textContent, /Tracking is paused/);
  assert.equal(page.elements["#elbow-angle"].textContent, "—");
  assert.equal(page.reset.disabled, false);
  page.stop();
});

test("failed session cleanup explains the bounded expiration fallback", async () => {
  const page = createWorkoutPage({ fetch(url, request) {
    if (request.method === "DELETE") return Promise.reject(new Error("offline"));
  } });
  await page.start();
  page.stop();
  for (let step = 0; step < 5; step += 1) await Promise.resolve();
  assert.match(page.workoutMessage.textContent, /expire within 10 minutes/);
});

test("late cleanup failures do not overwrite a newly running session", async () => {
  const cleanup = createDeferred();
  const page = createWorkoutPage({ fetch(url, request) {
    if (request.method === "DELETE") return cleanup.promise;
  } });
  await page.start();
  await page.reset.click();
  cleanup.reject(new Error("offline"));
  for (let step = 0; step < 5; step += 1) await Promise.resolve();
  assert.equal(page.workoutMessage.textContent, "Server guidance.");
  assert.equal(page.reset.disabled, false);
  page.stop();
});


for (const exercise of ["squats", "lunge"]) {
  test(`${exercise} sends frames to its own service and displays only its metrics`, async () => {
    const result = {
      ...workout(5), elbow_angle: null, body_angle: null,
      knee_angle: 92, left_knee_angle: 94, right_knee_angle: 96,
    };
    const page = createWorkoutPage({ exercise, fetch(url) {
      if (url.endsWith("/frame")) return Promise.resolve(makeResponse({ ...makePoseResult(), workout: result }));
    } });
    assert.equal(page.calls.length, 0);
    await page.start();
    assert.equal(page.calls[0].url, `/api/${exercise}/session`);
    assert.equal(page.calls[1].url, `/api/${exercise}/frame`);
    assert.equal(page.count.textContent, "5");
    assert.equal(page.elements["#elbow-angle"], undefined);
    if (exercise === "squats") {
      assert.equal(page.elements["#knee-angle"].textContent, "92°");
    } else {
      assert.equal(page.elements["#left-knee-angle"].textContent, "94°");
      assert.equal(page.elements["#right-knee-angle"].textContent, "96°");
    }
    await page.reset.click();
    assert.equal(page.calls.at(-1).url, `/api/${exercise}/frame`);
    assert.equal(page.calls.at(-1).request.headers["X-Coach-Session"], "2".padStart(32, "0"));
    page.stop();
    assert.equal(page.calls.at(-1).url, `/api/${exercise}/session`);
    assert.equal(page.calls.at(-1).request.method, "DELETE");
    assert.equal(page.reset.disabled, true);
    const angleId = exercise === "squats" ? "#knee-angle" : "#left-knee-angle";
    assert.equal(page.elements[angleId].textContent, "—");
  });

  test(`${exercise} ignores an old frame that arrives after Reset`, async () => {
    const oldFrame = createDeferred();
    let frames = 0;
    const page = createWorkoutPage({ exercise, fetch(url) {
      if (url.endsWith("/frame") && ++frames === 1) return oldFrame.promise;
    } });
    const starting = page.start();
    for (let step = 0; step < 8; step += 1) await Promise.resolve();
    await page.reset.click();
    oldFrame.resolve(makeResponse({ ...makePoseResult(), workout: workout(99) }));
    await starting;
    assert.equal(page.count.textContent, "0");
    assert.equal(page.calls.filter((call) => call.url === `/api/${exercise}/session` && call.request.method === "POST").length, 2);
    page.stop();
  });
}


test("portrait capture and a later landscape frame keep landmarks aligned", async () => {
  let frameNumber = 0;
  const page = createPosePage({ fetch: async () => {
    const result = makePoseResult();
    if (++frameNumber === 1) {
      result.width = 360;
      result.height = 640;
    }
    return makeResponse(result);
  } });
  page.video.videoWidth = 720;
  page.video.videoHeight = 1280;
  await page.start();
  assert.equal(page.capture.width, 360);
  assert.equal(page.capture.height, 640);
  assert.equal(page.overlay.width, 360);
  assert.equal(page.overlay.height, 640);
  assert.deepEqual(page.dots.at(-1), [180, 320]);

  page.video.videoWidth = 1280;
  page.video.videoHeight = 720;
  const [timerId, timer] = [...page.timers.entries()].find(([, timer]) => timer.delay === 200);
  page.timers.delete(timerId);
  await timer.callback();
  assert.equal(page.capture.width, 640);
  assert.equal(page.capture.height, 360);
  assert.equal(page.overlay.width, 640);
  assert.equal(page.overlay.height, 360);
  assert.deepEqual(page.dots.at(-1), [320, 180]);
  page.stop();
});


test("posture feedback displays the Python cue without making a correctness score", async () => {
  const page = createWorkoutPage({ fetch(url) {
    if (url.endsWith("/frame")) return Promise.resolve(makeResponse({
      ...makePoseResult(), workout: { ...workout(), feedback: {
        level: "adjust", code: "hips_raised", message: "Lower your hips toward the shoulder-to-ankle line.", side: "left",
      } },
    }));
  } });
  await page.start();
  assert.equal(page.elements["#posture-feedback"].dataset.level, "adjust");
  assert.equal(page.elements["#feedback-label"].textContent, "Adjust position");
  assert.match(page.elements["#feedback-message"].textContent, /Lower your hips/);
  page.stop();
  assert.equal(page.elements["#posture-feedback"].dataset.level, "unavailable");
  assert.equal(page.elements["#feedback-label"].textContent, "Not assessed");
});

test("network loss clears old observed posture feedback", async () => {
  let calls = 0;
  const page = createWorkoutPage({ fetch(url) {
    if (url.endsWith("/frame")) {
      if (++calls > 1) return Promise.reject(new Error("offline"));
      return Promise.resolve(makeResponse({ ...makePoseResult(), workout: {
        ...workout(), feedback: { level: "observed", code: "visible_alignment", message: "Visible joints are being tracked." },
      } }));
    }
  } });
  await page.start();
  assert.equal(page.elements["#feedback-label"].textContent, "Visible checks");
  const [timerId, timer] = [...page.timers.entries()].find(([, timer]) => timer.delay === 200);
  page.timers.delete(timerId);
  await timer.callback();
  assert.equal(page.elements["#posture-feedback"].dataset.level, "unavailable");
  assert.match(page.elements["#feedback-message"].textContent, /No current posture assessment/);
  page.stop();
});


test("camera results feed the stopped-trial panel and a new run clears the comparison", async () => {
  const page = createWorkoutPage({ countCheck: true, count: 4, fetch(url) {
    if (url.endsWith("/count-check")) return Promise.resolve(makeResponse({ outcome: "missed", message: "The app counted one fewer in this trial." }));
  } });
  await page.start();
  assert.equal(page.elements["#check-app-count"].textContent, "4");
  assert.equal(page.elements["#compare-counts"].disabled, true);
  page.stop();
  assert.equal(page.elements["#compare-counts"].disabled, false);
  page.elements["#manual-count"].value = "5";
  await page.compare();
  const comparison = page.calls.find((call) => call.url.endsWith("/count-check"));
  assert.deepEqual(JSON.parse(comparison.request.body), { manual_count: 5, observed_count: 4 });
  assert.equal(page.elements["#count-check-status"].dataset.outcome, "missed");
  await page.start();
  assert.equal(page.elements["#manual-count"].value, "");
  assert.equal(page.elements["#compare-counts"].disabled, true);
  assert.equal(page.elements["#count-check-status"].dataset.outcome, "waiting");
  page.stop();
});
