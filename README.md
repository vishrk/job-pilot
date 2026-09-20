# JobPilot — Phase 0 + Phase 1 + Phase 2

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

## Phase 2 additions

- `app/services/tailor.py` — resume tailoring. `enforce_provenance()` is a pure function (no
  LLM/DB) that rejects any bullet whose `source_bullet_id` doesn't exist in the master profile
  or belongs to a different experience entry — adversarially tested in `tests/test_tailor.py`
  (fabricated ids, misattributed experience, mixed valid/invalid sections). The skills list is
  always Python-computed from the master profile; the LLM's output schema has no `skills` field
  at all, so there's nothing for a misbehaving model to inject.
- `app/services/cover_letter.py` — same discipline for prose: each paragraph cites the bullet
  ids its specifics come from, unknown citations are stripped (`strip_unknown_citations()`,
  also adversarially tested) but the paragraph text is kept so the verifier still sees it.
- `app/services/verifier.py` — entailment check against the master profile; unsupported claims
  are returned, not dropped, and shown inline in the UI (`TailorPanel.tsx`'s unsupported-claims box).
- `app/services/export.py` — DOCX (python-docx) and PDF (reportlab) export, plain
  paragraphs/headings only — no tables, text boxes, or multi-column layout, so it stays
  ATS-parseable. `tests/test_export.py` checks the DOCX round-trips through our own
  `resume_parse.extract_text` with no lost bullet/summary/skill text; the LLM re-extraction
  half of that criterion needs a live API key (manual acceptance step).
- `documents` table + `Document` model — versioned; `POST /documents/{id}/regenerate` with
  user notes creates a new version rather than mutating the old one.
- Frontend: `TailorPanel.tsx` — bullet-level original-vs-tailored diff, checkboxes per bullet,
  rejected-bullet and unsupported-claim boxes, regenerate-with-feedback, approve, then PDF/DOCX
  export links (export only unlocks after approval).

## Embedding provider

Voyage AI (`voyage-3.5-lite`, 512-dim) — Anthropic's recommended embeddings partner,
used for skill-normalization fallback and the seniority_fit/domain_fit score components.
Requires `VOYAGE_API_KEY`.
