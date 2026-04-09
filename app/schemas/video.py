from pydantic import BaseModel, Field


class VideoCandidate(BaseModel):
    video_id: str
    title: str
    description: str
    video_url: str
    channel_id: str
    channel_name: str
    subscriber_count: int = Field(..., ge=0)
    creator_reply_ratio: float = Field(..., ge=0.0, le=1.0)
    engagement_score: float = Field(..., ge=0.0, le=1.0)
    comment_count: int = Field(..., ge=0)
    days_since_upload: int = Field(..., ge=0)
    niche: str