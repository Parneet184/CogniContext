"""ChromaDB + multilingual E5 embeddings for Japji Sahib Pauri-level retrieval."""
from __future__ import annotations
import os
from pathlib import Path

from .japji_db import list_pauris, get_salok

import random

DEFAULT_MODEL = 'intfloat/multilingual-e5-small'  # 384 dimensions; compact multilingual model
DEFAULT_CHROMA_PATH = Path(__file__).resolve().parent / 'data' / 'chroma_japji'
COLLECTION_NAME = 'japji_sahib_pauris'


def _dependencies():
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError('Vector dependencies missing. Run: pip install -r backend/requirements.txt') from exc
    return chromadb, SentenceTransformer


def build_collection(model_name: str | None = None, persist_path: str | None = None):
    chromadb, SentenceTransformer = _dependencies()
    model_name = model_name or os.getenv('COGNICONTEXT_EMBEDDING_MODEL', DEFAULT_MODEL)
    persist_path = persist_path or os.getenv('COGNICONTEXT_CHROMA_PATH', str(DEFAULT_CHROMA_PATH))
    model = SentenceTransformer(model_name)
    client = chromadb.PersistentClient(path=persist_path)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={'hnsw:space': 'cosine', 'embedding_model': model_name}
    )
    rows = list_pauris()
    if len(rows) != 38:
        raise RuntimeError(f'Expected 38 Pauris in SQLite before vector ingestion; found {len(rows)}')
    ids = [f'pauri_{r["pauri_number"]:02d}' for r in rows]
    documents = [f'passage: {r["combined_text"]}' for r in rows]
    metadatas = [{
    'pauri_number': r['pauri_number'],
    'section_type': 'pauri',
    'source': 'Japji Sahib',
    'pdf_page_start': r['pdf_page_start'] or 0,
    'pdf_page_end': r['pdf_page_end'] or 0,
    'extraction_status': r['extraction_status'],
    'original_gurmukhi': r.get('original_gurmukhi') or ''
} for r in rows]
    salok = get_salok()
    if salok:
        ids.append('concluding_salok')
        documents.append(f'passage: {salok["combined_text"]}')
        metadatas.append({
    'pauri_number': 0,
    'section_type': 'salok',
    'source': 'Japji Sahib',
    'pdf_page_start': salok['pdf_page_start'] or 0,
    'pdf_page_end': salok['pdf_page_end'] or 0,
    'extraction_status': salok['extraction_status'],
    'original_gurmukhi': salok.get('original_gurmukhi') or ''
})
    embeddings = model.encode(documents, normalize_embeddings=True).tolist()
    # Upsert makes re-running ingestion safe and repeatable.
    collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
    return {'collection': COLLECTION_NAME, 'count': collection.count(), 'model': model_name,
            'embedding_dimensions': len(embeddings[0]) if embeddings else 0, 'persist_path': persist_path}


def search_pauris(query: str, n_results: int = 5, emotion: str | None = None):
    chromadb, SentenceTransformer = _dependencies()
    model_name = os.getenv('COGNICONTEXT_EMBEDDING_MODEL', DEFAULT_MODEL)
    persist_path = os.getenv('COGNICONTEXT_CHROMA_PATH', str(DEFAULT_CHROMA_PATH))
    model = SentenceTransformer(model_name)
    client = chromadb.PersistentClient(path=persist_path)
    collection = client.get_collection(COLLECTION_NAME)
    query_vector = model.encode([f'query: {query}'], normalize_embeddings=True).tolist()
    # Emotion tags remain in SQLite and are applied after vector retrieval.
    fetch_n = 39 if emotion else min(max(n_results, 1), 39)
    result = collection.query(query_embeddings=query_vector, n_results=fetch_n)
    hits=[]
    for i, sid in enumerate(result['ids'][0]):
        meta = result['metadatas'][0][i]
        hits.append({
    'id': sid,
    'pauri_number': meta['pauri_number'],
    'section_type': meta.get('section_type', 'pauri'),
    'distance': result['distances'][0][i],
    'document': result['documents'][0][i].removeprefix('passage: '),
    'original_gurmukhi': meta.get('original_gurmukhi', '')
                  })
    if emotion:
        from .japji_db import connect

        con = connect()
        try:
            allowed = {
                r[0] for r in con.execute(
                    'SELECT pauri_number FROM japji_emotion_map WHERE emotion=?',
                    (emotion,)
                )
            }
        finally:
            con.close()

        hits = [
            h for h in hits
            if h['pauri_number'] in allowed
        ]

        # Randomly select from ALL emotion-matched candidates,
# not just the top-ranked candidates.
        hits = random.sample(
                hits,
                k=min(n_results, len(hits))
                        )

# Keep the selected results ordered by relevance.
        hits.sort(key=lambda h: h['distance'])
    else:
        hits = hits[:n_results]

    return hits
