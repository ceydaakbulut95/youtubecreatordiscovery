from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)

    role = Column(String, default="user", nullable=False)

    plan_type = Column(String, default="free", nullable=False)
    subscription_status = Column(String, default="inactive", nullable=False)
    payment_status = Column(String, default="unpaid", nullable=False)
    free_search_count = Column(Integer, default=0, nullable=False)

    stripe_customer_id = Column(String, nullable=True)
    stripe_checkout_session_id = Column(String, nullable=True)

    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)