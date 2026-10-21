// Transport and display only. Python owns all exercise rules and counting state.
function createWorkoutControls() {
  const panel = document.querySelector("#workout-results");
  if (!panel) {
    return null;
  }

  const exerciseId = panel.dataset.exercise;
  if (!["pushup", "squats", "lunge"].includes(exerciseId)) {
    return null;
  }
  const sessionEndpoint = `/api/${exerciseId}/session`;
  const count = document.querySelector("#rep-count");
  const phase = document.querySelector("#rep-phase");
  const angleDisplays = [
    ["elbow_angle", "#elbow-angle"],
    ["body_angle", "#body-angle"],
    ["knee_angle", "#knee-angle"],
    ["left_knee_angle", "#left-knee-angle"],
    ["right_knee_angle", "#right-knee-angle"],
  ].map(([name, selector]) => [name, document.querySelector(selector)])
    .filter(([, element]) => element);
  const message = document.querySelector("#workout-message");
  const reset = document.querySelector("#reset-count");
  const phaseLabels = { ready: "Get ready", up: "Upper position", down: "Lower position" };

  function showResult(result) {
    count.textContent = String(result.rep_count);
    phase.textContent = phaseLabels[result.phase] || "Get ready";
    for (const [name, element] of angleDisplays) {
      element.textContent = result[name] == null ? "—" : `${result[name]}°`;
    }
    message.textContent = result.message;
  }

  function showPaused(text) {
    phase.textContent = "Paused";
    for (const [, element] of angleDisplays) {
      element.textContent = "—";
    }
    message.textContent = text;
  }

  async function createSession(signal) {
    const response = await fetch(sessionEndpoint, {
      method: "POST",
      mode: "same-origin",
      credentials: "omit",
      cache: "no-store",
      headers: { "X-Coach-Camera": "1" },
      signal,
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "Could not start local counting.");
    }
    return result;
  }

  async function closeSession(token) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    try {
      const response = await fetch(sessionEndpoint, {
        method: "DELETE",
        mode: "same-origin",
        credentials: "omit",
        cache: "no-store",
        keepalive: true,
        headers: { "X-Coach-Camera": "1", "X-Coach-Session": token },
        signal: controller.signal,
      });
      return response.ok;
    } catch (error) {
      return false;
    } finally {
      clearTimeout(timeout);
    }
  }

  reset.addEventListener("click", () => {
    if (!reset.disabled) {
      return startPoseDetection();
    }
  });

  return {
    frameEndpoint: `/api/${exerciseId}/frame`,
    createSession,
    closeSession,
    showResult,
    showPaused,
    setActive(active) {
      reset.disabled = !active;
    },
  };
}
