from os import getenv

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from app.auth import router as auth_router
from app.password_recovery import router as password_recovery_router
from app.admin import router as admin_router
from app.db.session import init_db
from app.intake import router as intake_router
from app.http_policy import PortalHttpPolicy
from app.evidence import router as evidence_router
from app.verified_evidence import router as gateway_router
from app.trust_graph import router as trust_graph_router
from app.financial import router as financial_router
from app.assessment import router as assessment_router
from app.stress_tests import router as stress_tests_router
from app.loan_options import router as loan_options_router
from app.credit_passport import router as credit_passport_router
from app.review import router as review_router
from app.sharing import router as sharing_router


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    synthetic_demo: bool


def _cors_origins() -> list[str]:
    configured = getenv("CORS_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app = FastAPI(
    title="CREDWEAVE AI API",
    version="0.1.0",
    description="Credit evidence and decision support for human lender review.",
)

app.add_middleware(PortalHttpPolicy)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)
app.include_router(auth_router)
app.include_router(password_recovery_router)
app.include_router(admin_router)
app.include_router(intake_router)
app.include_router(evidence_router)
app.include_router(gateway_router)
app.include_router(trust_graph_router)
app.include_router(financial_router)
app.include_router(assessment_router)
app.include_router(stress_tests_router)
app.include_router(loan_options_router)
app.include_router(credit_passport_router)
app.include_router(review_router)
app.include_router(sharing_router)


@app.on_event("startup")
def prepare_database() -> None:
    init_db()


@app.get("/api/health", response_model=HealthResponse)
def health(request: Request, response: Response) -> HealthResponse:
    demo = getattr(request.app.state, "synthetic_demo", False)
    response.headers["X-CredWeave-Mode"] = "jury" if demo else "portal"
    return HealthResponse(
        status="ok",
        service="credweave-ai-api",
        version=app.version,
        synthetic_demo=demo,
    )


@app.exception_handler(RequestValidationError)
async def invalid_request(_request: Request, exc: RequestValidationError) -> JSONResponse:
    # Validation errors must not echo credentials or financial records from the request.
    messages = [f"{'.'.join(str(part) for part in err['loc'][1:])}: {err['msg']}" for err in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": " ".join(messages)})


@app.exception_handler(IntegrityError)
async def conflicting_record(_request: Request, _exc: IntegrityError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": "The request conflicts with an existing record. No changes were applied."})
