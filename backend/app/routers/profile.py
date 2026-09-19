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
