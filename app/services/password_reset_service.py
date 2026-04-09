from datetime import datetime, timedelta
import secrets

from sqlalchemy.orm import Session

from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services.auth_service import get_user_by_email, hash_password


RESET_TOKEN_EXPIRE_MINUTES = 30


def create_password_reset_token(db: Session, email: str) -> tuple[User | None, PasswordResetToken | None]:
    user = get_user_by_email(db, email)
    if not user:
        return None, None

    token_value = secrets.token_urlsafe(32)

    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token_value,
        is_used=False,
        expires_at=datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
    )

    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)

    return user, reset_token


def reset_user_password(db: Session, token: str, new_password: str) -> bool:
    reset_token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token == token)
        .first()
    )

    if not reset_token:
        return False

    if reset_token.is_used:
        return False

    if reset_token.expires_at < datetime.utcnow():
        return False

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        return False

    user.password_hash = hash_password(new_password)
    reset_token.is_used = True

    db.commit()
    return True