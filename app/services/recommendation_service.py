from sqlalchemy.orm import Session

from app.models.interaction import Interaction
from app.models.user import User
from app.schemas.filters import VideoSearchRequest
from app.schemas.response import RecommendationResponse, VideoRecommendation
from app.schemas.video import VideoCandidate
from app.services.comment_cache_service import generate_and_cache_comments
from app.services.usage_service import enforce_search_limit, increment_search_count
from app.services.video_query_service import get_videos_for_recommendation


def _to_video_candidate(db_video) -> VideoCandidate:
    return VideoCandidate(
        video_id=db_video.youtube_video_id,
        title=db_video.title,
        description=db_video.description,
        video_url=db_video.video_url,
        channel_id=db_video.youtube_channel_id,
        channel_name=db_video.channel_name,
        subscriber_count=db_video.subscriber_count,
        creator_reply_ratio=db_video.creator_reply_ratio,
        engagement_score=db_video.engagement_score,
        comment_count=db_video.comment_count,
        days_since_upload=db_video.days_since_upload,
        niche=db_video.niche,
    )


def build_recommendations(
    request: VideoSearchRequest,
    db: Session,
    current_user: User,
) -> RecommendationResponse:
    enforce_search_limit(current_user)

    db_videos = get_videos_for_recommendation(
        db=db,
        niche=request.niche,
        subscriber_min=request.subscriber_min,
        subscriber_max=request.subscriber_max,
        min_engagement_score=request.min_engagement_score,
        min_video_comment_count=request.min_video_comment_count,
        only_active_creators=request.only_active_creators,
        max_results=request.max_results,
    )

    staged_results: list[tuple[Interaction, VideoCandidate, list[str]]] = []

    for db_video in db_videos:
        video_candidate = _to_video_candidate(db_video)

        comments = generate_and_cache_comments(
            db=db,
            video_id=db_video.id,
            youtube_video_id=db_video.youtube_video_id,
            video_candidate=video_candidate,
        )

        interaction = Interaction(
            video_id=db_video.id,
            youtube_video_id=db_video.youtube_video_id,
            youtube_channel_id=db_video.youtube_channel_id,
            suggested_comment=comments[0] if comments else "",
        )

        db.add(interaction)
        staged_results.append((interaction, video_candidate, comments))

    db.commit()

    recommendations: list[VideoRecommendation] = []

    for interaction, video_candidate, comments in staged_results:
        db.refresh(interaction)
        recommendations.append(
            VideoRecommendation(
                interaction_id=interaction.id,
                video=video_candidate,
                suggested_comments=comments,
            )
        )

    increment_search_count(db, current_user)

    return RecommendationResponse(
        total_results=len(recommendations),
        results=recommendations,
    )