from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.db.database import Base


class SearchSeed(Base):
    __tablename__ = "search_seeds"

    id = Column(Integer, primary_key=True, index=True)

    niche = Column(String, nullable=False, index=True)
    keyword = Column(String, nullable=False, unique=True, index=True)

    is_active = Column(Boolean, default=True, nullable=False)

    last_fetched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)