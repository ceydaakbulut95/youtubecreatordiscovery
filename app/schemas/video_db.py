from datetime import datetime
from pydantic import BaseModel


class VideoDBResponse(BaseModel):
    id: int
    youtube_video_id: str
    youtube_channel_id: str
    channel_name: str
    subscriber_count: int
    title: str
    description: str
    video_url: str
    niche: str
    published_at: datetime | None
    days_since_upload: int
    comment_count: int
    creator_reply_ratio: float
    engagement_score: float
    is_short: bool
    has_description: bool

    model_config = {
        "from_attributes": True
    }