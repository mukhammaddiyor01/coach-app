# Coach App

A local exercise coach for Push Up, Squats, and Lunge.

## Current progress

Stage seven is implemented: Push Up, Squats, and stationary Lunge each have
a separate plain Python counting service. All three pages display the count,
position, relevant angles, guidance, and a Reset count button. Detailed posture
feedback is a later milestone. The app cannot check every technique error.

Choose an exercise, read its setup instructions, and press Start camera.
Sampled JPEG frames are sent only to the Python server on this computer.
MediaPipe returns body landmarks; the browser draws visible points and lines.
If no body is found, the app asks you to move into view.

For Push Up, use a side view and keep your shoulder, elbow, wrist, hip, knee,
and ankle visible. Hold the upper position, lower your body, then return to
the upper position. This complete sequence counts once. Holding a position,
starting at the bottom, or making an incomplete movement does not count.
If tracking is lost, the incomplete repetition is discarded and completed
repetitions remain. Displayed Push Up and Squats angles describe the currently
tracked side.

For Squats, stand side-on with your shoulder, hip, knee, and ankle visible.
Start standing, bend your knees and hips, then return to standing. The service
tracks one visible leg and keeps that side for the current tracking sequence.

For Lunge, begin upright with one foot forward and the other behind. Keep both
hips, knees, and ankles visible. Bend both knees in place, then straighten both
legs to complete one repetition. A movement of only one knee does not count.
The screen shows left and right knee angles. Obvious changes in leg order or
relative stance width discard the incomplete repetition, so start from the
upper position again after changing the lead leg. This is a stationary-lunge
counter; it does not reliably classify walking lunges or every foot movement.

Reset count starts a new counting session while the camera stays on.
Stop camera keeps the last received count on screen. Starting again begins at
zero. Network delays can make the displayed count lag behind the server;
paused results are labelled, and late replies cannot overwrite a reset.

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

- `backend/main.py` — create the app and clear temporary state on shutdown.
- `backend/routes.py` — page controllers, request validation, and HTTP responses.
- `backend/schemas.py` — public landmark, workout, and session response formats.
- `backend/exercises.py` — exercise names and display instructions.
- `backend/vision/pose_detector.py` — JPEG decoding and MediaPipe inference.
- `backend/security.py` — HTTP policies and allowed public assets.
- `frontend/templates/` — page layout and setup instructions.
- `frontend/static/js/camera.js` — camera permission, start, and stop.
- `frontend/static/js/pose.js` — sample frames, call the local API, draw landmarks.
- `backend/services/calculations.py` — shared pixel-based angle calculations.
- `backend/services/pushup_service.py` — Push Up validation and counting rules.
- `backend/services/squats_service.py` — Squats rules for the visible leg.
- `backend/services/lunge_service.py` — stationary Lunge rules for both legs.
- `backend/services/observations.py` — shared landmark validation and pixel conversion.
- `backend/services/repetition_counter.py` — upper/lower sequence tracking for leg exercises.
- `backend/workout_sessions.py` — isolated, temporary counting state and cleanup.
- `frontend/static/js/workout.js` — display Python results and manage exercise sessions.

Current flow:
Camera → local controller → vision adapter → landmarks → selected exercise service
→ workout result → browser display and overlay.
The frontend does not calculate exercise angles or count repetitions.

The services use named experimental settings:

| Exercise | Upper position | Lower position |
| --- | --- | --- |
| Push Up | Elbow angle at least 155° | Elbow angle at most 100° |
| Squats | Knee angle at least 160° | Knee angle at most 105° |
| Lunge | Both knee angles at least 150° | Both knee angles at most 110° |

Positions must persist for at least 0.15 seconds. Gaps longer than one second
discard an incomplete repetition. Push Up additionally requires a horizontal,
straight body, knee angle of at least 160°, and visible wrist support. Squats
requires a visibly upright torso and a supported leg. Lunge requires an upright
torso, visible legs, and separated feet. These simple 2D checks are prototype
settings, not universal exercise standards or a complete technique assessment.
Adjust named settings in Python after camera testing. Angles are calculated in
pixel coordinates so the frame's width and height are both accounted for.

## Frame limits and session handling

`POST /api/pose` and `POST /api/{exercise_id}/frame` accept only JPEG frames,
up to 1 MB and 1280 pixels per side. The supported exercise identifiers are
`pushup`, `squats`, and `lunge`.
The frontend samples at most 640 pixels per side and waits for each response
before sending another frame. Inference uses independent-image mode, so one
user's video history is not reused for another. An overlapping frame receives
a busy response rather than creating an inference queue.

Only frames from this app's camera controls are accepted. Foreign origins and
requests without the custom camera header are rejected. A successful response
contains dimensions and up to 33 landmarks; no body is a normal empty result.
Exercise frame endpoints also return the count, phase, relevant angles, and guidance.

`POST /api/{exercise_id}/session` creates temporary counting state and returns
the session identifier, exercise identifier, and initial workout result. Send
the session identifier in the `X-Coach-Session` header on frame requests and on
`DELETE /api/{exercise_id}/session` to close it. A session is bound to its
exercise; another exercise's endpoint cannot use or close it. Identifiers stay in browser memory and
request headers; they are not placed in URLs, cookies, or local storage.
Each camera run has its own counter. Reset closes the old session and creates
a new one; there is no shared global repetition count.

State is bounded to 32 sessions. Idle sessions expire after 10 minutes and
are removed on the next session lookup or creation, or at server shutdown.
The browser requests cleanup on Stop, navigation, and hiding the tab. If the
server is unreachable or a session-creation reply is lost, expiration provides
a fallback. Only counting state and primitive tracking settings are retained;
frames and landmark coordinates are not.
Use one server process: sessions live in memory, so restarting or reloading the
server clears them. Restart the camera if its session ends.

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
3. On each exercise page, hold the upper position, lower with control, and
   return up. The count should increase once. Holding either position should
   not add repetitions. On Squats, a half movement should not count. On Lunge,
   keep both legs visible and feet in place; both knees must bend and straighten.
4. Move out of view during an incomplete repetition. Old landmarks should
   disappear, the incomplete movement should be discarded, and the count kept.
5. Press Reset count. It should return to zero with the camera still running.
6. Press Stop camera. The preview should stop and the last count remain visible.
7. Start again: the count begins at zero. Switch exercises, return home, or hide
   the tab to confirm the camera stops. The selected exercise should show its
   own count and angles. Separate browser windows must have independent counts.
8. If model setup fails, run `python download_model.py` and restart the camera.

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

All three exercise services have tests for complete and incomplete repetitions,
short position jitter,
missing or low-confidence joints, posture readiness, frame aspect ratios,
tracking gaps, reset, session isolation, bounded state, HTTP protections, and
late browser responses. Synthetic landmark sequences check the counting path
through the API for every exercise; a generated blank JPEG checks the actual
MediaPipe path and its zero-count waiting result for all three endpoints. Real exercise counting still needs the manual
camera check above.
