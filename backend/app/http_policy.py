"""Keep portal responses private and bound multipart bodies before parsing."""
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.intake import MAX_FILE_BYTES


class PortalHttpPolicy:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            await self.app(scope, receive, send)
            return

        async def send_private(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)["Cache-Control"] = "no-store"
            await send(message)

        path = scope["path"]
        if scope["method"] == "POST" and path.startswith("/api/businesses/") and "/imports/" in path:
            length = Headers(scope=scope).get("content-length", "")
            if not length.isascii() or not length.isdecimal():
                response = JSONResponse({"detail": "The upload must include its content length."}, status_code=411)
                await response(scope, receive, send_private)
                return
            if len(length) > 8 or int(length) > MAX_FILE_BYTES + 16 * 1024:
                response = JSONResponse({"detail": "File exceeds the 2 MB import limit."}, status_code=413)
                await response(scope, receive, send_private)
                return
        await self.app(scope, receive, send_private)
