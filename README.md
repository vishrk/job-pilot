# JobPilot — Phase 0 + Phase 1

## Setup

```bash
docker compose up -d                      # Postgres 16 + pgvector

cd backend
python -m venv .venv && .venv/Scripts/activate   # or source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                      # fill in ANTHROPIC_API_KEY, VOYAGE_API_KEY
alembic upgrade head
python -m seed.load_seed                  # loads ~60 companies (Greenhouse/Lever/Ashby) + skill aliases
uvicorn app.main:app --reload
python -m app.worker                      # separate process: polls & runs due Hunts every 60s

cd ../frontend
npm install
npm run dev                               # http://localhost:5173
```

## Tests

```bash
cd backend
pytest tests/                             # golden set + unit tests, no DB/API keys needed
```

## Phase 1 additions

- `app/services/adapters/{lever,ashby}.py` — verified live against real boards (Palantir/Spotify/Outreach
  on Lever, Ramp/Notion/OpenAI/Linear/Vanta/Watershed on Ashby).
- `app/services/ats_detect.py` — given a domain, tries it against all three adapters to find the ATS + board token.
- `app/services/job_dedup.py` — collapses the same role cross-posted to two boards into one `jobs` row,
  keyed on `(company_id, normalized_title, location)`.
- `app/services/discovery.py` — shared discovery+scoring path used by both `POST /matches` (ad hoc) and
  the Hunt runner, so a job is fetched/parsed once regardless of which caller triggered it (§2.5).
- `app/services/hunt_runner.py` + `app/worker.py` — Postgres `FOR UPDATE SKIP LOCKED` queue over the
  `hunts` table; a failing adapter is logged and skipped, never fails the whole hunt (see the module
  docstring for the one known limitation: commits inside the run release the claim lock early, fine
  for a single worker process, revisit if a second worker is ever added).
- `app/services/gap_analysis.py` — prep plan generator, `GET /matches/{id}/prep-plan`, distinguishes
  closeable vs. structural gaps.
- Match inbox: `GET /matches/inbox?email=...` (new/dismissed state, `min_score` filter),
  `POST /matches/{id}/dismiss`.
- Hunts CRUD: `POST/GET/DELETE /hunts`, `POST /hunts/{id}/run` for a manual trigger without waiting on the worker.

## Embedding provider

Voyage AI (`voyage-3.5-lite`, 512-dim) — Anthropic's recommended embeddings partner,
used for skill-normalization fallback and the seniority_fit/domain_fit score components.
Requires `VOYAGE_API_KEY`.
