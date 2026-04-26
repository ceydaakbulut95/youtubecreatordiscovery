from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from app.db.database import Base


class VideoCommentCache(Base):
    __tablename__ = "video_comment_cache"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True)
    youtube_video_id = Column(String, nullable=False, index=True)

    comment_1 = Column(String, nullable=False)
    comment_2 = Column(String, nullable=True)
    comment_3 = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)