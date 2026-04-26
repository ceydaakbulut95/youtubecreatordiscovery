from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import settings

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_published_window_between_weeks(min_weeks_ago: int = 2, max_weeks_ago: int = 4) -> tuple[str, str]:
    """
    Returns:
      published_after, published_before

    Example for 2-4 weeks window:
    - published_after = now - 4 weeks
    - published_before = now - 2 weeks
    """
    now = datetime.now(timezone.utc)

    older_bound = now - timedelta(weeks=max_weeks_ago)
    newer_bound = now - timedelta(weeks=min_weeks_ago)

    return _iso_z(older_bound), _iso_z(newer_bound)


def _days_since_upload(published_at: str | None) -> int:
    if not published_at:
        return 9999

    try:
        published_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return max(0, (now - published_dt).days)
    except Exception:
        return 9999


def _compute_engagement_score(view_count: int, like_count: int, comment_count: int) -> float:
    if view_count <= 0:
        return 0.0
    return round((like_count + comment_count) / view_count, 4)


def _search_video_candidates(
    keyword: str,
    published_after: str | None = None,
    published_before: str | None = None,
    max_pages: int = 2,
    page_size: int = 25,
    relevance_language: str = "en",
) -> list[dict[str, Any]]:
    if not settings.YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY is missing")

    results: list[dict[str, Any]] = []
    next_page_token: str | None = None

    with httpx.Client(timeout=30.0) as client:
        for _ in range(max_pages):
            params = {
                "part": "snippet",
                "q": keyword,
                "type": "video",
                "maxResults": page_size,
                "order": "relevance",
                "relevanceLanguage": relevance_language,
                "key": settings.YOUTUBE_API_KEY,
            }

            if published_after:
                params["publishedAfter"] = published_after

            if published_before:
                params["publishedBefore"] = published_before

            if next_page_token:
                params["pageToken"] = next_page_token

            response = client.get(YOUTUBE_SEARCH_URL, params=params)
            if response.status_code >= 400:
                print("YOUTUBE SEARCH ERROR STATUS:", response.status_code)
                print("YOUTUBE SEARCH ERROR BODY:", response.text)
            response.raise_for_status()

            data = response.json()
            items = data.get("items", [])
            results.extend(items)

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

    return results


def _fetch_video_details(video_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not video_ids:
        return {}

    details_by_id: dict[str, dict[str, Any]] = {}

    with httpx.Client(timeout=30.0) as client:
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]

            response = client.get(
                YOUTUBE_VIDEOS_URL,
                params={
                    "part": "snippet,statistics",
                    "id": ",".join(batch),
                    "maxResults": 50,
                    "key": settings.YOUTUBE_API_KEY,
                },
            )
            if response.status_code >= 400:
                print("YOUTUBE VIDEOS ERROR STATUS:", response.status_code)
                print("YOUTUBE VIDEOS ERROR BODY:", response.text)
            response.raise_for_status()

            data = response.json()
            for item in data.get("items", []):
                details_by_id[item["id"]] = item

    return details_by_id


def _fetch_channel_details(channel_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not channel_ids:
        return {}

    unique_ids = list(dict.fromkeys(channel_ids))
    details_by_id: dict[str, dict[str, Any]] = {}

    with httpx.Client(timeout=30.0) as client:
        for i in range(0, len(unique_ids), 50):
            batch = unique_ids[i:i + 50]

            response = client.get(
                YOUTUBE_CHANNELS_URL,
                params={
                    "part": "snippet,statistics",
                    "id": ",".join(batch),
                    "maxResults": 50,
                    "key": settings.YOUTUBE_API_KEY,
                },
            )
            if response.status_code >= 400:
                print("YOUTUBE CHANNELS ERROR STATUS:", response.status_code)
                print("YOUTUBE CHANNELS ERROR BODY:", response.text)
            response.raise_for_status()

            data = response.json()
            for item in data.get("items", []):
                details_by_id[item["id"]] = item

    return details_by_id


def search_videos_for_ingestion(
    keyword: str,
    niche: str,
    published_after: str | None = None,
    published_before: str | None = None,
    max_pages: int = 2,
    page_size: int = 25,
) -> list[dict[str, Any]]:
    """
    Fetches candidate videos for DB ingestion.

    Rules:
    - only videos between published_after and published_before
    - only videos with comment_count >= settings.MIN_DB_VIDEO_COMMENT_COUNT
    """

    raw_candidates = _search_video_candidates(
        keyword=keyword,
        published_after=published_after,
        published_before=published_before,
        max_pages=max_pages,
        page_size=page_size,
    )

    video_ids: list[str] = []
    for item in raw_candidates:
        video_id = item.get("id", {}).get("videoId")
        if video_id:
            video_ids.append(video_id)

    video_details_by_id = _fetch_video_details(video_ids)

    channel_ids: list[str] = []
    for video in video_details_by_id.values():
        snippet = video.get("snippet", {})
        channel_id = snippet.get("channelId")
        if channel_id:
            channel_ids.append(channel_id)

    channel_details_by_id = _fetch_channel_details(channel_ids)

    final_results: list[dict[str, Any]] = []

    for raw_item in raw_candidates:
        video_id = raw_item.get("id", {}).get("videoId")
        if not video_id:
            continue

        full_video = video_details_by_id.get(video_id)
        if not full_video:
            continue

        snippet = full_video.get("snippet", {})
        statistics = full_video.get("statistics", {})

        comment_count = _safe_int(statistics.get("commentCount"))

        # Core rule: do not ingest low-signal videos
        if comment_count < settings.MIN_DB_VIDEO_COMMENT_COUNT:
            continue

        view_count = _safe_int(statistics.get("viewCount"))
        like_count = _safe_int(statistics.get("likeCount"))

        channel_id = snippet.get("channelId", "")
        channel = channel_details_by_id.get(channel_id, {})
        channel_stats = channel.get("statistics", {})

        subscriber_count = _safe_int(channel_stats.get("subscriberCount"))
        published_at = snippet.get("publishedAt")
        days_since_upload = _days_since_upload(published_at)

        engagement_score = _compute_engagement_score(
            view_count=view_count,
            like_count=like_count,
            comment_count=comment_count,
        )

        final_results.append(
            {
                "youtube_video_id": video_id,
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
                "youtube_channel_id": channel_id,
                "channel_name": snippet.get("channelTitle", ""),
                "subscriber_count": subscriber_count,
                "comment_count": comment_count,
                "view_count": view_count,
                "like_count": like_count,
                "engagement_score": engagement_score,
                "creator_reply_ratio": 0.0,
                "days_since_upload": days_since_upload,
                "published_at": published_at,
                "niche": niche,
                "keyword": keyword,
            }
        )

    return final_results