from pydantic import BaseModel, Field


class VideoSearchRequest(BaseModel):
    niche: str = Field(..., min_length=2)
    subscriber_min: int = Field(default=0, ge=0)
    subscriber_max: int = Field(default=1_000_000_000, ge=0)
    min_engagement_score: float = Field(default=0.0, ge=0.0, le=1.0)
    min_video_comment_count: int = Field(default=0, ge=0)
    only_active_creators: bool = Field(default=False)
    max_results: int = Field(default=10, ge=1, le=50)