"""Loads seed companies (with their Greenhouse board tokens) and skill aliases.
Run once against a fresh DB: python -m seed.load_seed
"""

import json
from pathlib import Path

from app.db import SessionLocal
from app.models import AtsAccount, Company, SkillAlias

SEED_DIR = Path(__file__).parent


def load_companies(db):
    companies = json.loads((SEED_DIR / "companies.json").read_text())
    for c in companies:
        existing = db.query(Company).filter_by(domain=c["domain"]).first()
        if existing:
            continue
        company = Company(name=c["name"], domain=c["domain"])
        db.add(company)
        db.flush()
        db.add(AtsAccount(company_id=company.id, ats_kind=c.get("ats_kind", "greenhouse"), board_token=c["board_token"]))
    db.commit()
    print(f"Loaded {len(companies)} companies")


def load_skill_aliases(db):
    aliases = json.loads((SEED_DIR / "skill_aliases.json").read_text())
    count = 0
    for canonical, alias_list in aliases.items():
        for alias in alias_list:
            if db.query(SkillAlias).filter_by(alias=alias).first():
                continue
            db.add(SkillAlias(canonical=canonical, alias=alias))
            count += 1
    db.commit()
    print(f"Loaded {count} skill aliases")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        load_companies(db)
        load_skill_aliases(db)
    finally:
        db.close()
