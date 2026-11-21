"""Mount the built React portal on an existing FastAPI application."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def mount_portal(app: FastAPI) -> None:
    if getattr(app.state, "portal_mounted", False):
        return

    frontend = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    index = frontend / "index.html"
    if not index.is_file():
        raise RuntimeError("Build the frontend with VITE_API_BASE_URL='' npm --prefix frontend run build.")

    app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="portal-assets")

    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def serve_frontend(path: str = "") -> FileResponse:
        # Let React Router resolve page links while returning 404 for missing API routes and files.
        if path.split("/", 1)[0] in {"api", "assets"} or "." in Path(path).name:
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    app.state.portal_mounted = True
