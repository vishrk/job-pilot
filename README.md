# JobPilot — Phase 0

## Setup

```bash
docker compose up -d                      # Postgres 16 + pgvector

cd backend
python -m venv .venv && .venv/Scripts/activate   # or source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                      # fill in ANTHROPIC_API_KEY, VOYAGE_API_KEY
alembic upgrade head
python -m seed.load_seed                  # loads ~50 Greenhouse companies + skill aliases
uvicorn app.main:app --reload

cd ../frontend
npm install
npm run dev                               # http://localhost:5173
```

## Tests

```bash
cd backend
pytest tests/                             # scorer golden set + skill-normalize unit tests, no DB/API keys needed
```

## Embedding provider

Voyage AI (`voyage-3.5-lite`, 512-dim) — Anthropic's recommended embeddings partner,
used for skill-normalization fallback and the seniority_fit/domain_fit score components.
Requires `VOYAGE_API_KEY`.
