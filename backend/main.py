"""Create the application and connect its routes and static files."""
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.routes import router
from backend.security import PublicStaticFiles, add_security_headers

PROJECT_ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(
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
