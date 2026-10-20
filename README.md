# Coach App

An exercise coach for Push Up, Squats, and Lunge.

## Current progress

Stage three is complete. FastAPI serves the exercise selection page and
individual workout pages using Jinja2 templates. Instructions are rendered on
the server and are readable without JavaScript. Each page includes camera
placement and starting position guidance. Unknown exercise IDs return a
readable error page with HTTP status 404.

The camera button is currently disabled. Camera access and repetition counting
will be added in later stages. All project content is in English.

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
- `AGENTS.md` — MVC, service layer, and incremental commit rules.

Page flow: browser → controller → HTML template → browser.
Exercise calculations will belong in services, separate from page content.

## Pages

- `/` — choose an exercise.
- `/workout/pushup` — Push Up instructions.
- `/workout/squats` — Squats instructions.
- `/workout/lunge` — Lunge instructions.

`backend/services/`, `backend/vision/`, and `models/` are currently empty.
