from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "youtube-commenter-backend",
    }