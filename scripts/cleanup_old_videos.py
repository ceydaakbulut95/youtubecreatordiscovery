from app.db.database import SessionLocal
from app.services.cleanup_service import delete_videos_older_than_days


def main() -> None:
    db = SessionLocal()
    try:
        result = delete_videos_older_than_days(db=db, days=90)
        print("----- CLEANUP SUMMARY -----")
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()