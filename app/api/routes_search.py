from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.filters import VideoSearchRequest
from app.schemas.response import RecommendationResponse
from app.services.recommendation_service import build_recommendations

from fastapi import APIRouter, Depends, Request
from app.core.limiter import limiter

router = APIRouter(prefix="/search", tags=["Search"])

@router.post("/recommendations", response_model=RecommendationResponse)
@limiter.limit("30/minute")
def search_recommendations(
    request: Request,
    payload: VideoSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return build_recommendations(payload, db, current_user)