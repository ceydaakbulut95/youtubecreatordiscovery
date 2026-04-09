import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.db.database import SessionLocal
from app.services.ingestion_service import run_daily_inventory_fill


def main():
    db = SessionLocal()
    try:
        result = run_daily_inventory_fill(
            db=db,
            target_per_niche=250,
            published_after_days=90,
            max_seeds_per_run=10,
        )
        print(result.model_dump())
    finally:
        db.close()


if __name__ == "__main__":
    main()