# Japji Sahib RAG implementation (MVP)

## What is implemented

- Extracted 38 numbered Pauris and the concluding Salok from `data_templates/Japji-Sahib-GRE.pdf`.
- Structured Romanized Punjabi transliteration and the supplied English translation separately.
- Added a dedicated SQLite schema for 38 Pauris, the concluding Salok, and emotion tags. This is deliberately separate from the existing `scriptures` table because Pauri numbers are not Sri Guru Granth Sahib Ang numbers.
- Added a ChromaDB vector-store module using `intfloat/multilingual-e5-small` (384 dimensions).
- Added API routes for listing/reading Pauris and semantic vector search.

## Important source limitation

The PDF's embedded Gurmukhi font mapping does not extract as valid Unicode text. The imported `original_gurmukhi` value is therefore NULL. Do not invent or infer the Gurmukhi text. Add it only from a separately verified, appropriately authorized source. The transliteration and English translation are retained as extracted and still require human proofreading against the intended edition.

The supplied English translation's rights/provenance have not been independently verified. Keep the source PDF and translation provenance attached to any public release.

## Setup (run from the project root)

```bash
python -m pip install -r backend/requirements.txt
python -m backend.import_japji
```

The first vector ingestion downloads the embedding model if it is not already cached:

```bash
python -c "from backend.vector_store import build_collection; print(build_collection())"
```

## API

Start the API:

```bash
uvicorn backend.main:app --reload --port 8001
```

- `GET /api/v1/japji/pauris` — list all imported Pauris.
- `GET /api/v1/japji/pauris/1` — get one Pauri.
- `GET /api/v1/japji/salok` — get the concluding Salok.
- `POST /api/v1/japji/search` — vector search; optional emotion filter.

Example request:

```json
{
  "query": "How can I accept things that are outside my control?",
  "limit": 5,
  "emotion": "overwhelmed"
}
```

## Emotion mapping

The `japji_emotion_map` table is intentionally empty until the project's owner reviews and confirms the proposed emotion-to-Pauri associations. Do not treat generated or illustrative mappings as established truth.

## Model choice

`intfloat/multilingual-e5-small` is used for a compact 384-dimensional multilingual embedding model. It is a practical MVP choice; evaluate retrieval quality on representative queries before calling the system production-ready. The E5 convention is used: prefix corpus text with `passage:` and user queries with `query:`.
