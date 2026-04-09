from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.db.database import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)

    youtube_video_id = Column(String, unique=True, nullable=False, index=True)
    youtube_channel_id = Column(String, nullable=False, index=True)

    channel_name = Column(String, nullable=False)
    subscriber_count = Column(Integer, default=0, nullable=False)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    video_url = Column(String, nullable=False)

    niche = Column(String, nullable=False, index=True)

    published_at = Column(DateTime, nullable=True)
    days_since_upload = Column(Integer, default=0, nullable=False)

    comment_count = Column(Integer, default=0, nullable=False)
    creator_reply_ratio = Column(Float, default=0.0, nullable=False)
    engagement_score = Column(Float, default=0.0, nullable=False)

    is_short = Column(Boolean, default=False, nullable=False)
    has_description = Column(Boolean, default=True, nullable=False)

    last_fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)