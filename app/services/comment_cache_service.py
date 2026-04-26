from sqlalchemy.orm import Session

from app.models.video_comment_cache import VideoCommentCache
from app.schemas.video import VideoCandidate
from app.services.ai_comment_service import generate_comments


def get_cached_comments(db: Session, video_id: int) -> list[str] | None:
    row = (
        db.query(VideoCommentCache)
        .filter(VideoCommentCache.video_id == video_id)
        .first()
    )

    if not row:
        return None

    comments = [row.comment_1, row.comment_2, row.comment_3]
    return [c for c in comments if c]


def generate_and_cache_comments(
    db: Session,
    video_id: int,
    youtube_video_id: str,
    video_candidate: VideoCandidate,
) -> list[str]:
    existing = (
        db.query(VideoCommentCache)
        .filter(VideoCommentCache.video_id == video_id)
        .first()
    )

    if existing:
        comments = [existing.comment_1, existing.comment_2, existing.comment_3]
        return [c for c in comments if c]

    comments = generate_comments(video_candidate)

    if not comments:
        comments = ["Nice video"]

    cache_row = VideoCommentCache(
        video_id=video_id,
        youtube_video_id=youtube_video_id,
        comment_1=comments[0],
        comment_2=comments[1] if len(comments) > 1 else None,
        comment_3=comments[2] if len(comments) > 2 else None,
    )

    db.add(cache_row)
    db.commit()
    db.refresh(cache_row)

    return [c for c in [cache_row.comment_1, cache_row.comment_2, cache_row.comment_3] if c]