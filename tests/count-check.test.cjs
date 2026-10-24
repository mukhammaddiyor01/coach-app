const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const script = fs.readFileSync(path.join(__dirname, "../frontend/static/js/count-check.js"), "utf8");

function createPage(options = {}) {
  const listeners = {};
  const inputListeners = {};
  const elements = {
    "#count-check-form": { addEventListener: (name, handler) => { listeners[name] = handler; } },
    "#manual-count": { value: "5", disabled: true, reportValidity: () => options.valid !== false, addEventListener: (name, handler) => { inputListeners[name] = handler; } },
    "#check-app-count": { textContent: "—" },
    "#compare-counts": { disabled: true },
    "#count-check-status": { textContent: "", dataset: {} },
  };
  const calls = [];
  const context = vm.createContext({
    document: { querySelector: (selector) => elements[selector] },
    AbortController, setTimeout, clearTimeout,
    fetch: (url, request) => {
      calls.push({ url, request });
      return options.fetch ? options.fetch(url, request) : Promise.resolve({ ok: true, json: async () => ({ outcome: "match", message: "Counts match in this trial." }) });
    },
  });
  vm.runInContext(script, context);
  const check = context.createCountCheck(options.exercise || "pushup");
  return { check, elements, calls, submit: () => listeners.submit({ preventDefault() {} }), edit: () => inputListeners.input() };
}

function stopAt(page, count) {
  page.check.startSession();
  page.check.showCount(count);
  page.check.setActive(false);
  page.elements["#manual-count"].value = "5";
}

test("comparison requires a received count and a stopped trial", async () => {
  const page = createPage();
  assert.equal(page.elements["#compare-counts"].disabled, true);
  await page.submit();
  assert.equal(page.calls.length, 0);
  page.check.startSession();
  page.check.showCount(5);
  await page.submit();
  assert.equal(page.calls.length, 0);
  page.check.setActive(false);
  assert.equal(page.elements["#compare-counts"].disabled, false);
});

test("each exercise sends only its manual tally and last displayed count to Python", async () => {
  for (const exercise of ["pushup", "squats", "lunge"]) {
    const page = createPage({ exercise });
    stopAt(page, 4);
    await page.submit();
    assert.equal(page.calls[0].url, `/api/${exercise}/count-check`);
    assert.deepEqual(JSON.parse(page.calls[0].request.body), { manual_count: 5, observed_count: 4 });
    assert.equal(page.calls[0].request.mode, "same-origin");
    assert.equal(page.elements["#count-check-status"].textContent, "Counts match in this trial.");
  }
});

test("new camera runs ignore late comparison results and clear old trials", async () => {
  let resolve;
  const response = new Promise((done) => { resolve = done; });
  const page = createPage({ fetch: () => response });
  stopAt(page, 5);
  const checking = page.submit();
  page.check.startSession();
  assert.equal(page.calls[0].request.signal.aborted, true);
  resolve({ ok: true, json: async () => ({ outcome: "match", message: "OLD RESULT" }) });
  await checking;
  assert.doesNotMatch(page.elements["#count-check-status"].textContent, /OLD RESULT/);
  assert.equal(page.elements["#manual-count"].value, "");
  assert.equal(page.elements["#check-app-count"].textContent, "—");
  assert.equal(page.elements["#compare-counts"].disabled, true);
});

test("manual input validation and pending requests prevent duplicate submissions", async () => {
  const invalid = createPage({ valid: false });
  stopAt(invalid, 5);
  await invalid.submit();
  assert.equal(invalid.calls.length, 0);
  let resolve;
  const response = new Promise((done) => { resolve = done; });
  const page = createPage({ fetch: () => response });
  stopAt(page, 5);
  const first = page.submit();
  await page.submit();
  assert.equal(page.calls.length, 1);
  resolve({ ok: true, json: async () => ({ outcome: "match", message: "One result" }) });
  await first;
});

test("editing the manual tally clears an obsolete result", async () => {
  const page = createPage();
  stopAt(page, 5);
  await page.submit();
  assert.equal(page.elements["#count-check-status"].dataset.outcome, "match");
  page.edit();
  assert.equal(page.elements["#count-check-status"].dataset.outcome, "waiting");
});

test("network errors keep the stopped trial available for retry", async () => {
  const page = createPage({ fetch: async () => { throw new Error("offline"); } });
  stopAt(page, 5);
  await page.submit();
  assert.match(page.elements["#count-check-status"].textContent, /local Python server/);
  assert.equal(page.elements["#compare-counts"].disabled, false);
  assert.equal(page.elements["#check-app-count"].textContent, "5");
});
