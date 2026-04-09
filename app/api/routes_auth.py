from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.user import (
    TokenResponse,
    UpgradeResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import (
    create_access_token,
    get_user_by_email,
    hash_password,
    normalize_email,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    normalized_email = normalize_email(request.email)

    existing = get_user_by_email(db, normalized_email)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="This email is already registered"
        )

    user = User(
        email=normalized_email,
        password_hash=hash_password(request.password),
        plan_type="free",
        subscription_status="inactive",
        payment_status="unpaid",
        free_search_count=0,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.email)

    return TokenResponse(
        access_token=token,
        user=user,
    )


@router.post("/login", response_model=TokenResponse)
def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    normalized_email = normalize_email(request.email)

    user = get_user_by_email(db, normalized_email)
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user.id, user.email)

    return TokenResponse(
        access_token=token,
        user=user,
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/upgrade", response_model=UpgradeResponse)
def upgrade_to_premium(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.plan_type = "paid"
    current_user.subscription_status = "active"
    current_user.payment_status = "paid"
    db.commit()
    db.refresh(current_user)

    return UpgradeResponse(
        message="Paid access activated",
        plan_type=current_user.plan_type,
        subscription_status=current_user.subscription_status,
    )