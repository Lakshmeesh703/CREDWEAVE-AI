"""Portal role administration without access to business evidence."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, select

from app.auth import Principal, current_user
from app.db.session import SessionLocal
from app.models.entities import Business, BusinessShare, PortalAccount

router = APIRouter(prefix="/api/admin")


class RoleChange(BaseModel):
    role: Literal["owner", "lender"]


def admin(user: Principal = Depends(current_user)) -> Principal:
    if user.demo or user.role != "admin":
        raise HTTPException(403, "Admin access is required.")
    return user


@router.get("/accounts", dependencies=[Depends(admin)])
def accounts(after: UUID | None = None, limit: int = Query(25, ge=1, le=100)) -> dict:
    query = select(PortalAccount).order_by(PortalAccount.id).limit(limit + 1)
    if after is not None:
        query = query.where(PortalAccount.id > str(after))
    with SessionLocal() as db:
        rows = db.scalars(query).all()
        return {
            "items": [{"id": account.id, "role": account.role} for account in rows[:limit]],
            "next_after": rows[limit - 1].id if len(rows) > limit else None,
        }


@router.put("/accounts/{account_id}/role", dependencies=[Depends(admin)])
def change_role(account_id: UUID, payload: RoleChange) -> dict:
    with SessionLocal.begin() as db:
        account = db.scalar(select(PortalAccount).where(PortalAccount.id == str(account_id)).with_for_update())
        if account is None:
            raise HTTPException(404, "Account not found. The user must sign in first.")
        if account.role == "admin":
            raise HTTPException(403, "Administrator accounts are managed outside the portal.")
        if account.role == payload.role:
            return {"id": account.id, "role": account.role}
        if payload.role == "lender":
            if db.scalar(select(Business.id).where(Business.owner_id == account.id).limit(1)):
                raise HTTPException(409, "This account owns a business. Use a dedicated lender account.")
        else:
            # A later promotion must not silently restore any former lender grants.
            affected = select(BusinessShare.business_id).where(BusinessShare.lender_id == account.id)
            businesses = db.scalars(select(Business).where(Business.id.in_(affected))
                                    .order_by(Business.id).with_for_update()).all()
            db.execute(delete(BusinessShare).where(BusinessShare.lender_id == account.id))
            for business in businesses:
                business.passport_sharing_consent = db.scalar(
                    select(BusinessShare.lender_id).where(BusinessShare.business_id == business.id).limit(1)
                ) is not None
        account.role = payload.role
        return {"id": account.id, "role": account.role}
