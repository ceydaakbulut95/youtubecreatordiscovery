from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.limiter import limiter
from app.schemas.email_verification import (
    VerifyEmailRequest,
    VerifyEmailResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
)
from app.services.email_service import send_email_verification_email
from app.services.email_verification_service import (
    create_email_verification_token,
    verify_user_email,
)

router = APIRouter(prefix="/email-verification", tags=["Email Verification"])


@router.post("/verify", response_model=VerifyEmailResponse)
@limiter.limit("10/minute")
def verify_email(
    request: Request,
    payload: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    success = verify_user_email(db, payload.token)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    return VerifyEmailResponse(message="Email verified successfully")


@router.post("/resend", response_model=ResendVerificationResponse)
@limiter.limit("5/minute")
def resend_verification(
    request: Request,
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user, verification_token = create_email_verification_token(db, payload.email)

    if not user or not verification_token:
        return ResendVerificationResponse(
            message="If this email exists, a verification email has been sent."
        )

    verification_link = f"{settings.FRONTEND_URL}/?verify_token={verification_token.token}"

    background_tasks.add_task(
        send_email_verification_email,
        user.email,
        verification_link,
    )

    return ResendVerificationResponse(
        message="If this email exists, a verification email has been sent."
    )