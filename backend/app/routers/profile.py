from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Profile, ProfileBullet, User
from app.services import profile_extractor
from app.services.resume_parse import extract_text

router = APIRouter()


@router.post("/profile")
async def upload_profile(file: UploadFile, email: str = Form(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        resume_text = extract_text(file.filename, content)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not resume_text.strip():
        raise HTTPException(400, "Could not extract any text from resume")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.commit()

    master_profile = profile_extractor.extract(db, resume_text, user_id=user.id)

    profile_row = Profile(user_id=user.id, master_json=master_profile.model_dump(), version=1)
    db.add(profile_row)
    db.flush()  # assign profile_row.id before bullets reference it

    for bullet in master_profile.bullets:
        db.add(
            ProfileBullet(
                id=bullet.id,
                profile_id=profile_row.id,
                experience_id=bullet.experience_id,
                text=bullet.text,
                tags=bullet.tags,
            )
        )
    db.commit()

    return {"profile_id": profile_row.id, "profile": master_profile.model_dump()}


@router.get("/profile/vault")
def get_profile_vault(email: str, db: Session = Depends(get_db)):
    """Fetched by the extension's background service worker into memory only —
    never written to chrome.storage (§7 Phase 3, §6 security).

    # ponytail/SECURITY: email-as-identity has no real authentication behind it,
    # same placeholder as the rest of the app (§3 defers real auth to Clerk/Supabase,
    # not yet wired). Do NOT ship the extension against this endpoint without a real
    # bearer token check first — right now anyone who knows an email can pull that
    # user's profile vault.
    """
    user = db.query(User).filter_by(email=email).first()
    if not user:
        raise HTTPException(404, "user not found")
    profile_row = db.query(Profile).filter_by(user_id=user.id).order_by(Profile.created_at.desc()).first()
    if not profile_row:
        raise HTTPException(404, "no profile for this user")
    return {"profile_id": profile_row.id, "profile": profile_row.master_json}
