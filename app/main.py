from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from app.core.config import settings
from app.core.limiter import limiter

from app.db.database import Base, engine
from app.models import Video, SearchSeed, Interaction, User, PasswordResetToken

from app.api.routes_auth import router as auth_router
from app.api.routes_health import router as health_router
from app.api.routes_search import router as search_router
from app.api.routes_interactions import router as interactions_router
from app.api.routes_seeds import router as seeds_router
from app.api.routes_videos_db import router as videos_db_router
from app.api.routes_ingestion import router as ingestion_router
from app.api.routes_billing import router as billing_router
from app.api.routes_password_reset import router as password_reset_router
from app.api.routes_admin import router as admin_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="YouTube Creator Discovery Assistant",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(search_router)
app.include_router(interactions_router)
app.include_router(seeds_router)
app.include_router(videos_db_router)
app.include_router(ingestion_router)
app.include_router(billing_router)
app.include_router(password_reset_router)
app.include_router(admin_router)


@app.get("/")
def root():
    return {
        "message": "YouTube Creator Discovery Assistant API is running",
        "docs": "/docs",
    }