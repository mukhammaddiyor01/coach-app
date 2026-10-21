// Sample frames, call the local detector, and draw its result. No exercise rules.
const poseVideo = document.querySelector("#camera-video");
const poseCanvas = document.querySelector("#pose-overlay");
const poseMessage = document.querySelector("#pose-message");
const poseContext = poseCanvas.getContext("2d");
const frameCanvas = document.createElement("canvas");
const frameContext = frameCanvas.getContext("2d");
const workoutControls = typeof createWorkoutControls === "function" ? createWorkoutControls() : null;

const FRAME_INTERVAL_MS = 200;
const REQUEST_TIMEOUT_MS = 20_000;
const CAPTURE_MAX_SIDE = 640;
const MIN_LANDMARK_CONFIDENCE = 0.65;
const POSE_CONNECTIONS = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24], [23, 25], [25, 27],
  [24, 26], [26, 28], [27, 29], [29, 31], [28, 30], [30, 32],
];

let poseRunning = false;
let poseRunId = 0;
let poseTimer = null;
let poseRequest = null;
let workoutSession = null;

function isCurrentPoseRun(runId) {
  return poseRunning && runId === poseRunId;
}

function clearPoseOverlay() {
  poseContext?.clearRect(0, 0, poseCanvas.width, poseCanvas.height);
}

function stopPoseDetection() {
  poseRunning = false;
  poseRunId += 1;
  clearTimeout(poseTimer);
  poseRequest?.abort();
  poseRequest = null;
  clearPoseOverlay();

  // Release the last sampled camera pixels when detection stops.
  frameCanvas.width = 0;
  frameCanvas.height = 0;
  poseMessage.textContent = "Body detection is off.";
  if (workoutControls) {
    workoutControls.setActive(false);
    workoutControls.showPaused("Camera stopped. Last received count is shown. Starting again begins at zero.");
    closeCountingSession();
  }
}

function closeCountingSession() {
  if (!workoutSession) {
    return;
  }
  const token = workoutSession;
  const stoppedRunId = poseRunId;
  workoutSession = null;
  workoutControls.closeSession(token).then((closed) => {
    if (!closed && !poseRunning && poseRunId === stoppedRunId) {
      workoutControls.showPaused("Camera stopped. Temporary counting state will expire within 10 minutes.");
    }
  });
}

async function startPoseDetection() {
  stopPoseDetection();

  if (!poseContext || !frameContext) {
    poseMessage.textContent = "This browser cannot draw body landmarks.";
    return;
  }

  poseRunning = true;
  const runId = ++poseRunId;
  poseMessage.textContent = "Starting local body detection…";
  if (workoutControls) {
    const request = new AbortController();
    poseRequest = request;
    const timeout = setTimeout(() => request.abort(), REQUEST_TIMEOUT_MS);
    try {
      const session = await workoutControls.createSession(request.signal);
      if (!isCurrentPoseRun(runId)) {
        // A late session response must never replace the next camera run.
        await workoutControls.closeSession(session.session_id);
        return;
      }
      workoutSession = session.session_id;
      workoutControls.showResult(session.workout);
      workoutControls.setActive(true);
    } catch (error) {
      if (isCurrentPoseRun(runId)) {
        stopPoseDetection();
        poseMessage.textContent = "Could not start local counting. Stop and restart the camera to try again.";
        workoutControls.showPaused("Counting is unavailable. Check the local Python server and restart the camera.");
      }
      return;
    } finally {
      clearTimeout(timeout);
      if (poseRequest === request) {
        poseRequest = null;
      }
    }
  }
  return analyzeNextFrame(runId);
}

function captureCameraFrame() {
  const scale = Math.min(
    CAPTURE_MAX_SIDE / poseVideo.videoWidth,
    CAPTURE_MAX_SIDE / poseVideo.videoHeight,
    1,
  );
  frameCanvas.width = Math.max(1, Math.round(poseVideo.videoWidth * scale));
  frameCanvas.height = Math.max(1, Math.round(poseVideo.videoHeight * scale));
  frameContext.drawImage(poseVideo, 0, 0, frameCanvas.width, frameCanvas.height);

  return new Promise((resolve) => frameCanvas.toBlob(resolve, "image/jpeg", 0.75));
}

function isVisibleLandmark(point) {
  return point && point.visibility >= MIN_LANDMARK_CONFIDENCE
    && point.presence >= MIN_LANDMARK_CONFIDENCE
    && point.x >= 0 && point.x <= 1 && point.y >= 0 && point.y <= 1;
}

function drawPoseLandmarks(result) {
  poseCanvas.width = result.width;
  poseCanvas.height = result.height;
  clearPoseOverlay();
  poseContext.strokeStyle = "#c5f167";
  poseContext.fillStyle = "#c5f167";
  poseContext.lineWidth = 3;

  for (const [startIndex, endIndex] of POSE_CONNECTIONS) {
    const start = result.landmarks[startIndex];
    const end = result.landmarks[endIndex];
    if (!isVisibleLandmark(start) || !isVisibleLandmark(end)) {
      continue;
    }

    poseContext.beginPath();
    poseContext.moveTo(start.x * result.width, start.y * result.height);
    poseContext.lineTo(end.x * result.width, end.y * result.height);
    poseContext.stroke();
  }

  const visibleLandmarks = result.landmarks.filter(isVisibleLandmark);
  for (const point of visibleLandmarks) {
    poseContext.beginPath();
    poseContext.arc(point.x * result.width, point.y * result.height, 4, 0, Math.PI * 2);
    poseContext.fill();
  }

  poseMessage.textContent = visibleLandmarks.length
    ? `Body detected · ${visibleLandmarks.length} visible landmarks.${workoutControls ? "" : " Repetition counting comes later."}`
    : "No visible body landmarks. Move back so your whole body is in the frame.";
}

async function analyzeNextFrame(runId) {
  if (!isCurrentPoseRun(runId)) {
    return;
  }

  if (!poseVideo.videoWidth || !poseVideo.videoHeight) {
    poseTimer = setTimeout(() => analyzeNextFrame(runId), FRAME_INTERVAL_MS);
    return;
  }

  let request = null;
  let timeout = null;
  let nextDelay = FRAME_INTERVAL_MS;

  try {
    const frame = await captureCameraFrame();
    if (!isCurrentPoseRun(runId)) {
      return;
    }
    if (!frame) {
      throw new Error("Could not sample the camera frame.");
    }

    request = new AbortController();
    poseRequest = request;
    timeout = setTimeout(() => request.abort(), REQUEST_TIMEOUT_MS);
    const headers = { "Content-Type": "image/jpeg", "X-Coach-Camera": "1" };
    if (workoutSession) {
      headers["X-Coach-Session"] = workoutSession;
    }
    const endpoint = workoutControls ? workoutControls.frameEndpoint : "/api/pose";
    const response = await fetch(endpoint, {
      method: "POST",
      mode: "same-origin",
      credentials: "omit",
      cache: "no-store",
      headers,
      body: frame,
      signal: request.signal,
    });
    const result = await response.json();

    if (!isCurrentPoseRun(runId)) {
      return;
    }

    if (!response.ok) {
      clearPoseOverlay();
      poseMessage.textContent = result.detail || "Local body detection is unavailable.";
      if (response.status === 429) {
        nextDelay = 1000;
        workoutControls?.showPaused("Tracking is busy. Last received count is shown.");
      } else {
        const detail = poseMessage.textContent;
        stopPoseDetection();
        poseMessage.textContent = detail + " Stop and restart the camera after resolving this issue.";
      }
      return;
    }

    drawPoseLandmarks(result);
    if (workoutControls && result.workout) {
      workoutControls.showResult(result.workout);
    }
  } catch (error) {
    if (!isCurrentPoseRun(runId)) {
      return;
    }

    clearPoseOverlay();
    poseMessage.textContent = "Waiting for local body detection. Check that the Python server is running.";
    workoutControls?.showPaused("Tracking is paused. Last received count is shown; waiting for the local server.");
    nextDelay = 1000;
  } finally {
    clearTimeout(timeout);
    if (poseRequest === request) {
      poseRequest = null;
    }

    // Schedule only after this request finishes; never build a frame queue.
    if (isCurrentPoseRun(runId)) {
      poseTimer = setTimeout(() => analyzeNextFrame(runId), nextDelay);
    }
  }
}
