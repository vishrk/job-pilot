from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Profile, User
from app.schemas.profile import MasterProfile
from app.services import answer_library

router = APIRouter()


class ResolveAnswerRequest(BaseModel):
    email: str
    question: str


@router.post("/answers/resolve")
def resolve_answer(req: ResolveAnswerRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=req.email).first()
    if not user:
        raise HTTPException(404, "user not found")
    profile_row = db.query(Profile).filter_by(user_id=user.id).order_by(Profile.created_at.desc()).first()
    if not profile_row:
        raise HTTPException(400, "no profile for this user")

    profile = MasterProfile.model_validate(profile_row.master_json)
    return answer_library.resolve_answer(db, user_id=user.id, question_text=req.question, profile=profile)
