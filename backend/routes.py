"""Page controllers: validate the exercise and render its HTML template."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.exercises import EXERCISES

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
