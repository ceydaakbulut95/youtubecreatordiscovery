from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.db.database import Base


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)

    video_id = Column(Integer, nullable=True, index=True)
    youtube_video_id = Column(String, nullable=False, index=True)
    youtube_channel_id = Column(String, nullable=False, index=True)

    suggested_comment = Column(Text, nullable=False)

    copied = Column(Boolean, default=False, nullable=False)
    opened = Column(Boolean, default=False, nullable=False)
    selected = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)