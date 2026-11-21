"""No-email password recovery for Business Owner and Lender accounts."""

from math import ceil
from os import getenv
from secrets import compare_digest
from time import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app import auth
from app.auth import Principal, check_origin, current_user
from app.db.session import SessionLocal
from app.models.entities import PasswordRecovery, PortalAccount
from app.recovery_store import RECOVERABLE_ROLES, RecoveryDetails, enroll_recovery, hash_answer, hash_code, rotate_code

router = APIRouter(prefix="/api/auth/recovery")


class RecoveryCode(BaseModel):
    code: str = Field(pattern=r"^\s*[A-Za-z0-9_-]{32}\s*$", max_length=40)


class ResetPassword(RecoveryCode):
    answer: str = Field(min_length=8, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class RecoveryEnrollment(BaseModel):
    recovery: RecoveryDetails
    password: str = Field(min_length=1, max_length=256)


def unavailable() -> HTTPException:
    return HTTPException(503, "Password recovery is temporarily unavailable.")


def invalid_details() -> HTTPException:
    return HTTPException(403, "Check your recovery code and security answer.")


def update_password(account_id: str, password: str) -> None:
    url = getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = getenv("SUPABASE_SECRET_KEY", "").strip()
    if not url.startswith("https://") or not key.startswith("sb_secret_"):
        raise unavailable()
    try:
        result = httpx.put(f"{url}/auth/v1/admin/users/{account_id}", headers={"apikey": key},
                           json={"password": password}, timeout=8)
    except httpx.HTTPError as exc:
        raise unavailable() from exc
    if result.status_code in {400, 422}:
        raise HTTPException(422, "Choose a different password and try again.")
    if not result.is_success:
        raise unavailable()


@router.post("/setup")
def configure_recovery(payload: RecoveryEnrollment, user: Principal = Depends(current_user)) -> dict:
    if user.demo or user.role not in RECOVERABLE_ROLES or not user.email:
        raise HTTPException(403, "Password recovery is unavailable for this account.")
    # Ask for the current password before replacing a saved recovery code.
    login = auth.supabase("token?grant_type=password", payload={"email": user.email, "password": payload.password})
    if not isinstance(login.get("user"), dict) or login["user"].get("id") != user.id:
        raise HTTPException(403, "Could not verify your current password.")
    # The reauthentication session is used only to verify this request.
    if login.get("access_token"):
        auth.supabase("logout?scope=local", token=login["access_token"], payload={})
    code = enroll_recovery(user.id, payload.recovery)
    if code is None:
        raise HTTPException(403, "Password recovery is unavailable for this account.")
    return {"recovery_code": code}


@router.post("/question")
def recovery_question(payload: RecoveryCode, request: Request) -> dict:
    check_origin(request)
    with SessionLocal() as db:
        question = db.scalar(select(PasswordRecovery.question).join(PortalAccount)
                             .where(PasswordRecovery.code_hash == hash_code(payload.code),
                                    PortalAccount.role.in_(RECOVERABLE_ROLES)))
    if question is None:
        raise invalid_details()
    return {"question": question}


@router.post("/reset")
def reset_password(payload: ResetPassword, request: Request) -> dict:
    check_origin(request)
    auth.check_new_password(payload.password)
    digest = hash_code(payload.code)
    retry_after = 0
    with SessionLocal.begin() as db:
        account_id = db.scalar(select(PasswordRecovery.account_id).where(PasswordRecovery.code_hash == digest))
        if account_id is None:
            raise invalid_details()
        role = db.scalar(select(PortalAccount.role).where(PortalAccount.id == account_id).with_for_update())
        record = db.get(PasswordRecovery, account_id)
        if role not in RECOVERABLE_ROLES or record is None or record.code_hash != digest:
            raise invalid_details()
        now = time()
        if record.blocked_until > now:
            retry_after = ceil(record.blocked_until - now)
        elif compare_digest(record.answer_hash, hash_answer(payload.answer, record.answer_salt)):
            update_password(account_id, payload.password)
            return {"recovery_code": rotate_code(record)}
        else:
            record.failed_attempts += 1
            if record.failed_attempts >= 5:
                retry_after = 900
                record.blocked_until = ceil(now) + retry_after
                record.failed_attempts = 0
    if retry_after:
        raise HTTPException(429, "Too many attempts. Please wait before trying again.",
                            headers={"Retry-After": str(retry_after)})
    raise invalid_details()
