"""Serve the built UI and the live API for the local synthetic presentation."""

from os import environ
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.assessment import create_assessment
from app.main import app
from app.db.session import SessionLocal, database_url
from app.models import Business
from app.seed import seed


frontend = Path(environ["CREDWEAVE_JURY_FRONTEND"])
index = frontend / "index.html"
if not index.is_file() or database_url() != f"sqlite:///{frontend.parent / 'demo.sqlite3'}":
    raise RuntimeError("Start the isolated presentation with scripts/run-jury-demo.sh.")

app.state.synthetic_demo = True
app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="jury-assets")


@app.on_event("startup")
def prepare_jury_cases() -> None:
    seed(simulate_gateway=True)
    with SessionLocal() as db:
        business_ids = db.scalars(select(Business.id)).all()
    for business_id in business_ids:
        create_assessment(business_id)


@app.get("/", include_in_schema=False)
def jury_home() -> RedirectResponse:
    return RedirectResponse("/demo")


@app.get("/demo", include_in_schema=False)
@app.get("/demo/{path:path}", include_in_schema=False)
def serve_frontend(path: str = "") -> FileResponse:
    # BrowserRouter handles direct links to stages. Unknown API or asset URLs
    # should still return a 404 instead of the HTML entry point.
    if path.split("/", 1)[0] in {"api", "assets"} or "." in Path(path).name:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(index)
