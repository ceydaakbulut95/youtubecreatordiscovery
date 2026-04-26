from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.password_reset import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.services.password_reset_service import (
    create_password_reset_token,
    reset_user_password,
)
from app.services.email_service import send_password_reset_email
from app.core.config import settings
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from app.core.limiter import limiter

router = APIRouter(prefix="/password", tags=["Password Reset"])


@router.post("/forgot", response_model=ForgotPasswordResponse)
@limiter.limit("5/minute")
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user, reset_token = create_password_reset_token(db, payload.email)

    if not user or not reset_token:
        return ForgotPasswordResponse(
            message="If this email exists, a password reset email has been sent."
        )

    reset_link = f"{settings.FRONTEND_URL}/?reset_token={reset_token.token}"

    background_tasks.add_task(
        send_password_reset_email,
        user.email,
        reset_link,
    )

    return ForgotPasswordResponse(
        message="If this email exists, a password reset email has been sent."
    )

@router.post("/reset", response_model=ResetPasswordResponse)
@limiter.limit("10/minute")
def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    success = reset_user_password(db, payload.token, payload.new_password)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    return ResetPasswordResponse(message="Password reset successful")