from app.db.database import SessionLocal
from app.services.ingestion_service import run_bulk_ingestion_from_active_seeds

DEFAULT_NICHES = ["food", "fitness", "beauty", "coding", "travel"]

MAX_SEEDS_PER_NICHE = 10
MIN_WEEKS_AGO = 2
MAX_WEEKS_AGO = 4
MAX_PAGES = 1
PAGE_SIZE = 25


def main() -> None:
    db = SessionLocal()
    try:
        grand_total_inserted = 0
        grand_total_skipped_duplicates = 0
        all_results = []

        print("----- DAILY FILL STARTED -----")
        print(
            f"settings: max_seeds={MAX_SEEDS_PER_NICHE}, "
            f"window={MIN_WEEKS_AGO}-{MAX_WEEKS_AGO} weeks, "
            f"max_pages={MAX_PAGES}, page_size={PAGE_SIZE}"
        )

        for niche in DEFAULT_NICHES:
            try:
                result = run_bulk_ingestion_from_active_seeds(
                    db=db,
                    niche=niche,
                    max_seeds=MAX_SEEDS_PER_NICHE,
                    min_weeks_ago=MIN_WEEKS_AGO,
                    max_weeks_ago=MAX_WEEKS_AGO,
                    max_pages=MAX_PAGES,
                    page_size=PAGE_SIZE,
                )

                grand_total_inserted += result.get("total_inserted", 0)
                grand_total_skipped_duplicates += result.get("total_skipped_duplicates", 0)
                all_results.append(result)

                print(
                    f"[{niche}] "
                    f"seed_count={result.get('seed_count', 0)} "
                    f"inserted={result.get('total_inserted', 0)} "
                    f"skipped_duplicates={result.get('total_skipped_duplicates', 0)}"
                )
            except Exception as e:
                print(f"[{niche}] failed: {e}")

        print("----- DAILY FILL SUMMARY -----")
        print(f"grand_total_inserted={grand_total_inserted}")
        print(f"grand_total_skipped_duplicates={grand_total_skipped_duplicates}")

        for result in all_results:
            print(result)

    finally:
        db.close()


if __name__ == "__main__":
    main()