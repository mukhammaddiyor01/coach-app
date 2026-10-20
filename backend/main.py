"""Create the application and connect its routes and static files."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.routes import router

PROJECT_ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(title="Coach App")
app.mount(
    "/static",
    StaticFiles(directory=PROJECT_ROOT / "frontend" / "static"),
    name="static",
)
app.include_router(router)
