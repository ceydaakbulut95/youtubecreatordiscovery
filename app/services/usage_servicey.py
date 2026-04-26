from fastapi import HTTPException
from app.core.config import settings
from app.models.user import User


def is_admin_user(user: User) -> bool:
    return getattr(user, "role", "user") == "admin"


def is_paid_user(user: User) -> bool:
    return (
        user.plan_type in {"paid", "premium"}
        and user.payment_status == "paid"
    )


def has_full_access(user: User) -> bool:
    return is_admin_user(user) or is_paid_user(user)


def can_use_search(user: User) -> bool:
    if has_full_access(user):
        return True

    return user.free_search_count < settings.FREE_SEARCH_LIMIT


def enforce_search_limit(user: User):
    if not can_use_search(user):
        raise HTTPException(
            status_code=402,
            detail={
                "message": f"You used your {settings.FREE_SEARCH_LIMIT} free searches. Unlock full access for a one-time payment of €{settings.PAYMENT_PRICE_EUR}.",
                "requires_payment": True,
                "price_eur": settings.PAYMENT_PRICE_EUR,
            },
        )


def increment_search_count(db, user: User):
    if has_full_access(user):
        return

    user.free_search_count += 1
    db.commit()
    db.refresh(user)