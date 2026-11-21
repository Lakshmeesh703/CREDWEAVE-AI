"""Owner-managed consent for individual verified lender accounts."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.auth import Principal, owned_business
from app.db.session import SessionLocal
from app.models.entities import Business, BusinessShare, PortalAccount

router = APIRouter(prefix="/api/businesses/{business_id}/shares")


def _grants(db, business_id: str):
    return select(BusinessShare).where(BusinessShare.business_id == business_id)


def _owned_portal_business(db, business_id: str, user: Principal, *, lock: bool = False) -> Business:
    if user.demo:
        raise HTTPException(403, "Lender grants are available in the signed-in portal.")
    statement = select(Business).where(Business.id == business_id, Business.owner_id == user.id)
    business = db.scalar(statement.with_for_update() if lock else statement)
    if business is None:
        raise HTTPException(404, "Business not found.")
    return business


@router.get("")
def list_shares(business_id: str, user: Principal = Depends(owned_business)) -> list[dict]:
    with SessionLocal() as db:
        _owned_portal_business(db, business_id, user)
        return [{"lender_id": grant.lender_id, "granted_at": grant.granted_at.isoformat()}
                for grant in db.scalars(_grants(db, business_id).order_by(BusinessShare.granted_at))]


@router.put("/{lender_id}")
def grant_share(business_id: str, lender_id: UUID, user: Principal = Depends(owned_business)) -> dict:
    lender_id = str(lender_id)
    with SessionLocal.begin() as db:
        lender = db.scalar(select(PortalAccount).where(PortalAccount.id == lender_id).with_for_update())
        if lender is None or lender.role != "lender":
            raise HTTPException(404, "Lender account not found. Confirm the account ID with your lender.")
        business = _owned_portal_business(db, business_id, user, lock=True)
        if db.get(BusinessShare, (business_id, lender_id)) is None:
            db.add(BusinessShare(business_id=business_id, lender_id=lender_id))
        business.passport_sharing_consent = True
    return {"lender_id": lender_id}


@router.delete("/{lender_id}")
def revoke_share(business_id: str, lender_id: UUID, user: Principal = Depends(owned_business)) -> dict:
    lender_id = str(lender_id)
    with SessionLocal.begin() as db:
        business = _owned_portal_business(db, business_id, user, lock=True)
        grant = db.get(BusinessShare, (business_id, lender_id))
        if grant is not None:
            db.delete(grant)
            db.flush()
        business.passport_sharing_consent = db.scalar(_grants(db, business_id).limit(1)) is not None
    return {"lender_id": lender_id}
