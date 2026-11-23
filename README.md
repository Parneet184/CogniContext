# CogniContext

Psychometric-driven affective RAG concept: **working frontend demo + honest backend scaffold**.

## Run frontend

```bash
cd frontend
python -m http.server 8000
```

Open http://localhost:8000. The demo works without keys, database, or network (web fonts require network). Select energy, then emotion, then Find my reflection. Explore sources, citations, sample chat and the architecture drawer.

## Run API

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8001
```

Open http://localhost:8001/docs for OpenAPI docs. `GET /api/v1/health` reports which services are not configured. Live endpoints return HTTP 503 intentionally; **they are not implemented live**.

## Database foundation

Apply `sql/001_schema.sql` to PostgreSQL with pgvector installed. The embedding vector(768) is a **placeholder dimension**; change it to the selected embedding model's actual output dimension before ingesting. Private tables have RLS enabled and no client access policies; do not expose privileged database keys in browser code.

## System architecture target

Assessment → thematic state mapping → SQL prefilter → multilingual vector + lexical retrieval → reranking → provenance checks → grounded LLM → validated citations → notebook.

## Implementation status

- Functional: responsive frontend, two-stage assessment, six emotions, loading transition, notebook, sample scripture navigation, toggles, text sizing, copy, predefined conversational replies, source highlighting, accessible architecture drawer.
- Scaffold only: FastAPI request validation, honest health status, schema and a few backend tests.
- **Not implemented:** real corpus ingestion, embedding model, SQL/vector retrieval service, reranking, source validation, real LLM generation, persistent sessions, authentication, secure session authorization, complete RLS policies, speech playback, full evaluation suite and production deployment.
- **Scripture notice:** sample Gurmukhi strings and illustrative English renderings are not represented as verified canonical records or authorized translations. Replace with expert-reviewed, appropriately licensed data before real use.

## Privacy

Demo selections stay in JavaScript memory. No assessment data is saved or transmitted. The backend rejects live requests rather than returning fictional verified sources.

## Next steps

1. Obtain an authorized, versioned scripture and translation dataset with provenance.
2. Validate metadata and verse boundaries against the chosen edition.
3. Select/evaluate multilingual embeddings on Gurmukhi + English; update vector dimension.
4. Implement secure server-side corpus ingestion, hybrid retrieval and citation verification.
5. Add authenticated session storage with ownership enforcement and RLS policies.
6. Integrate a grounded LLM with abstention and safety checks; add evaluation and integration tests.

## Local database upgrade (v0.2)

See [LOCAL_DATABASE_GUIDE.md](LOCAL_DATABASE_GUIDE.md) for the new working SQLite schema, CSV/JSON importer, emotion-aware SQL lookup, API documentation, and tests. The previous **scaffold-only** API description above is superseded for database/search endpoints: `GET /api/v1/health`, `/api/v1/themes`, `/api/v1/scriptures`, `/api/v1/scriptures/{id}`, and `POST /api/v1/assess` now work. Grounded AI chat, vector retrieval, and authenticated scripture records are still pending. The colorful frontend remains a separately labeled demo.


## Japji Sahib RAG MVP (new)

The project now includes a first local corpus pipeline for Japji Sahib: 38 Pauris and the concluding Salok are extracted into `backend/data_templates/japji_pauris_extracted.json` and imported into a dedicated SQLite schema. The dedicated tables keep Pauri numbers separate from Ang numbers in the existing general scripture catalogue.

See [backend/README_JAPJI_RAG.md](backend/README_JAPJI_RAG.md) for setup and API instructions. In short, from the project root run:

```bash
python -m pip install -r backend/requirements.txt
python -m backend.import_japji
python -c "from backend.vector_store import build_collection; print(build_collection())"
uvicorn backend.main:app --reload --port 8001
```

Vector retrieval requires downloading the multilingual embedding model the first time. Emotion mappings remain empty until reviewed and confirmed by the project owner. The extracted Gurmukhi field is unavailable in the supplied PDF's font encoding; only the readable transliteration and supplied English translation have been imported.


Japji Sahib RAG implementation (MVP)
What is implemented
- Extracted 38 numbered Pauris and the concluding Salok from data_templates/Japji-Sahib-GRE.pdf.
- Structured Romanized Punjabi transliteration and the supplied English translation separately.
- Added a dedicated SQLite schema for 38 Pauris, the concluding Salok, and emotion tags. This is deliberately separate from the existing scriptures table because Pauri numbers are not Sri Guru Granth Sahib Ang numbers.
- Added a ChromaDB vector-store module using intfloat/multilingual-e5-small (384 dimensions).
- Added API routes for listing/reading Pauris and semantic vector search.
Important source limitation
The PDF's embedded Gurmukhi font mapping does not extract as valid Unicode text. The imported original_gurmukhi value is therefore NULL. Do not invent or infer the Gurmukhi text. Add it only from a separately verified, appropriately authorized source. The transliteration and English translation are retained as extracted and still require human proofreading against the intended edition.

The supplied English translation's rights/provenance have not been independently verified. Keep the source PDF and translation provenance attached to any public release.
Setup (run from the project root)
python -m pip install -r backend/requirements.txt
python -m backend.import_japji
The first vector ingestion downloads the embedding model if it is not already cached:
python -c "from backend.vector_store import build_collection; print(build_collection())"
API
Start the API:
uvicorn backend.main:app --reload --port 8001
- GET /api/v1/japji/pauris — list all imported Pauris.
- GET /api/v1/japji/pauris/1 — get one Pauri.
- GET /api/v1/japji/salok — get the concluding Salok.
- POST /api/v1/japji/search — vector search; optional emotion filter.
Example request:
{
  "query": "How can I accept things that are outside my control?",
  "limit": 5,
  "emotion": "overwhelmed"
}
Emotion mapping
The japji_emotion_map table is intentionally empty until the project's owner reviews and confirms the proposed emotion-to-Pauri associations. Do not treat generated or illustrative mappings as established truth.
Model choice
intfloat/multilingual-e5-small is used for a compact 384-dimensional multilingual embedding model. It is a practical MVP choice; evaluate retrieval quality on representative queries before calling the system production-ready. The E5 convention is used: prefix corpus text with passage: and user queries with query:.
Provisional emotion mappings (MVP test only)
The project includes a provisional many-to-many emotion annotation for all 38 Pauris, based on the initial assistant proposal and approved by the user for end-to-end workflow testing. These are draft interpretations, not authoritative meanings or theological classifications. They must be reviewed and corrected before public release or any claim of scripture-grounded emotional guidance.

After importing the Pauris, run:
python -m backend.seed_japji_emotions
This writes draft rows (review_status=draft, annotation_source=draft_mapping) to SQLite. It does not mark them as user-confirmed. Multiple emotion tags per Pauri are supported. The earlier reverse-by-emotion summary was inconsistent with the Pauri-by-Pauri table, so the Pauri-by-Pauri list is used as the source of truth for this prototype.