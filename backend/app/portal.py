"""Serve the production React portal alongside the FastAPI API."""

from app.main import app
from app.portal_routes import mount_portal


mount_portal(app)
