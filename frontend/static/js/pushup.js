// Transport and display only. Python owns all exercise rules and counting state.
function createPushUpControls() {
  const panel = document.querySelector("#pushup-results");
  if (!panel) {
    return null;
  }

  const count = document.querySelector("#rep-count");
  const phase = document.querySelector("#rep-phase");
  const elbow = document.querySelector("#elbow-angle");
  const body = document.querySelector("#body-angle");
  const message = document.querySelector("#workout-message");
  const reset = document.querySelector("#reset-count");
  const phaseLabels = { ready: "Get ready", up: "Upper position", down: "Lower position" };

  function showResult(result) {
    count.textContent = String(result.rep_count);
    phase.textContent = phaseLabels[result.phase] || "Get ready";
    elbow.textContent = result.elbow_angle === null ? "—" : `${result.elbow_angle}°`;
    body.textContent = result.body_angle === null ? "—" : `${result.body_angle}°`;
    message.textContent = result.message;
  }

  function showPaused(text) {
    phase.textContent = "Paused";
    elbow.textContent = "—";
    body.textContent = "—";
    message.textContent = text;
  }

  async function createSession(signal) {
    const response = await fetch("/api/pushup/session", {
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
      const response = await fetch("/api/pushup/session", {
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
    createSession,
    closeSession,
    showResult,
    showPaused,
    setActive(active) {
      reset.disabled = !active;
    },
  };
}
