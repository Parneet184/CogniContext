# CogniContext Database v1 — getting started

## What this package provides

- An **automatically created, local SQLite database** (`backend/data/cognicontext.sqlite3`). No signup, password, PostgreSQL, or cloud service necessary.
- Relational tables: `source_editions`, `scriptures`, `scripture_themes`, and `assessment_theme_map`.
- Seeded *taxonomy only* for the six emotional choices, with three retrieval themes each.
- A provenance-aware CSV/JSON/JSONL scripture importer, search API, and tests.
- **No scripture passages are preloaded**, because we cannot safely claim accuracy or permission to redistribute a full external corpus. The colorful frontend continues to display its *clearly labeled illustrative demo passages* rather than inventing live results.
- The API does NOT provide vector search, independent verification, or LLM-generated responses yet.

## 1. Start the API

From the folder containing `backend` and `frontend`:

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --port 8001
```

Open http://127.0.0.1:8001/docs to try the API. Calling `/api/v1/health` automatically creates the database file.

## 2. Obtain permitted source records

Use a source edition with documented provenance and permission to reuse each text component, **especially English translations**. If an API permits access but forbids bulk republication, follow its terms rather than scraping it. Keep exact Ang references and source IDs; have imported texts and thematic annotations reviewed against the edition before treating them as authentic or verified.

Sources to evaluate (NOT preapproved/automatically copied):
- https://github.com/opengranth/open-granth
- https://api.banidb.com/v2/api-docs/

The database records the dataset's title, source URL, and rights note. Per-record `translation_source` and `source_url` can also be provided. Source records start in `unreviewed` status, regardless of where they came from.

## 3. Make a CSV

Copy `data_templates/import_template.csv` and add rows with correctly quoted fields. Required fields: `external_id`, `ang_number` (1 to 1430), and `original_gurmukhi`. Other metadata fields can be empty. Use `|` separators for multiple optional themes such as `steadiness|acceptance`.

A row cannot automatically be classified as verified just because the import succeeds. For meaningful emotion filtering, add human-reviewed themes and record their annotation provenance before production use. The provided importer's theme labels are explicitly unreviewed.

## 4. Import

Run this from the project root, substituting actual paths and provenance:

```bash
python -m backend.import_scriptures \
  --file path/to/permitted_scriptures.csv \
  --edition-id my-authorized-edition-v1 \
  --title "My authorized source edition" \
  --source-url "https://example.org/edition" \
  --rights-note "Describe the actual rights and permission here"
```

Use `--update` to replace existing edition records by `external_id`; updated records revert to `unreviewed` and lose their previous theme annotations if replaced. Duplicate imports are ignored by default. A failed import rolls back its changes.

To store the database elsewhere, set `COGNICONTEXT_DB` to an absolute path before starting the API/import command.

## 5. Try the API

- `GET /api/v1/health` — actual corpus and database readiness.
- `GET /api/v1/themes` — emotional categories and mapped themes.
- `GET /api/v1/scriptures?q=...&limit=10` — basic substring search.
- `GET /api/v1/scriptures?emotion=overwhelmed` — theme-annotated retrieval, **not semantic/vector search**.
- `GET /api/v1/scriptures?reviewed_only=true` — only manually reviewed sources (initially none).
- `GET /api/v1/scriptures/{id}` — individual record and provenance.
- `POST /api/v1/assess` — obtains theme-matched sources; saves no assessment.

Example assessment payload:

```json
{"energy_level":"low","emotional_state":"overwhelmed","consent_to_save":false}
```

If the corpus is empty or unannotated, retrieval returns no sources; this is expected. `POST /api/v1/chat` still returns HTTP 503 until a grounded generation service is implemented.

## 6. Tests

```bash
python -m pytest tests/test_local_db.py -q
```

## Roadmap

1. Obtain and review licensed/authenticated Gurbani and translations.
2. Add source-by-source metadata/verse-boundary checks, annotation review workflow, and review audit logs.
3. Connect frontend to the live search API with a clearly marked local retrieval mode.
4. Implement PostgreSQL+pgvector embeddings and evaluated Punjabi/English retrieval.
5. Add LLM generation only after citation checks and robust safety controls are in place.

**Privacy:** Do not store individual emotional assessments unless explicitly opted in. The current retrieval API does not persist them. The SQLite API is intended for local use, not internet-facing multiuser deployment.
