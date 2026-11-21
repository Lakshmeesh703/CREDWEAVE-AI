"""Supabase identity verification and application-owned authorization."""
import logging
from dataclasses import dataclass
from os import getenv
from typing import Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.session import SessionLocal
from app.models.entities import Business, BusinessShare, PortalAccount
from app.recovery_store import RecoveryDetails, enroll_recovery

router = APIRouter(prefix="/api")
logger = logging.getLogger("uvicorn.error")
ACCESS = "credweave_access"
REFRESH = "credweave_refresh"


@dataclass(frozen=True)
class Principal:
    id: str
    role: str
    demo: bool = False
    email: str | None = None


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class Login(Credentials):
    role: Literal["owner", "lender", "admin"] = "owner"


class Registration(Credentials):
    account_type: Literal["owner", "lender"] = "owner"
    recovery: RecoveryDetails | None = None


def check_new_password(password: str) -> None:
    if len(password) < 15 or not password.strip():
        raise HTTPException(422, "Use a password with at least 15 characters.")
    try:
        size = len(password.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise HTTPException(422, "Use valid Unicode characters in your password.") from exc
    if size > 72:
        raise HTTPException(422, "Use a password that fits within 72 UTF-8 bytes.")


def supabase(path: str, *, token: str | None = None, payload: dict | None = None) -> dict:
    url = getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    if not url.startswith("https://"):
        raise HTTPException(503, "Set SUPABASE_URL to your HTTPS project URL in .env and restart the API.")
    if not key:
        raise HTTPException(503, "Set SUPABASE_PUBLISHABLE_KEY in .env and restart the API.")
    headers = {"apikey": key}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = httpx.request("GET" if payload is None else "POST", f"{url}/auth/v1/{path}",
                                 headers=headers, json=payload, timeout=8)
        code = response.headers.get("x-sb-error-code")
        if not response.is_success and not code and response.headers.get("content-type", "").startswith("application/json"):
            try:
                error = response.json()
                code = error.get("error_code") if isinstance(error, dict) else None
            except ValueError:
                pass
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            detail = "Too many authentication requests. Wait before trying again."
            if code == "over_email_send_rate_limit":
                detail = "Supabase has limited confirmation emails. Check your inbox or spam for an earlier link and wait before trying again."
            raise HTTPException(429, detail, headers={"Retry-After": retry_after} if retry_after else None)
        if code == "email_address_not_authorized":
            raise HTTPException(403, "This Supabase project cannot send confirmation email to this address. The project owner can enable custom SMTP.")
        if code == "email_not_confirmed":
            raise HTTPException(403, "Confirm your email using the link in your inbox before signing in.")
        if response.status_code >= 500:
            raise HTTPException(503, "Authentication service is temporarily unavailable.")
        if not response.is_success:
            raise HTTPException(401, "Credentials or session could not be verified.")
        return response.json() if response.content else {}
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(503, "Authentication service is temporarily unavailable.") from exc


def portal_account(user_id: str, *, initial_role: Literal["owner", "lender_pending"] = "owner") -> Principal:
    with SessionLocal.begin() as db:
        account = db.get(PortalAccount, user_id)
        if account is None:
            insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
            db.execute(insert(PortalAccount).values(id=user_id, role=initial_role).on_conflict_do_nothing())
            account = db.get(PortalAccount, user_id)
        return Principal(account.id, account.role)


def check_origin(request: Request) -> None:
    if getattr(request.app.state, "synthetic_demo", False):
        raise HTTPException(404, "Sign-in is available in the main portal.")
    allowed = {origin.strip() for origin in getenv("CORS_ORIGINS", "http://localhost:5173").split(",")}
    if request.headers.get("origin") not in allowed:
        raise HTTPException(403, "Request origin is not allowed.")


def session_account(token: str) -> Principal:
    user = supabase("user", token=token)
    try:
        user_id = str(UUID(user["id"]))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(401, "Sign in with a verified account.") from exc
    if user.get("is_anonymous") or not user.get("email_confirmed_at"):
        raise HTTPException(401, "Confirm your email before signing in.")
    account = portal_account(user_id)
    return Principal(account.id, account.role, email=user.get("email"))


def current_user(request: Request) -> Principal:
    if getattr(request.app.state, "synthetic_demo", False):
        return Principal("synthetic-demo", "owner", demo=True)
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    else:
        token = request.cookies.get(ACCESS)
        if token and request.method not in {"GET", "HEAD", "OPTIONS"}:
            check_origin(request)
    if not token:
        raise HTTPException(401, "Sign in to continue.")
    return session_account(token)


def owner(user: Principal = Depends(current_user)) -> Principal:
    if user.role != "owner":
        raise HTTPException(403, "Business Owner access required.")
    return user


def businesses_for(user: Principal):
    query = select(Business)
    if user.demo:
        return query
    if user.role == "owner":
        return query.where(Business.owner_id == user.id)
    if user.role == "lender":
        return query.join(BusinessShare, BusinessShare.business_id == Business.id).where(
            BusinessShare.lender_id == user.id, Business.passport_sharing_consent.is_(True),
        )
    return query.where(False)


def business_access(business_id: str, user: Principal = Depends(current_user)) -> Principal:
    with SessionLocal() as db:
        if db.scalar(businesses_for(user).where(Business.id == business_id)) is None:
            raise HTTPException(404, "Business not found.")
    return user


def owned_business(user: Principal = Depends(business_access)) -> Principal:
    return owner(user)


def session_cookies(response: Response, data: dict) -> None:
    secure = getenv("AUTH_COOKIE_SECURE", "1") != "0"
    response.set_cookie(ACCESS, data["access_token"], max_age=int(data.get("expires_in", 3600)),
                        httponly=True, secure=secure, samesite="strict", path="/api")
    response.set_cookie(REFRESH, data["refresh_token"], max_age=30 * 24 * 3600,
                        httponly=True, secure=secure, samesite="strict", path="/api/auth")


@router.get("/me")
def me(user: Principal = Depends(current_user)) -> dict:
    return {"id": user.id, "role": user.role, "demo": user.demo}


@router.post("/me/lender-access")
def request_lender_access(user: Principal = Depends(current_user)) -> dict:
    if user.demo:
        raise HTTPException(403, "This action is available in the signed-in portal.")
    with SessionLocal.begin() as db:
        account = db.scalar(select(PortalAccount).where(PortalAccount.id == user.id).with_for_update())
        if account is None or account.role not in {"owner", "lender_pending", "lender"}:
            raise HTTPException(403, "This account cannot request lender access.")
        if account.role == "owner":
            if db.scalar(select(Business.id).where(Business.owner_id == user.id).limit(1)):
                raise HTTPException(409, "Use a dedicated lender account for lender access.")
            account.role = "lender_pending"
        return {"id": account.id, "role": account.role, "demo": False}


@router.post("/auth/login")
def login(payload: Login, request: Request, response: Response) -> dict:
    check_origin(request)
    data = supabase("token?grant_type=password", payload={"email": payload.email, "password": payload.password})
    token = data.get("access_token")
    if not token or not data.get("refresh_token"):
        raise HTTPException(503, "Sign-in is temporarily unavailable.")
    try:
        role = session_account(token).role
        login_role = "lender" if role == "lender_pending" else role
        if login_role != payload.role:
            raise HTTPException(409, "Use the sign-in option for your account role.")
    except HTTPException:
        try:
            supabase("logout?scope=local", token=token, payload={})
        except HTTPException:
            logger.warning("Could not revoke a discarded sign-in session.")
        raise
    session_cookies(response, data)
    return {"signed_in": True}


@router.post("/auth/register")
def register(payload: Registration, request: Request, response: Response) -> dict:
    check_origin(request)
    check_new_password(payload.password)
    email_confirmation_required = supabase("settings").get("mailer_autoconfirm") is not True
    data = supabase("signup", payload={"email": payload.email, "password": payload.password})
    user = data.get("user") if isinstance(data.get("user"), dict) else data
    if email_confirmation_required and not user.get("identities"):
        # Supabase may obfuscate the response for an already registered address.
        return {"signed_in": False, "confirmation_required": True}
    if not email_confirmation_required and (not data.get("access_token") or not data.get("refresh_token")):
        logger.warning("Supabase signup returned no session. Check the project's sign-up settings.")
        raise HTTPException(503, "Account registration is temporarily unavailable.")
    try:
        user_id = str(UUID(user["id"]))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(503, "Account registration is temporarily unavailable.") from exc
    account = portal_account(user_id, initial_role="lender_pending" if payload.account_type == "lender" else "owner")
    if email_confirmation_required:
        return {"signed_in": False, "confirmation_required": True}
    result: dict[str, str | bool] = {"signed_in": True}
    if payload.recovery is not None:
        code = enroll_recovery(account.id, payload.recovery)
        if code is not None:
            result["recovery_code"] = code
    session_cookies(response, data)
    return result


@router.post("/auth/refresh")
def refresh(request: Request, response: Response) -> dict:
    check_origin(request)
    token = request.cookies.get(REFRESH)
    if not token:
        raise HTTPException(401, "Sign in to continue.")
    session_cookies(response, supabase("token?grant_type=refresh_token", payload={"refresh_token": token}))
    return {"signed_in": True}


@router.post("/auth/logout")
def logout(request: Request, response: Response) -> dict:
    check_origin(request)
    token = request.cookies.get(ACCESS)
    refresh_token = request.cookies.get(REFRESH)
    try:
        if not token and refresh_token:
            token = supabase("token?grant_type=refresh_token", payload={"refresh_token": refresh_token})["access_token"]
        if token:
            supabase("logout?scope=local", token=token, payload={})
    except HTTPException:
        # Clear browser credentials even if the provider session already expired.
        pass
    response.delete_cookie(ACCESS, path="/api")
    response.delete_cookie(REFRESH, path="/api/auth")
    return {"signed_in": False}
