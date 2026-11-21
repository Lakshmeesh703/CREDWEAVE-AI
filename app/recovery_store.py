"""Account-bound recovery codes and private answers."""

from hashlib import scrypt, sha256
from secrets import token_bytes, token_urlsafe

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import PasswordRecovery, PortalAccount

RECOVERABLE_ROLES = ("owner", "lender_pending", "lender")

class RecoveryDetails(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=8, max_length=160)
    answer: str = Field(min_length=8, max_length=128)


def hash_code(code: str) -> str:
    return sha256(code.strip().encode()).hexdigest()


def hash_answer(answer: str, salt: str) -> str:
    return scrypt(answer.strip().encode(), salt=bytes.fromhex(salt), n=2**15, r=8, p=1,
                  maxmem=64 * 1024 * 1024, dklen=32).hex()


def rotate_code(record: PasswordRecovery) -> str:
    code = token_urlsafe(24)
    record.code_hash = hash_code(code)
    record.failed_attempts = 0
    record.blocked_until = 0
    return code


def enroll_recovery(account_id: str, details: RecoveryDetails) -> str | None:
    salt = token_bytes(16).hex()
    answer = hash_answer(details.answer, salt)
    with SessionLocal.begin() as db:
        role = db.scalar(select(PortalAccount.role).where(PortalAccount.id == account_id).with_for_update())
        if role not in RECOVERABLE_ROLES:
            return None
        record = db.get(PasswordRecovery, account_id)
        if record is None:
            record = PasswordRecovery(account_id=account_id)
            db.add(record)
        record.question = details.question
        record.answer_salt = salt
        record.answer_hash = answer
        return rotate_code(record)
