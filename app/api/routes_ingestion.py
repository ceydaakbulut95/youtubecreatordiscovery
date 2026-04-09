from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.schemas.ingestion import (
    DailyIngestionResponse,
    IngestionRunRequest,
    IngestionRunResponse,
)
from app.services.ingestion_service import run_daily_inventory_fill, run_ingestion

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/run", response_model=IngestionRunResponse)
def run_ingestion_endpoint(
    request: IngestionRunRequest,
    db: Session = Depends(get_db),
):
    return run_ingestion(request, db)


@router.post("/daily-fill", response_model=DailyIngestionResponse)
def run_daily_fill_endpoint(db: Session = Depends(get_db)):
    return run_daily_inventory_fill(
        db=db,
        target_per_niche=250,
        published_after_days=90,
        max_seeds_per_run=10,
    )