from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Company

router = APIRouter()


@router.get("/companies")
def list_companies(db: Session = Depends(get_db)):
    companies = db.query(Company).order_by(Company.name).all()
    return [{"id": c.id, "name": c.name, "domain": c.domain} for c in companies]
