from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.filters import VideoSearchRequest
from app.schemas.response import RecommendationResponse
from app.services.recommendation_service import build_recommendations

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("/recommendations", response_model=RecommendationResponse)
def search_recommendations(
    request: VideoSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return build_recommendations(request, db, current_user)