from sqlalchemy.orm import Session

from app.models.video import Video


def get_videos_for_recommendation(
    db: Session,
    niche: str,
    subscriber_min: int,
    subscriber_max: int,
    min_engagement_score: float,
    min_video_comment_count: int,
    only_active_creators: bool,
    max_results: int,
) -> list[Video]:
    query = db.query(Video)

    query = query.filter(Video.niche == niche)
    query = query.filter(Video.subscriber_count >= subscriber_min)
    query = query.filter(Video.subscriber_count <= subscriber_max)
    query = query.filter(Video.engagement_score >= min_engagement_score)
    query = query.filter(Video.comment_count >= min_video_comment_count)

    if only_active_creators:
        query = query.filter(Video.creator_reply_ratio > 0)

  
    query = query.order_by(
        Video.creator_reply_ratio.desc(),
        Video.engagement_score.desc(),
        Video.comment_count.desc(),
        Video.days_since_upload.asc(),
    )

    return query.limit(max_results).all()