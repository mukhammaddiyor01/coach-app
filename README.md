# Coach App

An exercise coach for Push Up, Squats, and Lunge.

## Current progress

Stage four is complete. FastAPI serves exercise pages using Jinja2 templates.
Each workout page has Start camera and Stop camera controls with a live preview.
Camera access is requested only after pressing Start camera. The app stops its
camera tracks when you press Stop camera or leave the workout page.

Permission errors, missing cameras, and disconnected cameras display clear
messages and allow another attempt. Stop camera also cancels a pending start;
the browser permission prompt may still need a response, but its late result
will not reopen the preview.

The preview stays in your browser. This stage does not request microphone
access, record video, upload frames, or analyze exercises. Body landmark
detection and repetition counting come in later stages.

All project content is in English. Instructions remain readable without
JavaScript; the camera controls require JavaScript.

## Install dependencies

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If `.venv` already exists, activate it and install the requirements.

## Run the app

Open the VS Code terminal and run:

```bash
cd /Users/mukhammaddiyor/Desktop/coach-app
source .venv/bin/activate
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 in your browser.
Press `Ctrl + C` in the terminal to stop the server.

The old `python -m http.server` command is no longer used because the HTML
files are now Jinja2 templates that must be rendered by FastAPI.

## Files and request flow

- `backend/main.py` — creates FastAPI and connects static files and routes.
- `backend/routes.py` — page controllers and exercise ID validation.
- `backend/exercises.py` — exercise names and display instructions.
- `frontend/templates/index.html` — exercise selection template.
- `frontend/templates/workout.html` — selected exercise template.
- `frontend/static/css/style.css` — page styles.
- `frontend/static/js/camera.js` — camera start, stop, status, and error handling.
- `tests/camera.test.cjs` — camera lifecycle tests using simulated devices.
- `AGENTS.md` — MVC, service layer, and incremental commit rules.

Page flow: browser → controller → HTML template → browser.
Exercise calculations will belong in services, separate from page content.

## Pages

- `/` — choose an exercise.
- `/workout/pushup` — Push Up instructions.
- `/workout/squats` — Squats instructions.
- `/workout/lunge` — Lunge instructions.

`backend/services/`, `backend/vision/`, and `models/` are currently empty.


## Try the camera

1. Start the app and open a workout page.
2. Press Start camera and allow camera access in your browser.
3. Check that the live preview appears and the header says Camera on.
4. Press Stop camera. The preview should close and the header should say Camera off.
5. Start again, then switch exercises or return home. The camera should stop.
6. If permission is denied, allow it in your browser settings and try again.

Use the localhost address above, or HTTPS when deploying the app.
If another app is using your camera, close it before trying again.

## Camera tests

With Node.js installed, run the frontend lifecycle tests without using a camera:

```bash
node --test tests/camera.test.cjs
```

Node.js is used only for these tests; the application backend remains Python.
The tests cover start and stop, permission errors and retry, duplicate starts,
late permission results, page navigation, playback failure, and disconnection.
Real camera permissions and device behavior still need a check in your browser.
