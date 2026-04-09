from datetime import datetime
from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.models.search_seed import SearchSeed
from app.models.video import Video
from app.schemas.ingestion import (
    DailyIngestionResponse,
    IngestionRunRequest,
    IngestionRunResponse,
)
from app.schemas.ingestion_search import IngestionSearchRequest
from app.services.youtube_service import search_videos


SUPPORTED_NICHES = ["food", "fitness", "beauty", "coding", "travel"]


def get_usable_video_count(db: Session, niche: str) -> int:
    return (
        db.query(Video)
        .filter(Video.niche == niche)
        .filter(Video.is_short == False)
        .filter(Video.has_description == True)
        .count()
    )


def _select_seeds(db: Session, niche: str, max_seeds: int, only_active_seeds: bool = True) -> list[SearchSeed]:
    query = db.query(SearchSeed).filter(SearchSeed.niche == niche)

    if only_active_seeds:
        query = query.filter(SearchSeed.is_active == True)

    seeds = (
        query.order_by(
            SearchSeed.last_fetched_at.isnot(None),
            asc(SearchSeed.last_fetched_at),
            asc(SearchSeed.id),
        )
        .limit(max_seeds)
        .all()
    )

    return seeds


def _upsert_video(db: Session, video) -> tuple[bool, bool]:
    existing = (
        db.query(Video)
        .filter(Video.youtube_video_id == video.video_id)
        .first()
    )

    if existing:
        existing.youtube_channel_id = video.channel_id
        existing.channel_name = video.channel_name
        existing.subscriber_count = video.subscriber_count
        existing.title = video.title
        existing.description = video.description
        existing.video_url = video.video_url
        existing.niche = video.niche
        existing.comment_count = video.comment_count
        existing.creator_reply_ratio = video.creator_reply_ratio
        existing.engagement_score = video.engagement_score
        existing.days_since_upload = video.days_since_upload
        existing.is_short = "#shorts" in video.title.lower()
        existing.has_description = bool(video.description.strip())
        existing.last_fetched_at = datetime.utcnow()
        return False, True

    db_video = Video(
        youtube_video_id=video.video_id,
        youtube_channel_id=video.channel_id,
        channel_name=video.channel_name,
        subscriber_count=video.subscriber_count,
        title=video.title,
        description=video.description,
        video_url=video.video_url,
        niche=video.niche,
        published_at=None,
        days_since_upload=video.days_since_upload,
        comment_count=video.comment_count,
        creator_reply_ratio=video.creator_reply_ratio,
        engagement_score=video.engagement_score,
        is_short="#shorts" in video.title.lower(),
        has_description=bool(video.description.strip()),
        last_fetched_at=datetime.utcnow(),
    )
    db.add(db_video)
    return True, False


def run_ingestion(request: IngestionRunRequest, db: Session) -> IngestionRunResponse:
    if not request.niche:
        raise ValueError("niche is required for run_ingestion")

    seeds = _select_seeds(
        db=db,
        niche=request.niche,
        max_seeds=request.max_seeds,
        only_active_seeds=request.only_active_seeds,
    )

    total_videos_found = 0
    total_inserted = 0
    total_updated = 0

    for seed in seeds:
        search_request = IngestionSearchRequest(
            keyword=seed.keyword,
            niche=seed.niche,
            subscriber_min=0,
            subscriber_max=1_000_000_000,
            only_active_creators=False,
            min_engagement_score=0.0,
            min_video_comment_count=0,
            published_after_days=90,
            search_pages=1,
            max_results=20,
        )

        videos = search_videos(search_request)
        total_videos_found += len(videos)

        for video in videos:
            inserted, updated = _upsert_video(db, video)
            if inserted:
                total_inserted += 1
            if updated:
                total_updated += 1

        seed.last_fetched_at = datetime.utcnow()
        db.commit()

    return IngestionRunResponse(
        total_seeds_processed=len(seeds),
        total_videos_found=total_videos_found,
        total_inserted=total_inserted,
        total_updated=total_updated,
    )


def run_daily_inventory_fill(
    db: Session,
    target_per_niche: int = 250,
    published_after_days: int = 90,
    max_seeds_per_run: int = 10,
) -> DailyIngestionResponse:
    results: list[dict] = []

    for niche in SUPPORTED_NICHES:
        before_count = get_usable_video_count(db, niche)
        needed = max(target_per_niche - before_count, 0)

        if needed <= 0:
            results.append(
                {
                    "niche": niche,
                    "before_count": before_count,
                    "after_count": before_count,
                    "needed": 0,
                    "seeds_processed": 0,
                    "inserted": 0,
                    "updated": 0,
                    "status": "already_full",
                }
            )
            continue

        seeds = _select_seeds(
            db=db,
            niche=niche,
            max_seeds=max_seeds_per_run,
            only_active_seeds=True,
        )

        total_inserted = 0
        total_updated = 0
        total_videos_found = 0

        for seed in seeds:
            search_request = IngestionSearchRequest(
                keyword=seed.keyword,
                niche=seed.niche,
                subscriber_min=0,
                subscriber_max=1_000_000_000,
                only_active_creators=False,
                min_engagement_score=0.0,
                min_video_comment_count=0,
                published_after_days=published_after_days,
                search_pages=1,
                max_results=20,
            )

            videos = search_videos(search_request)
            total_videos_found += len(videos)

            for video in videos:
                inserted, updated = _upsert_video(db, video)
                if inserted:
                    total_inserted += 1
                if updated:
                    total_updated += 1

            seed.last_fetched_at = datetime.utcnow()
            db.commit()

            current_count = get_usable_video_count(db, niche)
            if current_count >= target_per_niche:
                break

        after_count = get_usable_video_count(db, niche)

        results.append(
            {
                "niche": niche,
                "before_count": before_count,
                "after_count": after_count,
                "needed": needed,
                "videos_found": total_videos_found,
                "seeds_processed": len(seeds),
                "inserted": total_inserted,
                "updated": total_updated,
                "status": "filled" if after_count >= target_per_niche else "partial",
            }
        )

    return DailyIngestionResponse(
        target_per_niche=target_per_niche,
        published_after_days=published_after_days,
        results=results,
    )