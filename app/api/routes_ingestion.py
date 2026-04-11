from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.ingestion_service import (
    run_bulk_ingestion_from_active_seeds,
    run_ingestion_for_keyword,
    run_ingestion_from_seed,
)

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


class IngestionKeywordRequest(BaseModel):
    keyword: str
    niche: str
    min_weeks_ago: int = Field(default=2, ge=1)
    max_weeks_ago: int = Field(default=4, ge=2)
    max_pages: int = Field(default=2, ge=1, le=10)
    page_size: int = Field(default=25, ge=1, le=50)


class IngestionSeedRequest(BaseModel):
    seed_id: int
    min_weeks_ago: int = Field(default=2, ge=1)
    max_weeks_ago: int = Field(default=4, ge=2)
    max_pages: int = Field(default=2, ge=1, le=10)
    page_size: int = Field(default=25, ge=1, le=50)


class IngestionBulkRequest(BaseModel):
    niche: str | None = None
    max_seeds: int | None = Field(default=None, ge=1)
    min_weeks_ago: int = Field(default=2, ge=1)
    max_weeks_ago: int = Field(default=4, ge=2)
    max_pages: int = Field(default=2, ge=1, le=10)
    page_size: int = Field(default=25, ge=1, le=50)


@router.post("/run-keyword")
def run_keyword_ingestion(
    request: IngestionKeywordRequest,
    db: Session = Depends(get_db),
):
    if request.min_weeks_ago >= request.max_weeks_ago:
        raise HTTPException(
            status_code=400,
            detail="min_weeks_ago must be smaller than max_weeks_ago",
        )

    try:
        result = run_ingestion_for_keyword(
            db=db,
            keyword=request.keyword,
            niche=request.niche,
            min_weeks_ago=request.min_weeks_ago,
            max_weeks_ago=request.max_weeks_ago,
            max_pages=request.max_pages,
            page_size=request.page_size,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/run-seed")
def run_seed_ingestion(
    request: IngestionSeedRequest,
    db: Session = Depends(get_db),
):
    if request.min_weeks_ago >= request.max_weeks_ago:
        raise HTTPException(
            status_code=400,
            detail="min_weeks_ago must be smaller than max_weeks_ago",
        )

    try:
        result = run_ingestion_from_seed(
            db=db,
            seed_id=request.seed_id,
            min_weeks_ago=request.min_weeks_ago,
            max_weeks_ago=request.max_weeks_ago,
            max_pages=request.max_pages,
            page_size=request.page_size,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/run-bulk")
def run_bulk_ingestion(
    request: IngestionBulkRequest,
    db: Session = Depends(get_db),
):
    if request.min_weeks_ago >= request.max_weeks_ago:
        raise HTTPException(
            status_code=400,
            detail="min_weeks_ago must be smaller than max_weeks_ago",
        )

    try:
        result = run_bulk_ingestion_from_active_seeds(
            db=db,
            niche=request.niche,
            max_seeds=request.max_seeds,
            min_weeks_ago=request.min_weeks_ago,
            max_weeks_ago=request.max_weeks_ago,
            max_pages=request.max_pages,
            page_size=request.page_size,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))