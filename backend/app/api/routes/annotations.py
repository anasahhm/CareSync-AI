"""GestureMed AI — Annotations API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Annotation

router = APIRouter()


class CreateAnnotationRequest(BaseModel):
    consultation_id: str
    annotation_type: str = "point"
    coordinates: dict
    body_region: Optional[str] = None
    note: Optional[str] = None
    color: str = "#FF6B6B"


@router.post("/", status_code=201)
async def create_annotation(
    body: CreateAnnotationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ann = Annotation(
        consultation_id=body.consultation_id,
        created_by_id=current_user.id,
        annotation_type=body.annotation_type,
        coordinates=body.coordinates,
        body_region=body.body_region,
        note=body.note,
        color=body.color,
    )
    db.add(ann)
    await db.commit()
    await db.refresh(ann)
    return {"id": ann.id, "status": "created"}


@router.get("/{consultation_id}")
async def get_annotations(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Annotation)
        .where(Annotation.consultation_id == consultation_id)
        .order_by(Annotation.created_at)
    )
    annotations = result.scalars().all()
    return [
        {
            "id": a.id,
            "type": a.annotation_type,
            "coordinates": a.coordinates,
            "body_region": a.body_region,
            "note": a.note,
            "color": a.color,
            "created_at": a.created_at,
        }
        for a in annotations
    ]
