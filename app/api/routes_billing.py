from decimal import Decimal

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.billing import CheckoutSessionResponse

stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter(prefix="/billing", tags=["Billing"])


def eur_to_cents(value: str) -> int:
    return int(Decimal(value) * 100)


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
def create_checkout_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    is_paid = current_user.plan_type in {"paid", "premium"} and current_user.payment_status == "paid"
    if is_paid:
        raise HTTPException(status_code=400, detail="User already has paid access")

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            customer_email=current_user.email,
            line_items=[
                {
                    "price_data": {
                        "currency": "eur",
                        "product_data": {
                            "name": "YouTube Creator Discovery Assistant - Full Access",
                        },
                        "unit_amount": eur_to_cents(settings.PAYMENT_PRICE_EUR),
                    },
                    "quantity": 1,
                }
            ],
            success_url=f"{settings.FRONTEND_URL}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/?payment=cancelled",
            metadata={
                "user_id": str(current_user.id),
            },
        )

        current_user.stripe_checkout_session_id = session.id
        db.commit()
        db.refresh(current_user)

        return CheckoutSessionResponse(checkout_url=session.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe checkout creation failed: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    if event["type"] == "checkout.session.completed":
        session_obj = event["data"]["object"]
        user_id = session_obj.get("metadata", {}).get("user_id")

        if user_id:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                user.plan_type = "paid"
                user.payment_status = "paid"
                user.subscription_status = "active"
                user.stripe_checkout_session_id = session_obj.get("id")
                db.commit()

    return {"received": True}