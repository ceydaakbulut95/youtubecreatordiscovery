from datetime import datetime
from pydantic import BaseModel


class InteractionCreate(BaseModel):
    video_id: int | None = None
    youtube_video_id: str
    youtube_channel_id: str
    suggested_comment: str
    copied: bool = False
    opened: bool = False
    selected: bool = False


class InteractionResponse(BaseModel):
    id: int
    video_id: int | None
    youtube_video_id: str
    youtube_channel_id: str
    suggested_comment: str
    copied: bool
    opened: bool
    selected: bool
    created_at: datetime

    model_config = {
        "from_attributes": True
    }