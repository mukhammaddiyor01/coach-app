// Compare a stopped camera's last received count with a manual tally in Python.
function createCountCheck(exerciseId) {
  const form = document.querySelector("#count-check-form");
  if (!form) {
    return null;
  }
  const manualInput = document.querySelector("#manual-count");
  const observedOutput = document.querySelector("#check-app-count");
  const submitButton = document.querySelector("#compare-counts");
  const status = document.querySelector("#count-check-status");
  let observedCount = null;
  let active = true;
  let pending = false;
  let generation = 0;
  let request = null;

  function updateControls() {
    const canCompare = !active && observedCount !== null;
    manualInput.disabled = !canCompare;
    submitButton.disabled = !canCompare || pending;
  }

  function clearComparison() {
    generation += 1;
    request?.abort();
    request = null;
    pending = false;
    status.dataset.outcome = "waiting";
    status.textContent = active
      ? "Stop the camera after your trial to compare the last received count."
      : "Enter your manual tally and compare it with the displayed app count.";
    updateControls();
  }

  function startSession() {
    active = true;
    observedCount = null;
    observedOutput.textContent = "—";
    manualInput.value = "";
    clearComparison();
  }

  function showCount(count) {
    if (count !== observedCount) {
      observedCount = count;
      observedOutput.textContent = String(count);
      clearComparison();
    }
  }

  function setActive(value) {
    active = value;
    clearComparison();
    if (observedCount === null) {
      status.textContent = "Start a camera trial first. No count has been received yet.";
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (active || observedCount === null || pending || !manualInput.reportValidity()) {
      return;
    }
    const trialGeneration = ++generation;
    const controller = new AbortController();
    request = controller;
    pending = true;
    updateControls();
    status.textContent = "Comparing this trial…";
    const timeout = setTimeout(() => controller.abort(), 10_000);
    try {
      const response = await fetch(`/api/${exerciseId}/count-check`, {
        method: "POST",
        mode: "same-origin",
        credentials: "omit",
        cache: "no-store",
        headers: { "Content-Type": "application/json", "X-Coach-Camera": "1" },
        body: JSON.stringify({ manual_count: Number(manualInput.value), observed_count: observedCount }),
        signal: controller.signal,
      });
      const result = await response.json();
      if (trialGeneration !== generation) {
        return;
      }
      if (!response.ok || !["match", "extra", "missed"].includes(result.outcome)) {
        throw new Error("Comparison unavailable.");
      }
      status.dataset.outcome = result.outcome;
      status.textContent = result.message;
    } catch (error) {
      if (trialGeneration === generation) {
        status.dataset.outcome = "waiting";
        status.textContent = "Could not compare counts. Check the local Python server and try again.";
      }
    } finally {
      clearTimeout(timeout);
      if (trialGeneration === generation) {
        pending = false;
        request = null;
        updateControls();
      }
    }
  });

  manualInput.addEventListener("input", clearComparison);
  updateControls();
  return { startSession, showCount, setActive };
}
