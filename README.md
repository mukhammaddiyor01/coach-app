# Coach App

A local exercise coach for Push Up, Squats, and Lunge.

## Current progress

Stage five is complete: the app detects body landmarks with MediaPipe and draws
them over the camera preview. It does not count repetitions or judge exercise
technique yet. Those rules will be added separately in Python services.

Choose an exercise, read its setup instructions, and press Start camera.
Sampled JPEG frames are sent only to the Python server on this computer.
MediaPipe returns body landmarks; the browser draws visible points and lines.
If no body is found, the app asks you to move into view.

Stop camera, leave the page, or hide the tab to stop both the camera and analysis.
Returning to a tab does not automatically restart them. Permission errors and
camera disconnections have readable messages and can be retried.

## Install and download the model

In a terminal opened at the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python download_model.py
```

If `.venv` already exists, activate it and install the requirements.
The downloader uses Google's official versioned MediaPipe model URL. The model
is kept in `models/pose_landmarker.task`, outside public static files and Git.
The download contains model weights, not camera data. Once installed, inference
does not need an external image or AI service.

## Run the app

From the project root:

```bash
source .venv/bin/activate
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Open http://127.0.0.1:8000 in your browser.
Press `Ctrl + C` in the terminal to stop the server.
Use localhost or HTTPS for browser camera access. The first analysis request
can take a few seconds while the model loads.

## Clear responsibilities

- `backend/main.py` — create the app and close the detector on shutdown.
- `backend/routes.py` — page controllers, request validation, and HTTP responses.
- `backend/schemas.py` — the public landmark response format.
- `backend/exercises.py` — exercise names and display instructions.
- `backend/vision/pose_detector.py` — JPEG decoding and MediaPipe inference.
- `backend/security.py` — HTTP policies and allowed public assets.
- `frontend/templates/` — page layout and setup instructions.
- `frontend/static/js/camera.js` — camera permission, start, and stop.
- `frontend/static/js/pose.js` — sample frames, call the local API, draw landmarks.
- `backend/services/` — reserved for exercise rules in the next stages.

Current flow:
Camera → local controller → vision adapter → landmarks → browser overlay.
The frontend does not calculate angles or count repetitions.

## Frame limits and session handling

`POST /api/pose` accepts only JPEG frames, up to 1 MB and 1280 pixels per side.
The frontend samples at most 640 pixels per side and waits for each response
before sending another frame. Inference uses independent-image mode, so one
user's video history is not reused for another. An overlapping frame receives
a busy response rather than creating an inference queue.

Only frames from this app's camera controls are accepted. Foreign origins and
requests without the custom camera header are rejected. A successful response
contains dimensions and up to 33 landmarks; no body is a normal empty result.

## Privacy

- Camera frames and landmarks are processed in memory and are not saved.
- No microphone access, recordings, analytics, or third-party frame uploads.
- Sampled canvas pixels and displayed landmarks are cleared when analysis stops.
- Credentials belong in local environment variables or an ignored `.env` file.
  Never put real values in HTML, JavaScript, documentation, or screenshots.
- Logs, databases, keys, and private capture folders are ignored by Git.
  `.env.example`, if created, must contain empty placeholders only.
- Static serving blocks dotfiles, recordings, models, databases, and key files.
- Browser policies restrict connections to this app and block framing,
  microphone access, and location access.
- Responses use no-store caching and no-referrer policies. Debug mode and API
  documentation are disabled. The run command disables request access logs.
- Only localhost and 127.0.0.1 hosts are allowed. Keep the server bound to
  127.0.0.1; host validation is not network access control or authentication.

Review staged files before each commit. Ignore rules cannot remove credentials
from existing commits. If a real credential was committed, rotate it and clean
history before publishing. Do not expose this local prototype publicly without
an explicit access-control and data-handling review.

## Verify in your browser

1. Open a workout page and allow camera access after pressing Start camera.
2. Keep your whole body visible. Look for body landmarks over the video.
3. Move out of view. Old landmarks should disappear.
4. Press Stop camera. The preview and analysis should stop.
5. Start again, then switch exercises, return home, or hide the tab.
6. If model setup fails, run `python download_model.py` and restart the camera.

Automatic checks use simulated cameras and public test images, not your webcam.
Real camera permissions and device behavior still need this browser check.

## Automated checks

Install the optional HTTP test dependency:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -p 'test_*.py'
```

With Node.js installed, run frontend lifecycle and rendering checks:

```bash
node --test tests/camera.test.cjs tests/pose.test.cjs
```

Node.js is only used for tests. The app backend remains Python.
The local adapter and real API have also been checked with Google's public
MediaPipe pose sample (33 landmarks) and a blank image (no body).
