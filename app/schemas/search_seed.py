from datetime import datetime
from pydantic import BaseModel


class SearchSeedCreate(BaseModel):
    niche: str
    keyword: str
    is_active: bool = True


class SearchSeedBulkCreate(BaseModel):
    seeds: list[SearchSeedCreate]


class SearchSeedResponse(BaseModel):
    id: int
    niche: str
    keyword: str
    is_active: bool
    last_fetched_at: datetime | None

    model_config = {
        "from_attributes": True
    }


class SearchSeedBulkResponse(BaseModel):
    inserted_count: int
    skipped_count: int
    inserted_keywords: list[str]
    skipped_keywords: list[str]