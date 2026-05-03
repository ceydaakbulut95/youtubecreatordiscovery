from datetime import datetime, timedelta
import secrets

from sqlalchemy.orm import Session

from app.models.email_verification_token import EmailVerificationToken
from app.models.user import User
from app.services.auth_service import get_user_by_email


EMAIL_VERIFICATION_EXPIRE_HOURS = 24


def create_email_verification_token(db: Session, email: str) -> tuple[User | None, EmailVerificationToken | None]:
    user = get_user_by_email(db, email)
    if not user:
        return None, None

    active_tokens = (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.user_id == user.id)
        .filter(EmailVerificationToken.is_used == False)
        .all()
    )

    for token in active_tokens:
        token.is_used = True

    token_value = secrets.token_urlsafe(32)

    verification_token = EmailVerificationToken(
        user_id=user.id,
        token=token_value,
        is_used=False,
        expires_at=datetime.utcnow() + timedelta(hours=EMAIL_VERIFICATION_EXPIRE_HOURS),
    )

    db.add(verification_token)
    db.commit()
    db.refresh(verification_token)

    return user, verification_token


def verify_user_email(db: Session, token: str) -> bool:
    verification_token = (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.token == token)
        .first()
    )

    if not verification_token:
        return False

    if verification_token.is_used:
        return False

    if verification_token.expires_at < datetime.utcnow():
        return False

    user = db.query(User).filter(User.id == verification_token.user_id).first()
    if not user:
        return False

    user.is_email_verified = True
    verification_token.is_used = True

    other_tokens = (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.user_id == user.id)
        .filter(EmailVerificationToken.is_used == False)
        .all()
    )

    for other in other_tokens:
        other.is_used = True

    db.commit()
    return True