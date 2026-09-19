from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.llm.client import call_structured

SYSTEM_PROMPT = """You narrate a job match score that was already computed by code. Explain
in 2-3 sentences why the score landed where it did, referencing the strongest and weakest
components. You may propose a small adjustment (-10 to +10) only if the computed score
clearly misrepresents the fit for a reason the components don't capture — state that reason
explicitly. Most of the time adjustment should be 0."""


class Explanation(BaseModel):
    narrative: str
    adjustment: int  # -10..10
    adjustment_reason: str | None = None


def explain(db: Session, *, job_title: str, score: float, components: dict, gates: dict, user_id: str | None = None) -> Explanation:
    prompt = (
        f"Job: {job_title}\nComputed score: {score}/100\n"
        f"Components: {components}\nGates: {gates}"
    )
    return call_structured(
        db,
        node="score_explainer",
        model="claude-sonnet-5",
        effort="low",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        output_schema=Explanation,
        user_id=user_id,
    )
