from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document
from app.services import cover_letter, export, match_context, tailor, verifier

router = APIRouter()


def _verify_and_store(db: Session, document: Document, profile, user_id: str) -> None:
    text = verifier.resume_text(document.content_json) if document.kind == "resume" else verifier.cover_letter_text(document.content_json)
    report = verifier.verify(db, document_text=text, profile=profile, user_id=user_id)
    document.verify_report = report.model_dump()
    db.commit()


def _doc_out(d: Document) -> dict:
    return {
        "id": d.id,
        "match_id": d.match_id,
        "kind": d.kind,
        "version": d.version,
        "content": d.content_json,
        "provenance_map": d.provenance_map,
        "verify_report": d.verify_report,
        "rejected_bullets": d.rejected_bullets,
        "status": d.status,
        "approved_bullet_ids": d.approved_bullet_ids,
    }


@router.post("/matches/{match_id}/documents/resume")
def create_resume(match_id: str, db: Session = Depends(get_db)):
    ctx = match_context.load(db, match_id)
    if not ctx:
        raise HTTPException(400, "missing job requirements or profile for this match")
    match_row, profile, job = ctx

    draft = tailor.tailor_resume(db, profile=profile, job=job, user_id=match_row.user_id)
    document = Document(
        match_id=match_id,
        kind="resume",
        version=1,
        content_json=draft["content"],
        provenance_map=draft["provenance_map"],
        rejected_bullets=draft["rejected_bullets"],
    )
    db.add(document)
    db.commit()
    _verify_and_store(db, document, profile, match_row.user_id)
    return _doc_out(document)


@router.post("/matches/{match_id}/documents/cover-letter")
def create_cover_letter(match_id: str, db: Session = Depends(get_db)):
    ctx = match_context.load(db, match_id)
    if not ctx:
        raise HTTPException(400, "missing job requirements or profile for this match")
    match_row, profile, job = ctx

    draft = cover_letter.generate_cover_letter(db, profile=profile, job=job, user_id=match_row.user_id)
    document = Document(
        match_id=match_id,
        kind="cover_letter",
        version=1,
        content_json=draft["content"],
        provenance_map=draft["provenance_map"],
        rejected_bullets=draft["rejected_bullets"],
    )
    db.add(document)
    db.commit()
    _verify_and_store(db, document, profile, match_row.user_id)
    return _doc_out(document)


@router.get("/documents/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "document not found")
    return _doc_out(document)


class RegenerateRequest(BaseModel):
    notes: str = ""


@router.post("/documents/{document_id}/regenerate")
def regenerate_document(document_id: str, req: RegenerateRequest, db: Session = Depends(get_db)):
    prior = db.get(Document, document_id)
    if not prior:
        raise HTTPException(404, "document not found")
    ctx = match_context.load(db, prior.match_id)
    if not ctx:
        raise HTTPException(400, "missing job requirements or profile for this match")
    match_row, profile, job = ctx

    if prior.kind == "resume":
        draft = tailor.tailor_resume(db, profile=profile, job=job, user_id=match_row.user_id, notes=req.notes)
    else:
        draft = cover_letter.generate_cover_letter(db, profile=profile, job=job, user_id=match_row.user_id, notes=req.notes)

    document = Document(
        match_id=prior.match_id,
        kind=prior.kind,
        version=prior.version + 1,
        content_json=draft["content"],
        provenance_map=draft["provenance_map"],
        rejected_bullets=draft["rejected_bullets"],
    )
    db.add(document)
    db.commit()
    _verify_and_store(db, document, profile, match_row.user_id)
    return _doc_out(document)


@router.get("/documents/{document_id}/export")
def export_document(document_id: str, format: str, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "document not found")
    if format not in ("pdf", "docx"):
        raise HTTPException(400, "format must be 'pdf' or 'docx'")

    if format == "pdf":
        body = export.to_pdf(document.content_json, document.kind)
        media_type = "application/pdf"
    else:
        body = export.to_docx(document.content_json, document.kind)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{document.kind}_v{document.version}.{format}"'},
    )


class ApproveRequest(BaseModel):
    accepted_bullet_ids: list[str]


@router.post("/documents/{document_id}/approve")
def approve_document(document_id: str, req: ApproveRequest, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "document not found")
    document.status = "approved"
    document.approved_bullet_ids = req.accepted_bullet_ids
    db.commit()
    return _doc_out(document)
