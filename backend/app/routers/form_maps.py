from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.form import FormField
from app.services import form_mapper

router = APIRouter()


class ResolveFormRequest(BaseModel):
    domain: str
    form_fingerprint: str
    fields: list[FormField]


@router.post("/form-maps/resolve")
def resolve_form(req: ResolveFormRequest, db: Session = Depends(get_db)):
    result = form_mapper.resolve_form(db, domain=req.domain, form_fingerprint=req.form_fingerprint, fields=req.fields)
    return result.model_dump()
