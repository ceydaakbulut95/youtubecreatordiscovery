from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.search_seed import SearchSeed
from app.models.video import Video
from app.services.youtube_service import (
    build_published_window_between_weeks,
    search_videos_for_ingestion,
)


def _video_exists(db: Session, youtube_video_id: str) -> bool:
    return (
        db.query(Video)
        .filter(Video.youtube_video_id == youtube_video_id)
        .first()
        is not None
    )


def run_ingestion_for_keyword(
    db: Session,
    keyword: str,
    niche: str,
    min_weeks_ago: int = 2,
    max_weeks_ago: int = 4,
    max_pages: int = 2,
    page_size: int = 25,
) -> dict:
    published_after, published_before = build_published_window_between_weeks(
        min_weeks_ago=min_weeks_ago,
        max_weeks_ago=max_weeks_ago,
    )

    candidates = search_videos_for_ingestion(
        keyword=keyword,
        niche=niche,
        published_after=published_after,
        published_before=published_before,
        max_pages=max_pages,
        page_size=page_size,
    )

    inserted_count = 0
    skipped_duplicates = 0

    for item in candidates:
        youtube_video_id = item["youtube_video_id"]

        if _video_exists(db, youtube_video_id):
            skipped_duplicates += 1
            continue

        video = Video(
            youtube_video_id=item["youtube_video_id"],
            title=item["title"],
            description=item["description"],
            video_url=item["video_url"],
            youtube_channel_id=item["youtube_channel_id"],
            channel_name=item["channel_name"],
            subscriber_count=item["subscriber_count"],
            creator_reply_ratio=item.get("creator_reply_ratio", 0.0),
            engagement_score=item.get("engagement_score", 0.0),
            comment_count=item.get("comment_count", 0),
            days_since_upload=item.get("days_since_upload", 9999),
            niche=item["niche"],
        )

        db.add(video)
        inserted_count += 1

    db.commit()

    return {
        "keyword": keyword,
        "niche": niche,
        "window_weeks": f"{min_weeks_ago}-{max_weeks_ago}",
        "inserted_count": inserted_count,
        "skipped_duplicates": skipped_duplicates,
        "total_candidates_after_filters": len(candidates),
    }


def run_ingestion_from_seed(
    db: Session,
    seed_id: int,
    min_weeks_ago: int = 2,
    max_weeks_ago: int = 4,
    max_pages: int = 2,
    page_size: int = 25,
) -> dict:
    seed = db.query(SearchSeed).filter(SearchSeed.id == seed_id).first()
    if not seed:
        raise ValueError(f"Seed not found: {seed_id}")

    return run_ingestion_for_keyword(
        db=db,
        keyword=seed.keyword,
        niche=seed.niche,
        min_weeks_ago=min_weeks_ago,
        max_weeks_ago=max_weeks_ago,
        max_pages=max_pages,
        page_size=page_size,
    )


def run_bulk_ingestion_from_active_seeds(
    db: Session,
    niche: str | None = None,
    max_seeds: int | None = None,
    min_weeks_ago: int = 2,
    max_weeks_ago: int = 4,
    max_pages: int = 2,
    page_size: int = 25,
) -> dict:
    query = db.query(SearchSeed).filter(SearchSeed.is_active == True)

    if niche:
        query = query.filter(SearchSeed.niche == niche)

    query = query.order_by(SearchSeed.id.asc())

    if max_seeds:
        seeds = query.limit(max_seeds).all()
    else:
        seeds = query.all()

    results = []
    total_inserted = 0
    total_skipped_duplicates = 0

    for seed in seeds:
        result = run_ingestion_for_keyword(
            db=db,
            keyword=seed.keyword,
            niche=seed.niche,
            min_weeks_ago=min_weeks_ago,
            max_weeks_ago=max_weeks_ago,
            max_pages=max_pages,
            page_size=page_size,
        )
        results.append(result)
        total_inserted += result["inserted_count"]
        total_skipped_duplicates += result["skipped_duplicates"]

    return {
        "seed_count": len(seeds),
        "niche": niche,
        "window_weeks": f"{min_weeks_ago}-{max_weeks_ago}",
        "total_inserted": total_inserted,
        "total_skipped_duplicates": total_skipped_duplicates,
        "results": results,
    }