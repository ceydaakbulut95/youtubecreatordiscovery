from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.search_seed import SearchSeed
from app.schemas.search_seed import (
    SearchSeedBulkCreate,
    SearchSeedBulkResponse,
    SearchSeedCreate,
    SearchSeedResponse,
)

router = APIRouter(prefix="/seeds", tags=["Seeds"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=SearchSeedResponse)
def create_seed(request: SearchSeedCreate, db: Session = Depends(get_db)):
    normalized_keyword = request.keyword.strip().lower()

    existing = (
        db.query(SearchSeed)
        .filter(SearchSeed.keyword == normalized_keyword)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Seed already exists")

    seed = SearchSeed(
        niche=request.niche.strip().lower(),
        keyword=normalized_keyword,
        is_active=request.is_active,
    )

    db.add(seed)
    db.commit()
    db.refresh(seed)
    return seed


@router.post("/bulk", response_model=SearchSeedBulkResponse)
def create_seeds_bulk(request: SearchSeedBulkCreate, db: Session = Depends(get_db)):
    requested_keywords = [
        seed.keyword.strip().lower()
        for seed in request.seeds
        if seed.keyword.strip()
    ]

    existing_keywords = {
        row[0]
        for row in db.query(SearchSeed.keyword)
        .filter(SearchSeed.keyword.in_(requested_keywords))
        .all()
    }

    inserted_keywords: list[str] = []
    skipped_keywords: list[str] = []
    seen_in_payload: set[str] = set()

    for seed_data in request.seeds:
        normalized_keyword = seed_data.keyword.strip().lower()
        normalized_niche = seed_data.niche.strip().lower()

        if not normalized_keyword:
            continue

        if normalized_keyword in seen_in_payload:
            skipped_keywords.append(normalized_keyword)
            continue

        seen_in_payload.add(normalized_keyword)

        if normalized_keyword in existing_keywords:
            skipped_keywords.append(normalized_keyword)
            continue

        seed = SearchSeed(
            niche=normalized_niche,
            keyword=normalized_keyword,
            is_active=seed_data.is_active,
        )
        db.add(seed)
        inserted_keywords.append(normalized_keyword)

    db.commit()

    return SearchSeedBulkResponse(
        inserted_count=len(inserted_keywords),
        skipped_count=len(skipped_keywords),
        inserted_keywords=inserted_keywords,
        skipped_keywords=skipped_keywords,
    )


@router.get("/", response_model=list[SearchSeedResponse])
def list_seeds(db: Session = Depends(get_db)):
    return db.query(SearchSeed).order_by(SearchSeed.created_at.desc()).all()