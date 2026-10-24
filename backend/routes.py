"""Controllers coordinate pages, local vision, and exercise services."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.exercises import EXERCISES
from backend.schemas import CountCheckInput, CountCheckResult, PoseResult, WorkoutPoseResult, SessionResult
from backend.services.count_validation import compare_counts
from backend.services.observations import InvalidLandmarksError
from backend.workout_sessions import (
    SessionLimitError, SessionNotFoundError, WorkoutSessions, get_workout_sessions,
)
from backend.vision.pose_detector import (
    MAX_FRAME_BYTES,
    InvalidFrameError,
    ModelUnavailableError,
    PoseBusyError,
    PoseDetectionError,
    PoseDetector,
    get_pose_detector,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(directory=PROJECT_ROOT / "frontend" / "templates")
router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="home")
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@router.get("/workout/{exercise_id}", response_class=HTMLResponse, name="workout")
def workout(request: Request, exercise_id: str):
    exercise = EXERCISES.get(exercise_id)

    # Unknown exercises receive a readable page and a real HTTP 404 status.
    if exercise is None:
        return templates.TemplateResponse(
            request=request,
            name="workout.html",
            context={"exercise": None},
            status_code=404,
        )

    return templates.TemplateResponse(
        request=request,
        name="workout.html",
        context={
            "exercise": exercise,
            "exercise_id": exercise_id,
            "exercises": EXERCISES,
        },
    )


@router.get("/workout/{exercise_id}/camera", response_class=HTMLResponse, name="camera")
def camera(request: Request, exercise_id: str):
    exercise = EXERCISES.get(exercise_id)
    return templates.TemplateResponse(
        request=request,
        name="camera.html",
        context={"exercise": exercise, "exercise_id": exercise_id},
        status_code=200 if exercise is not None else 404,
    )


def validate_camera_request(request: Request):
    # A custom header prevents another website from submitting a simple form.
    if request.headers.get("x-coach-camera") != "1":
        raise HTTPException(status_code=403, detail="Use this app's camera controls.")

    origin = request.headers.get("origin")
    expected_origin = str(request.base_url).rstrip("/")
    if origin is not None and origin != expected_origin:
        raise HTTPException(status_code=403, detail="Cross-origin camera requests are blocked.")


def validate_frame_request(request: Request):
    validate_camera_request(request)
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "image/jpeg":
        raise HTTPException(status_code=415, detail="Send an image/jpeg frame.")


async def read_frame(request: Request) -> bytes:
    declared_size = request.headers.get("content-length")
    if declared_size is not None:
        try:
            size = int(declared_size)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid frame size.") from None

        if size < 0:
            raise HTTPException(status_code=400, detail="Invalid frame size.")
        if size > MAX_FRAME_BYTES:
            raise HTTPException(status_code=413, detail="Frame must be smaller than 1 MB.")

    frame = bytearray()
    try:
        async for chunk in request.stream():
            if len(frame) + len(chunk) > MAX_FRAME_BYTES:
                raise HTTPException(status_code=413, detail="Frame must be smaller than 1 MB.")
            frame.extend(chunk)
    except ClientDisconnect:
        raise HTTPException(status_code=400, detail="Frame request was interrupted.") from None

    return bytes(frame)


@router.post("/api/pose", response_model=PoseResult, name="detect_pose")
async def detect_pose(
    request: Request,
    detector: PoseDetector = Depends(get_pose_detector),
):
    validate_frame_request(request)
    frame_bytes = await read_frame(request)

    return await run_frame_analysis(detector.detect, frame_bytes)


async def run_frame_analysis(operation, *arguments):
    """Translate adapter and service failures into safe HTTP responses."""
    try:
        return await run_in_threadpool(operation, *arguments)
    except InvalidFrameError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except ModelUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except PoseBusyError:
        raise HTTPException(
            status_code=429,
            detail="Body detection is busy. Try the next frame.",
            headers={"Retry-After": "1"},
        ) from None
    except PoseDetectionError:
        raise HTTPException(status_code=503, detail="Body detection is temporarily unavailable.") from None
    except InvalidLandmarksError:
        raise HTTPException(status_code=503, detail="Body tracking could not be evaluated. Try again.") from None


@router.post("/api/{exercise_id}/session", response_model=SessionResult, status_code=201)
def create_workout_session(
    request: Request,
    exercise_id: str,
    sessions: WorkoutSessions = Depends(get_workout_sessions),
):
    validate_camera_request(request)
    validate_exercise_id(exercise_id)
    try:
        token, workout = sessions.create(exercise_id)
    except SessionLimitError as error:
        raise HTTPException(status_code=429, detail=str(error)) from None
    return {"session_id": token, "exercise_id": exercise_id, "workout": workout}


def validate_exercise_id(exercise_id):
    if exercise_id not in EXERCISES:
        raise HTTPException(status_code=404, detail="Choose Push Up, Squats, or Lunge.")


def read_session_token(request: Request):
    token = request.headers.get("x-coach-session", "")
    if len(token) != 32 or any(character not in "0123456789abcdef" for character in token):
        raise HTTPException(status_code=404, detail="Camera session ended. Start the camera again.")
    return token


@router.delete("/api/{exercise_id}/session", status_code=204)
def close_workout_session(
    request: Request,
    exercise_id: str,
    sessions: WorkoutSessions = Depends(get_workout_sessions),
):
    validate_camera_request(request)
    validate_exercise_id(exercise_id)
    try:
        sessions.close(read_session_token(request), exercise_id)
    except SessionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@router.post("/api/{exercise_id}/frame", response_model=WorkoutPoseResult)
async def analyze_workout_frame(
    request: Request,
    exercise_id: str,
    detector: PoseDetector = Depends(get_pose_detector),
    sessions: WorkoutSessions = Depends(get_workout_sessions),
):
    validate_frame_request(request)
    validate_exercise_id(exercise_id)
    token = read_session_token(request)
    try:
        session = sessions.get(token, exercise_id)
    except SessionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    frame = await read_frame(request)
    return await run_frame_analysis(session.analyze, detector, frame)


@router.post("/api/{exercise_id}/count-check", response_model=CountCheckResult)
def check_trial_count(request: Request, exercise_id: str, counts: CountCheckInput):
    validate_camera_request(request)
    validate_exercise_id(exercise_id)
    return {"exercise_id": exercise_id, **compare_counts(counts.manual_count, counts.observed_count)}
