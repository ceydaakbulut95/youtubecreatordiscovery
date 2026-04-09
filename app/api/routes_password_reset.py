from fastapi import APIRouter, Depends, HTTPException
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

router = APIRouter(prefix="/password", tags=["Password Reset"])


@router.post("/forgot", response_model=ForgotPasswordResponse)
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user, reset_token = create_password_reset_token(db, request.email)

    if not user or not reset_token:
        return ForgotPasswordResponse(
            message="If this email exists, a password reset link has been created."
        )

    reset_link = f"http://127.0.0.1:5500/?reset_token={reset_token.token}"

    return ForgotPasswordResponse(
        message="Password reset link created.",
        reset_token=reset_token.token,
        reset_link=reset_link,
    )


@router.post("/reset", response_model=ResetPasswordResponse)
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    success = reset_user_password(db, request.token, request.new_password)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    return ResetPasswordResponse(
        message="Password reset successful"
    )