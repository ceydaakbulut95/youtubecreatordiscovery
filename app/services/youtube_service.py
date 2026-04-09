from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.filters import VideoSearchRequest
from app.schemas.ingestion_search import IngestionSearchRequest
from app.schemas.video import VideoCandidate
from app.services.scoring_service import calculate_engagement_score

YOUTUBE_BASE_URL = "https://www.googleapis.com/youtube/v3"


def _chunk_list(items: list[str], size: int) -> list[list[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def _days_since(published_at: str) -> int:
    dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return max((now - dt).days, 0)

def _search_videos_paginated(
    keyword: str,
    pages: int = 5,
    page_size: int = 25,
    published_after_days: int | None = 180,
    order: str = "date",
    relevance_language: str | None = "en",
    region_code: str | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    next_page_token: str | None = None

    published_after = None
    if published_after_days is not None:
        dt = datetime.now(timezone.utc) - timedelta(days=published_after_days)
        published_after = dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    with httpx.Client(timeout=20.0) as client:
        for _ in range(pages):
            params = {
                "part": "snippet",
                "q": keyword,
                "type": "video",
                "maxResults": page_size,
                "order": order,
                "key": settings.YOUTUBE_API_KEY,
            }

            if next_page_token:
                params["pageToken"] = next_page_token
            if published_after:
                params["publishedAfter"] = published_after
            if relevance_language:
                params["relevanceLanguage"] = relevance_language
            if region_code:
                params["regionCode"] = region_code

            response = client.get(f"{YOUTUBE_BASE_URL}/search", params=params)

            if response.status_code >= 400:
                print("YOUTUBE SEARCH ERROR STATUS:", response.status_code)
                print("YOUTUBE SEARCH ERROR BODY:", response.text)
                return []

            data = response.json()
            results.extend(data.get("items", []))

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

    return results

def _get_channel_stats(channel_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not channel_ids:
        return {}

    result: dict[str, dict[str, Any]] = {}

    with httpx.Client(timeout=20.0) as client:
        for chunk in _chunk_list(channel_ids, 50):
            params = {
                "part": "snippet,statistics",
                "id": ",".join(chunk),
                "key": settings.YOUTUBE_API_KEY,
            }

            response = client.get(f"{YOUTUBE_BASE_URL}/channels", params=params)
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                result[item["id"]] = item

    return result


def _get_video_stats(video_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not video_ids:
        return {}

    result: dict[str, dict[str, Any]] = {}

    with httpx.Client(timeout=20.0) as client:
        for chunk in _chunk_list(video_ids, 50):
            params = {
                "part": "statistics",
                "id": ",".join(chunk),
                "key": settings.YOUTUBE_API_KEY,
            }

            response = client.get(f"{YOUTUBE_BASE_URL}/videos", params=params)
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                result[item["id"]] = item

    return result


def _get_comment_threads(video_id: str, max_results: int = 10) -> list[dict[str, Any]]:
    params = {
        "part": "snippet,replies",
        "videoId": video_id,
        "maxResults": max_results,
        "order": "relevance",
        "textFormat": "plainText",
        "key": settings.YOUTUBE_API_KEY,
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.get(f"{YOUTUBE_BASE_URL}/commentThreads", params=params)

            if response.status_code >= 400:
                print("YOUTUBE SEARCH ERROR STATUS:", response.status_code)
                print("YOUTUBE SEARCH ERROR BODY:", response.text)
  
            response.raise_for_status()
            data = response.json()

        return data.get("items", [])

    except httpx.HTTPError as e:
        print(f"Comment fetch failed for video {video_id}: {e}")
        return []


def _estimate_creator_reply_ratio(
    comment_threads: list[dict[str, Any]],
    channel_id: str
) -> tuple[float, int]:
    if not comment_threads:
        return 0.0, 0

    total_threads = len(comment_threads)
    creator_replied_threads = 0

    for thread in comment_threads:
        replies = thread.get("replies", {}).get("comments", [])
        creator_replied = False

        for reply in replies:
            author_channel = (
                reply.get("snippet", {})
                .get("authorChannelId", {})
                .get("value")
            )
            if author_channel == channel_id:
                creator_replied = True
                break

        if creator_replied:
            creator_replied_threads += 1

    ratio = creator_replied_threads / total_threads if total_threads else 0.0
    return round(ratio, 2), total_threads


def search_videos(request: IngestionSearchRequest) -> list[VideoCandidate]:
    if not settings.YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY is missing")

    raw_videos = _search_videos_paginated(
      keyword=request.keyword,
      pages=min(request.search_pages, 2),
      page_size=10,
      published_after_days=request.published_after_days,
      order="date",
      relevance_language="en",
      region_code=None,
)

    channel_ids = list({
        item["snippet"]["channelId"]
        for item in raw_videos
        if "snippet" in item and "channelId" in item["snippet"]
    })

    video_ids = list({
        item.get("id", {}).get("videoId")
        for item in raw_videos
        if item.get("id", {}).get("videoId")
    })

    channels_map = _get_channel_stats(channel_ids)
    videos_map = _get_video_stats(video_ids)

    results: list[VideoCandidate] = []
    seen_channels: set[str] = set()

    for item in raw_videos:
        snippet = item.get("snippet", {})
        video_id = item.get("id", {}).get("videoId")
        channel_id = snippet.get("channelId")

        if not video_id or not channel_id:
            continue

        title = snippet.get("title") or ""
        description = snippet.get("description") or ""
        channel_name = snippet.get("channelTitle") or ""
        published_at = snippet.get("publishedAt")

        if channel_id in seen_channels:
            continue

        if "#shorts" in title.lower():
            continue

        if not description.strip():
            continue

        channel_data = channels_map.get(channel_id, {})
        channel_statistics = channel_data.get("statistics", {})
        subscriber_count = int(channel_statistics.get("subscriberCount", 0))

        if not (request.subscriber_min <= subscriber_count <= request.subscriber_max):
            continue

        video_data = videos_map.get(video_id, {})
        video_statistics = video_data.get("statistics", {})
        video_comment_count = int(video_statistics.get("commentCount", 0))

        if video_comment_count < request.min_video_comment_count:
            continue

        days_since_upload = _days_since(published_at) if published_at else 9999

        if days_since_upload > request.published_after_days:
            continue

        comment_threads = _get_comment_threads(video_id, max_results=10)
        creator_reply_ratio, sampled_comment_count = _estimate_creator_reply_ratio(
            comment_threads=comment_threads,
            channel_id=channel_id,
        )

        if request.only_active_creators:
            if sampled_comment_count == 0:
                continue
            if creator_reply_ratio < 0.05:
                continue

        engagement_score = calculate_engagement_score(
            reply_ratio=creator_reply_ratio,
            comment_count=max(video_comment_count, sampled_comment_count),
            days_since_upload=days_since_upload,
        )

        if engagement_score < request.min_engagement_score:
            continue

        results.append(
            VideoCandidate(
                video_id=video_id,
                title=title,
                description=description,
                video_url=f"https://www.youtube.com/watch?v={video_id}",
                channel_id=channel_id,
                channel_name=channel_name,
                subscriber_count=subscriber_count,
                creator_reply_ratio=creator_reply_ratio,
                engagement_score=engagement_score,
                comment_count=video_comment_count,
                days_since_upload=days_since_upload,
                niche=request.niche,
            )
        )

        seen_channels.add(channel_id)

    results.sort(key=lambda x: x.engagement_score, reverse=True)
    return results[: request.max_results]