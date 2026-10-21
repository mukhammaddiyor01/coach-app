# Coach App — Project Development Rules

## 1. Goal and Current Stage

Build a small camera-based project for Push Up, Squats, and Lunge exercises.
The user selects an exercise and turns on the camera. The app counts
repetitions and provides feedback on the posture features it can observe.

The user has authorized starting implementation. The current milestone is
mobile web: adapt the existing selection and workout pages for phone screens,
portrait and landscape camera previews, and touch-friendly camera controls.
All three counters are implemented. Detailed posture feedback is a later milestone.
Implement only this milestone; later stages require user authorization.
The structure below is the target plan. Some files exist; create the remaining
files only when their implementation stage is authorized.
Work only inside this repository root (`coach-app/`).

## 2. Selected Technologies

- FastAPI: receive requests and return responses.
- HTML, CSS, JavaScript: pages, buttons, and browser camera access.
- Jinja2: render HTML templates through FastAPI; installed for page rendering.
- MediaPipe: detect body landmarks.
- OpenCV and NumPy: process images.
- A database is not required at this stage.

Do not introduce React, Django, a Node.js backend, or additional architecture
without agreement from the user.

## 3. MVC and the Service Layer

Model — `backend/models.py`: future database tables.
Do not create database models or a database yet. MediaPipe output is not
a database model.

View — `frontend/templates/`: HTML pages displayed to the user.
Styling and browser behavior belong in `frontend/static/`.

Controller — `backend/routes.py`: receive requests, validate incoming data,
call the appropriate service, and return responses.
Do not put elbow or knee angle calculations or repetition-counting rules here.

Service — `backend/services/`: exercise calculation rules.
Write this layer in plain Python. Keep it independent of FastAPI, HTTP,
WebSocket, Pydantic, MediaPipe, OpenCV, and the database.

Vision adapter — `backend/vision/`: MediaPipe and image-processing work.
Convert frames into body landmarks. Do not decide whether an exercise
is performed correctly in this layer.

## 4. Planned Folder and File Structure

```text
coach-app/
├── AGENTS.md
├── requirements.txt
├── .gitignore
├── .venv/
├── backend/
│   ├── main.py                 # Create FastAPI; connect routes, static files, templates
│   ├── routes.py               # Controller: page and analysis requests
│   ├── security.py             # HTTP policies and public asset restrictions
│   ├── exercises.py            # Exercise names and display instructions
│   ├── schemas.py              # Input/output formats, when needed
│   ├── models.py               # Database tables, only when a database is added
│   ├── services/
│   │   ├── calculations.py     # Shared angle and distance calculations
│   │   ├── pushup_service.py   # Push Up rules
│   │   ├── squats_service.py   # Squats rules
│   │   └── lunge_service.py    # Lunge rules
│   └── vision/
│       └── pose_detector.py   # Frame → body landmarks
├── frontend/
│   ├── templates/
│   │   ├── index.html         # Selection page for the three exercises
│   │   └── workout.html       # Selected exercise, camera, and results
│   └── static/
│       ├── css/
│       ├── js/
│       └── images/
└── models/                    # Downloaded AI model files, not database tables
```

Do not create all planned files at once.
Create only the files needed for the stage currently being implemented.

## 5. Application Flow

Opening a page:
Browser → routes.py → HTML template → browser.

Analyzing an exercise:
Camera frame → routes.py → vision/pose_detector.py → body landmarks
→ selected exercise service → result → routes.py → browser.

The controller coordinates the flow. Vision interprets the image.
The service applies exercise rules. The frontend displays the result.
Do not implement a second, separate repetition counter in the frontend.

## 6. Human-Readable Business Logic

- Keep each exercise in its own service file.
- Use clear names: `calculate_angle`, `elbow_angle`, `knee_angle`,
  `body_angle`, `rep_count`, `current_phase`, `is_body_straight`.
- Avoid vague names such as `x1`, `tmp`, or `val` in core calculations.
- Each function must perform one understandable task. Split large functions
  into smaller functions. Keep code formatting readable: use normal indentation,
  separate logical steps with blank lines, and avoid compressed one-line functions.
- Explain why a rule is needed with a short comment in English.
- Store angle thresholds in named settings; do not scatter them through the code.
- Account for image width and height when working with image landmarks.
- Keep counts and state separate for each camera session.
  Do not create a shared global counter for all users.

Repetition-counting rules:
1. Confirm the upper position first.
2. Then confirm the lower position.
3. Increment the count once when the user returns to the upper position.
4. Holding a position or jittering around a threshold must not increase the count.
5. If the body becomes invisible, discard the incomplete repetition and preserve
   the count of completed repetitions.

Push Up: track elbow bending and a horizontal, straight body position.
Squats: track knee bending and the return to a standing position.
Lunge: start with stationary lunges; feet are positioned forward and backward,
both knees bend, and the user returns to the upper position.

Angle thresholds are experimental settings, not universal exercise standards.
Do not promise that the app detects every technique error.
Do not evaluate a posture that cannot be observed.

## 7. Validation and Errors

Check invalid or missing data first and return early using guard clauses.
Avoid deeply nested `if/else` blocks.

Do not use `assert` to enforce business rules. Use explicit exceptions when
needed, such as `UnsupportedExerciseError` or `InvalidLandmarksError`.
Do not use `HTTPException` inside services. The controller translates service
errors into appropriate API responses.

An invisible body is a normal tracking state: return guidance to wait or
adjust the camera position.
Do not hide real errors with `except: pass`.

Service calculations must be testable without starting the camera or server.
Checks must cover full repetitions, incomplete repetitions, jitter, lost
tracking, reset, and isolation between sessions.

## 8. Avoid Unnecessary Complexity

Do not create a separate domain folder, abstract classes, repositories,
dependency injection containers, or ports/adapters interfaces at this stage.
Plain Python service functions and a separate vision adapter are sufficient.
Add such extra layers only when a concrete need arises.

## 9. Implementation Order

1. A simple page with Push Up, Squats, and Lunge buttons.
2. A page and instructions for the selected exercise.
3. Serve the pages through FastAPI.
4. Connect the browser camera and implement stopping it.
5. Detect body landmarks with MediaPipe.
6. Implement and verify Push Up counting first.
7. Add Squats and Lunge rules one at a time.
8. Add posture feedback.

Explain each stage briefly. If the user wants to write the code themselves,
provide explanations only. Implement only the stage authorized by the user;
do not write later stages on your own initiative.
Request camera permission only after a user action. Stop the camera tracks
when the camera is turned off. Do not save video by default.

## 10. Commit Messages

Use only `feat:` and `fix:` prefixes for commit messages.
- `feat:` for new functionality or additions.
- `fix:` for corrections to existing behavior or files.
Do not use other prefixes such as `chore:`, `docs:`, `refactor:`, or `test:`.
Write a short, clear description after the prefix.

Commit each completed logical change immediately after verifying it, using
`feat:` or `fix:`. Each commit must cover one small, complete, coherent change.
Do not accumulate unrelated changes, multiple large features, or the entire
project into a single commit. Split larger work into small, independently
verifiable steps and commit each completed step before starting the next.
Stage only the files or hunks belonging to that logical change.


## 11. Project Language

Use English for the entire project: interface text, exercise instructions,
page titles, accessibility labels, loading and error messages, code comments,
and project documentation. Keep future additions in English as well.
Conversation with the user may remain in Uzbek unless they request otherwise.


## 12. Privacy and Confidential Data

- Never commit credentials, API keys, tokens, passwords, private keys, local
  environment files, logs, databases, or camera captures. Keep them outside
  public asset folders and cover local files with `.gitignore`.
- A committed `.env.example` may contain variable names and empty placeholders
  only. Real values belong in local environment variables or an ignored file.
- Never put secrets in HTML, browser JavaScript, query strings, error messages,
  logs, screenshots, documentation, or commit messages.
- Avoid machine-specific paths and personal identifiers in tracked documentation.
- Before committing, review the exact staged files for sensitive content.
  `.gitignore` does not remove files that are already tracked or in Git history.
- Do not print secret values while checking them. Report filenames and counts
  only. If an actual credential is discovered in history, do not push it; arrange
  credential rotation and history cleanup without exposing its value.
- Local pose analysis is now authorized. Process sampled camera frames only
  on this computer. Do not record, persist, or send them to a third-party service.
- When local pose analysis is authorized, send only the frames needed for
  analysis to the local backend, process them in memory, and explain that data
  flow in the interface. Do not retain frames or landmarks by default.
- Stop the camera when the user stops it, leaves the page, or hides the tab.
- Serve only intended public assets. Never expose the repository root, local
  environment files, private directories, or model files as static content.
- Keep external scripts, analytics, and third-party image/font requests out of
  the interface. Use restrictive browser policies and local-only host settings.
- Keep debug tracebacks out of HTTP responses. This local prototype must not
  be exposed publicly without an explicit deployment and access-control review.
