# Coach App

An exercise coach for Push Up, Squats, and Lunge.

## Current progress

Stage four is complete. FastAPI serves exercise pages using Jinja2 templates.
Each workout page has Start camera and Stop camera controls with a live preview.
Camera access is requested only after pressing Start camera. The app stops its
camera tracks when you press Stop camera, leave the workout page, or hide the
tab. Returning to the tab does not restart the camera automatically.

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
cd /path/to/coach-app
source .venv/bin/activate
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Open http://127.0.0.1:8000 in your browser.
Press `Ctrl + C` in the terminal to stop the server.

The old `python -m http.server` command is no longer used because the HTML
files are now Jinja2 templates that must be rendered by FastAPI.

## Files and request flow

- `backend/main.py` — creates FastAPI and connects static files and routes.
- `backend/routes.py` — page controllers and exercise ID validation.
- `backend/security.py` — HTTP policies and allowed public asset types.
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
5. Start again, then switch exercises, return home, or switch to another tab.
   The camera should stop. Return and press Start camera to use it again.
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
late permission results, page navigation, hidden tabs, playback failure, and
disconnection.
Real camera permissions and device behavior still need a check in your browser.


## Confidential files

Keep credentials in local environment variables or an ignored `.env` file.
Do not add real values to HTML, JavaScript, documentation, or screenshots.
Only empty configuration examples may be committed as `.env.example`.
Logs, databases, private data folders, and camera captures are ignored by Git.
Review staged files before every commit: ignore rules do not remove old commits
or files that are already tracked.


## Local HTTP privacy protections

- Only localhost and 127.0.0.1 hostnames are accepted. Keep the server bound to
  127.0.0.1; host validation is not a replacement for network access controls.
- Browser policies restrict scripts, styles, images, and connections to this app
  and disallow framing. The camera is allowed for this origin; microphone and
  location access are blocked.
- Responses use `Cache-Control: no-store` and `Referrer-Policy: no-referrer`.
- Static serving allows only public CSS, JavaScript, image, and font file types.
  Dotfiles, recordings, model files, databases, and key files are not served.
- Debug mode and API documentation endpoints are disabled.
- The run command disables request access logs so URLs are not written there.

These protections apply to this local prototype. Do not publish it as a public
service without adding appropriate authentication and reviewing data handling.
If a real credential was ever committed, ignoring the file is not sufficient:
rotate the credential and remove it from history before publishing.

## HTTP privacy tests

Install the optional test dependency and run the checks:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -p 'test_*.py'
```

These tests use an in-process client and temporary dummy files. They do not
access the camera or transmit project data to external services.
