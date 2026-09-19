import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.embeddings import embed
from app.models import SkillAlias, UnresolvedSkill

SIMILARITY_THRESHOLD = 0.85

# ponytail: canonical embeddings are recomputed per process start, fine at seed-table
# scale (hundreds of skills). Cache in a table if this ever shows up in profiling.
_canonical_embedding_cache: dict[str, list[float]] | None = None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _canonical_embeddings(db: Session) -> dict[str, list[float]]:
    global _canonical_embedding_cache
    if _canonical_embedding_cache is not None:
        return _canonical_embedding_cache
    canonicals = sorted({row[0] for row in db.execute(select(SkillAlias.canonical)).all()})
    if not canonicals:
        _canonical_embedding_cache = {}
        return _canonical_embedding_cache
    vectors = embed(canonicals, input_type="document")
    _canonical_embedding_cache = dict(zip(canonicals, vectors))
    return _canonical_embedding_cache


def normalize_skill(token: str, db: Session) -> str | None:
    """Alias table lookup, then embedding similarity fallback, then log as unresolved."""
    key = token.strip().lower()
    if not key:
        return None

    alias = db.scalar(select(SkillAlias).where(SkillAlias.alias == key))
    if alias:
        return alias.canonical

    canonical_vecs = _canonical_embeddings(db)
    if canonical_vecs:
        [token_vec] = embed([token], input_type="query")
        best_match, best_score = None, 0.0
        for canonical, vec in canonical_vecs.items():
            score = _cosine(token_vec, vec)
            if score > best_score:
                best_match, best_score = canonical, score
        if best_score >= SIMILARITY_THRESHOLD:
            db.add(SkillAlias(canonical=best_match, alias=key))
            db.commit()
            return best_match

    existing = db.get(UnresolvedSkill, key)
    if existing:
        existing.count += 1
    else:
        db.add(UnresolvedSkill(token=key, count=1))
    db.commit()
    return None


def normalize_skills(tokens: list[str], db: Session) -> dict[str, str | None]:
    return {token: normalize_skill(token, db) for token in tokens}
