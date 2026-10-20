# Coach App

An exercise coach for Push Up, Squats, and Lunge.

## Current progress

Stage two is complete. Each exercise card opens its own instruction page,
including camera placement and starting position guidance. You can switch
between exercises or return to the home page. An unknown exercise URL displays
a clear error message.

The camera button is currently disabled. FastAPI page serving and repetition
counting will be added in later stages. All project content is in English.

## Run the frontend

Open the VS Code terminal and run:

```bash
cd /Users/mukhammaddiyor/Desktop/coach-app
source .venv/bin/activate
python -m http.server 5500 --bind 127.0.0.1 --directory frontend
```

Open http://127.0.0.1:5500/templates/index.html in your browser.
Press `Ctrl + C` in the terminal to stop the server.

This stage uses Python's built-in file server. The FastAPI run command will
be added when the backend is implemented.

## Files

- `frontend/templates/index.html` — exercise selection page.
- `frontend/templates/workout.html` — selected exercise page.
- `frontend/static/css/style.css` — page styles.
- `frontend/static/js/workout.js` — exercise instructions and page content.
- `AGENTS.md` — MVC, service layer, and incremental commit rules.

`backend/services/`, `backend/vision/`, and `models/` are currently empty.
