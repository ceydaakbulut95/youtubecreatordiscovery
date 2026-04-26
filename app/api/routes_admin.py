from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_admin
from app.models.interaction import Interaction
from app.models.search_seed import SearchSeed
from app.models.user import User
from app.models.video import Video
from app.models.video_comment_cache import VideoCommentCache

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    total_users = db.query(User).count()
    total_paid_users = db.query(User).filter(User.payment_status == "paid").count()
    total_free_users = db.query(User).filter(User.payment_status != "paid").count()
    new_users_last_7_days = db.query(User).filter(User.created_at >= seven_days_ago).count()

    total_videos = db.query(Video).count()
    new_videos_last_7_days = db.query(Video).filter(Video.created_at >= seven_days_ago).count()

    total_seeds = db.query(SearchSeed).count()
    total_active_seeds = db.query(SearchSeed).filter(SearchSeed.is_active == True).count()

    total_interactions = db.query(Interaction).count()
    total_opened_interactions = db.query(Interaction).filter(Interaction.opened == True).count()
    total_copied_interactions = db.query(Interaction).filter(Interaction.copied == True).count()
    total_selected_interactions = db.query(Interaction).filter(Interaction.selected == True).count()

    total_comment_cache_rows = db.query(VideoCommentCache).count()

    open_rate = round(total_opened_interactions / total_interactions, 4) if total_interactions else 0.0
    copy_rate = round(total_copied_interactions / total_interactions, 4) if total_interactions else 0.0
    selection_rate = round(total_selected_interactions / total_interactions, 4) if total_interactions else 0.0
    paid_user_rate = round(total_paid_users / total_users, 4) if total_users else 0.0

    return {
        "users": {
            "total": total_users,
            "paid": total_paid_users,
            "free": total_free_users,
            "new_last_7_days": new_users_last_7_days,
            "paid_user_rate": paid_user_rate,
        },
        "videos": {
            "total": total_videos,
            "new_last_7_days": new_videos_last_7_days,
        },
        "seeds": {
            "total": total_seeds,
            "active": total_active_seeds,
        },
        "interactions": {
            "total": total_interactions,
            "opened": total_opened_interactions,
            "copied": total_copied_interactions,
            "selected": total_selected_interactions,
            "open_rate": open_rate,
            "copy_rate": copy_rate,
            "selection_rate": selection_rate,
        },
        "comment_cache": {
            "total": total_comment_cache_rows,
        },
    }