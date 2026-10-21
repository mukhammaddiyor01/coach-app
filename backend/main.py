"""Create the application and connect its routes and static files."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.routes import router
from backend.security import PublicStaticFiles, add_security_headers
from backend.vision.pose_detector import pose_detector
from backend.workout_sessions import workout_sessions

PROJECT_ROOT = Path(__file__).resolve().parent.parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        workout_sessions.clear()
        await run_in_threadpool(pose_detector.close)


app = FastAPI(
    lifespan=lifespan,
    title="Coach App",
    debug=False,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["127.0.0.1", "localhost"],
    www_redirect=False,
)
app.middleware("http")(add_security_headers)
app.mount(
    "/static",
    PublicStaticFiles(directory=PROJECT_ROOT / "frontend" / "static"),
    name="static",
)
app.include_router(router)
