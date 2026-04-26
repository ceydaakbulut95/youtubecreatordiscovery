from app.db.database import SessionLocal
from app.services.ingestion_service import run_bulk_ingestion_from_active_seeds

DEFAULT_NICHES = ["food", "fitness", "beauty", "coding", "travel"]


def main() -> None:
    db = SessionLocal()
    try:
        grand_total_inserted = 0
        grand_total_skipped_duplicates = 0
        all_results = []

        for niche in DEFAULT_NICHES:
            result = run_bulk_ingestion_from_active_seeds(
                db=db,
                niche=niche,
                max_seeds=5,
                min_weeks_ago=2,
                max_weeks_ago=4,
                max_pages=1,
                page_size=25,
            )

            grand_total_inserted += result.get("total_inserted", 0)
            grand_total_skipped_duplicates += result.get("total_skipped_duplicates", 0)
            all_results.append(result)

            print(
                f"[{niche}] inserted={result.get('total_inserted', 0)} "
                f"skipped_duplicates={result.get('total_skipped_duplicates', 0)}"
            )

        print("----- DAILY FILL SUMMARY -----")
        print(f"grand_total_inserted={grand_total_inserted}")
        print(f"grand_total_skipped_duplicates={grand_total_skipped_duplicates}")

        for result in all_results:
            print(result)

    finally:
        db.close()


if __name__ == "__main__":
    main()