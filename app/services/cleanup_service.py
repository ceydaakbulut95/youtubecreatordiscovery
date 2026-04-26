from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.video import Video


def delete_videos_older_than_days(db: Session, days: int = 90) -> dict:
    cutoff_days_since_upload = days

    old_videos = (
        db.query(Video)
        .filter(Video.days_since_upload > cutoff_days_since_upload)
        .all()
    )

    deleted_count = len(old_videos)

    for video in old_videos:
        db.delete(video)

    db.commit()

    return {
        "deleted_count": deleted_count,
        "cutoff_days": days,
    }