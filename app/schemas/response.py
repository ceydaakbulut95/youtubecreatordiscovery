from pydantic import BaseModel
from app.schemas.video import VideoCandidate


class VideoRecommendation(BaseModel):
    interaction_id: int
    video: VideoCandidate
    suggested_comments: list[str]


class RecommendationResponse(BaseModel):
    total_results: int
    results: list[VideoRecommendation]