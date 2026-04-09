from pydantic import BaseModel


class IngestionRunRequest(BaseModel):
    niche: str | None = None
    only_active_seeds: bool = True
    max_seeds: int = 10


class IngestionRunResponse(BaseModel):
    total_seeds_processed: int
    total_videos_found: int
    total_inserted: int
    total_updated: int


class DailyIngestionResponse(BaseModel):
    target_per_niche: int
    published_after_days: int
    results: list[dict]