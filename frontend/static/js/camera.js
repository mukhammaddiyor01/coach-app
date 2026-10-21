// Camera controls only. Exercise rules and repetition counts belong in Python.
const cameraStage = document.querySelector("#camera-stage");
const cameraVideo = document.querySelector("#camera-video");
const cameraPlaceholder = document.querySelector("#camera-placeholder");
const cameraTitle = document.querySelector("#camera-title");
const cameraMessage = document.querySelector("#camera-message");
const cameraStatus = document.querySelector("#camera-status");
const cameraStatusText = document.querySelector("#camera-status-text");
const startCameraButton = document.querySelector("#start-camera");
const stopCameraButton = document.querySelector("#stop-camera");

const CAMERA_CONSTRAINTS = {
  video: { width: { ideal: 1280 }, height: { ideal: 720 } },
  audio: false,
};

const CAMERA_STATUS_LABELS = {
  off: "Camera off",
  starting: "Connecting camera",
  on: "Camera on",
  error: "Camera off",
};

let cameraStream = null;
let cameraState = "off";
let cameraRequestId = 0;

function showCameraState(state, message) {
  cameraState = state;
  const isCameraOn = state === "on";
  const isStarting = state === "starting";

  cameraStatus.dataset.state = state;
  cameraStatusText.textContent = CAMERA_STATUS_LABELS[state];
  cameraTitle.textContent = isCameraOn ? "Live camera" : "Get camera ready";
  cameraMessage.textContent = message;
  cameraVideo.hidden = !isCameraOn;
  cameraStage.hidden = !isCameraOn;
  cameraPlaceholder.hidden = isCameraOn;
  startCameraButton.disabled = isStarting || isCameraOn;
  startCameraButton.textContent = isStarting ? "Starting…" : "Start camera";
  stopCameraButton.disabled = !isStarting && !isCameraOn;
}

function stopStreamTracks(stream) {
  if (!stream) {
    return;
  }

  stream.getTracks().forEach((track) => track.stop());
}

function stopCamera() {
  // Invalidate pending permission requests so late results cannot reopen the camera.
  cameraRequestId += 1;
  stopStreamTracks(cameraStream);
  cameraStream = null;
  cameraVideo.pause();
  cameraVideo.srcObject = null;
  showCameraState("off", "Camera stopped. Press Start camera when you are ready.");

  // Release camera hardware even if the analysis script did not load.
  if (typeof stopPoseDetection === "function") {
    stopPoseDetection();
  }
}

function stopCameraWhenTabIsHidden() {
  if (!document.hidden) {
    return;
  }

  stopCamera();
}

function getCameraErrorMessage(error) {
  const messages = {
    NotAllowedError: "Camera access was denied. Allow camera access in your browser and try again.",
    SecurityError: "Camera access is blocked. Check your browser settings and open the app on localhost or HTTPS.",
    NotFoundError: "No camera was found. Connect a camera and try again.",
    NotReadableError: "The camera could not be opened. Close other apps using it and try again.",
    OverconstrainedError: "This camera cannot provide the requested video. Try another camera.",
  };

  return messages[error.name] || "The camera could not start. Check your device and try again.";
}

function handleCameraDisconnected(requestId) {
  if (requestId !== cameraRequestId) {
    return;
  }

  stopCamera();
  showCameraState("error", "The camera was disconnected. Reconnect it and press Start camera.");
}

async function startCamera() {
  if (cameraState === "starting" || cameraState === "on") {
    return;
  }

  if (!navigator.mediaDevices?.getUserMedia) {
    showCameraState("error", "Camera access is unavailable. Open the app on localhost or HTTPS in a supported browser.");
    return;
  }

  const requestId = ++cameraRequestId;
  let requestedStream = null;
  showCameraState("starting", "Allow camera access in your browser, or press Stop camera to cancel.");

  try {
    requestedStream = await navigator.mediaDevices.getUserMedia(CAMERA_CONSTRAINTS);

    if (requestId !== cameraRequestId) {
      stopStreamTracks(requestedStream);
      return;
    }

    cameraStream = requestedStream;
    cameraVideo.srcObject = cameraStream;
    await cameraVideo.play();

    if (requestId !== cameraRequestId) {
      stopStreamTracks(requestedStream);
      return;
    }

    const hasLiveVideo = cameraStream.getVideoTracks().some((track) => track.readyState === "live");

    if (!hasLiveVideo) {
      handleCameraDisconnected(requestId);
      return;
    }

    cameraStream.getVideoTracks().forEach((track) => {
      track.addEventListener("ended", () => handleCameraDisconnected(requestId), { once: true });
    });

    showCameraState("on", "Keep your whole body in view for local body detection.");
    if (typeof startPoseDetection === "function") {
      startPoseDetection();
    } else {
      cameraMessage.textContent = "Live preview is available, but body detection did not load. Refresh the page.";
    }
  } catch (error) {
    stopStreamTracks(requestedStream);

    // An older request must not change a newer camera session.
    if (requestId !== cameraRequestId) {
      return;
    }

    cameraStream = null;
    cameraVideo.srcObject = null;
    showCameraState("error", getCameraErrorMessage(error));
  }
}

startCameraButton.addEventListener("click", startCamera);
stopCameraButton.addEventListener("click", stopCamera);
window.addEventListener("pagehide", stopCamera);
document.addEventListener("visibilitychange", stopCameraWhenTabIsHidden);
