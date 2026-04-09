from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.interaction import Interaction
from app.schemas.interaction import InteractionCreate, InteractionResponse

router = APIRouter(prefix="/interactions", tags=["Interactions"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=InteractionResponse)
def create_interaction(request: InteractionCreate, db: Session = Depends(get_db)):
    interaction = Interaction(
        video_id=request.video_id,
        youtube_video_id=request.youtube_video_id,
        youtube_channel_id=request.youtube_channel_id,
        suggested_comment=request.suggested_comment,
        copied=request.copied,
        opened=request.opened,
        selected=request.selected,
    )

    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


@router.get("/", response_model=list[InteractionResponse])
def list_interactions(db: Session = Depends(get_db)):
    return db.query(Interaction).order_by(Interaction.created_at.desc()).all()


@router.patch("/{interaction_id}", response_model=InteractionResponse)
def update_interaction(
    interaction_id: int,
    copied: bool = False,
    opened: bool = False,
    selected: bool = False,
    db: Session = Depends(get_db),
):
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    interaction.copied = copied or interaction.copied
    interaction.opened = opened or interaction.opened
    interaction.selected = selected or interaction.selected

    db.commit()
    db.refresh(interaction)
    return interaction