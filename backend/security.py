"""HTTP protections and the public asset boundary, separate from exercise rules."""
from pathlib import PurePosixPath

from fastapi import HTTPException, Request
from fastapi.staticfiles import StaticFiles

CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "media-src 'self' blob:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
])

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "Permissions-Policy": "camera=(self), microphone=(), geolocation=()",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Resource-Policy": "same-origin",
}

PUBLIC_ASSET_EXTENSIONS = {
    ".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif", ".ico",
    ".woff", ".woff2",
}


def is_public_asset(path: str) -> bool:
    asset_path = PurePosixPath(path)

    if any(part.startswith(".") for part in asset_path.parts):
        return False

    return asset_path.suffix.lower() in PUBLIC_ASSET_EXTENSIONS


class PublicStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        # A misplaced credential, recording, or database is never a public asset.
        if not is_public_asset(path):
            raise HTTPException(status_code=404)

        return await super().get_response(path, scope)


async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    for name, value in SECURITY_HEADERS.items():
        response.headers[name] = value

    return response
