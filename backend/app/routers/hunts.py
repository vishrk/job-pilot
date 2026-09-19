from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Hunt, User
from app.services.hunt_runner import run_hunt

router = APIRouter()


class HuntCreate(BaseModel):
    email: str
    roles: list[str] = []
    locations: list[str] = []
    comp_floor: float | None = None
    company_ids: list[str]
    schedule: str = "daily"


def _hunt_dict(h: Hunt) -> dict:
    return {
        "id": h.id,
        "roles": h.roles,
        "locations": h.locations,
        "comp_floor": h.comp_floor,
        "company_ids": h.company_ids,
        "schedule": h.schedule,
        "next_run_at": h.next_run_at,
        "last_run_at": h.last_run_at,
    }


@router.post("/hunts")
def create_hunt(req: HuntCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=req.email).first()
    if not user:
        raise HTTPException(404, "user not found — upload a profile first")

    hunt = Hunt(
        user_id=user.id,
        roles=req.roles,
        locations=req.locations,
        comp_floor=req.comp_floor,
        company_ids=req.company_ids,
        schedule=req.schedule,
        next_run_at=datetime.now(timezone.utc),
    )
    db.add(hunt)
    db.commit()
    return _hunt_dict(hunt)


@router.get("/hunts")
def list_hunts(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=email).first()
    if not user:
        return []
    hunts = db.query(Hunt).filter_by(user_id=user.id).all()
    return [_hunt_dict(h) for h in hunts]


@router.delete("/hunts/{hunt_id}")
def delete_hunt(hunt_id: str, db: Session = Depends(get_db)):
    hunt = db.get(Hunt, hunt_id)
    if not hunt:
        raise HTTPException(404, "hunt not found")
    db.delete(hunt)
    db.commit()
    return {"deleted": hunt_id}


@router.post("/hunts/{hunt_id}/run")
def run_hunt_now(hunt_id: str, db: Session = Depends(get_db)):
    """Manual trigger, for testing without waiting on the scheduler (app.worker)."""
    hunt = db.get(Hunt, hunt_id)
    if not hunt:
        raise HTTPException(404, "hunt not found")
    results = run_hunt(db, hunt)
    hunt.last_run_at = datetime.now(timezone.utc)
    db.commit()
    return results
