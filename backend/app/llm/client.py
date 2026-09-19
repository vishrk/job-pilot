from typing import TypeVar

from anthropic import Anthropic
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.models import LlmCall

T = TypeVar("T", bound=BaseModel)

_client = Anthropic(api_key=settings.anthropic_api_key)

# $ per million tokens: (input, output). Cache reads cost ~10% of input.
PRICING = {
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
}


def _cost(model: str, input_tokens: int, output_tokens: int, cached_tokens: int) -> float:
    in_price, out_price = PRICING[model]
    uncached = max(input_tokens - cached_tokens, 0)
    return (
        uncached * in_price
        + cached_tokens * in_price * 0.1
        + output_tokens * out_price
    ) / 1_000_000


def call_structured(
    db: Session,
    *,
    node: str,
    model: str,
    effort: str,
    system: str,
    messages: list[dict],
    output_schema: type[T],
    user_id: str | None = None,
) -> T:
    """One structured (typed) call, with token+cost logging into llm_calls."""
    result = _client.messages.parse(
        model=model,
        max_tokens=8096,
        system=system,
        messages=messages,
        output_config={"effort": effort, "format": output_schema},
        thinking={"type": "adaptive"},
    )

    usage = result.usage
    cached = getattr(usage, "cache_read_input_tokens", 0) or 0
    cost = _cost(model, usage.input_tokens, usage.output_tokens, cached)

    db.add(
        LlmCall(
            user_id=user_id,
            node=node,
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=cached,
            cost_usd=cost,
        )
    )
    db.commit()

    return result.parsed
