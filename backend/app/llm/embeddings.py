import voyageai

from app.config import settings

_client = voyageai.Client(api_key=settings.voyage_api_key)
MODEL = "voyage-3.5-lite"  # 512-dim, cheap — matches EMBEDDING_DIM in app.models


def embed(texts: list[str], *, input_type: str) -> list[list[float]]:
    """input_type: 'query' or 'document', per Voyage's asymmetric embedding convention."""
    result = _client.embed(texts, model=MODEL, input_type=input_type, output_dimension=512)
    return result.embeddings
