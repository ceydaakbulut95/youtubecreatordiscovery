from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.video import Video
from app.schemas.video_db import VideoDBResponse

router = APIRouter(prefix="/db/videos", tags=["DB Videos"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=list[VideoDBResponse])
def list_videos(
    niche: str | None = None,
    subscriber_min: int = Query(default=0, ge=0),
    subscriber_max: int = Query(default=1_000_000_000, ge=0),
    min_comment_count: int = Query(default=0, ge=0),
    min_engagement_score: float = Query(default=0.0, ge=0.0, le=1.0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Video)

    if niche:
        query = query.filter(Video.niche == niche)

    query = query.filter(Video.subscriber_count >= subscriber_min)
    query = query.filter(Video.subscriber_count <= subscriber_max)
    query = query.filter(Video.comment_count >= min_comment_count)
    query = query.filter(Video.engagement_score >= min_engagement_score)

    return (
        query.order_by(Video.engagement_score.desc())
        .limit(limit)
        .all()
    )