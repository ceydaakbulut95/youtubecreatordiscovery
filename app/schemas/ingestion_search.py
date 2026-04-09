from pydantic import BaseModel, Field


class IngestionSearchRequest(BaseModel):
    keyword: str = Field(..., min_length=2)
    niche: str = Field(..., min_length=2)
    subscriber_min: int = Field(default=0, ge=0)
    subscriber_max: int = Field(default=1_000_000_000, ge=0)
    only_active_creators: bool = False
    min_engagement_score: float = Field(default=0.0, ge=0.0, le=1.0)
    min_video_comment_count: int = Field(default=0, ge=0)
    published_after_days: int = Field(default=90, ge=1, le=3650)
    search_pages: int = Field(default=1, ge=1, le=10)
    max_results: int = Field(default=20, ge=1, le=50)