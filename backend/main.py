"""SQLite-backed scripture search API. Not an LLM or verified RAG service."""
import os
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from . import local_db, japji_db

app = FastAPI(title='CogniContext API', version='0.2.0')
origins = os.getenv('CORS_ORIGINS','http://localhost:8000,http://127.0.0.1:8000').split(',')
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST'],allow_headers=['Content-Type'])
Emotion = Literal['grateful','at_peace','overwhelmed','heavy_sad','frustrated','lost']
class Assessment(BaseModel):
    energy_level: Literal['low','high'] | None = None
    emotional_state: Emotion | None = None
    consent_to_save: bool = False
class JapjiSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    limit: int = Field(default=5, ge=1, le=20)
    emotion: Emotion | None = None

class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=4000)
    emotional_state: Emotion | None = None
    energy_level: Literal['low', 'high'] | None = None
    active_source_ids: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=10)
    
# Temporary conversation storage (resets when backend restarts)
SESSION_STORE = {}

@app.get('/api/v1/health')
def health():
    try: data=local_db.stats()
    except Exception: raise HTTPException(503,'Local database unavailable')
    japji_count = len(japji_db.list_pauris())
    return {'backend':'healthy','database':'sqlite_ready','source_corpus':'loaded_unreviewed' if data['scripture_records'] else 'empty',
            'japji_pauri_records': japji_count, 'embedding_service':'configured_in_code_not_ingested','llm_service':'not_configured','mode':'local_retrieval_only',**data}

@app.get('/api/v1/themes')
def themes(): return local_db.THEMES

@app.get('/api/v1/japji/pauris')
def japji_pauris():
    return {'results': japji_db.list_pauris(), 'count': 38, 'corpus': 'Japji Sahib'}

@app.get('/api/v1/japji/salok')
def japji_salok():
    result = japji_db.get_salok()
    if result is None:
        raise HTTPException(404, 'Concluding Salok not imported yet')
    return result

@app.get('/api/v1/japji/pauris/{pauri_number}')
def japji_pauri(pauri_number: int):
    if not 1 <= pauri_number <= 38:
        raise HTTPException(404, 'Pauri number must be between 1 and 38')
    result = japji_db.get_pauri(pauri_number)
    if result is None:
        raise HTTPException(404, 'Pauri not imported yet')
    return result


@app.post('/api/v1/japji/search')
def japji_search(data: JapjiSearchRequest):
    try:
        from .vector_store import search_pauris
        hits = search_pauris(data.query, data.limit, data.emotion)

        enriched_hits = []

        for hit in hits:
            number = hit['pauri_number']

            # Fetch the complete scripture record from SQLite.
            if number == 0:
                scripture = japji_db.get_salok()
            else:
                scripture = japji_db.get_pauri(number)

            if scripture is None:
                continue

            enriched_hits.append({
                **hit,
                'original_gurmukhi': scripture.get('original_gurmukhi') or '',
                'transliteration': scripture.get('transliteration') or '',
                'english_translation': scripture.get('english_translation') or '',
                'section_type': 'salok' if number == 0 else 'pauri'
            })

    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    except Exception as exc:
        raise HTTPException(
            503,
            f'Japji vector collection is not ready: {exc}'
        )

    return {
        'query': data.query,
        'emotion': data.emotion,
        'results': enriched_hits,
        'result_count': len(enriched_hits),
        'retrieval_method': 'ChromaDB cosine similarity + optional SQLite emotion filter'
    }


@app.get('/api/v1/scriptures')
def scriptures(q: str = Query('',max_length=250), emotion: Emotion | None = None, limit: int = Query(10,ge=1,le=50), reviewed_only: bool = False):
    return {'results':local_db.search(q,emotion,limit,reviewed_only),'retrieval_method':'sqlite_lexical_and_theme_filter','grounding_status':'not_independently_verified'}

@app.get('/api/v1/scriptures/{source_id}')
def scripture(source_id:str):
    source=local_db.get_source(source_id)
    if source is None: raise HTTPException(404,'No such source')
    return source

@app.post('/api/v1/assess')
def assess(data:Assessment):
    if not data.emotional_state:
        raise HTTPException(422,'Select a state for theme-filtered retrieval or use GET /api/v1/scriptures')
    hits=local_db.search(emotion=data.emotional_state,limit=5)
    return {'energy_level':data.energy_level,'emotional_state':data.emotional_state,
            'mapped_themes':local_db.THEMES[data.emotional_state],'sources':hits,'retrieval_status':'results_found' if hits else 'no_annotated_matches',
            'generation_status':'not_configured','note':'No state or session was saved. These records are unreviewed until separately validated.'}


@app.post('/api/v1/chat')
def chat(data: ChatRequest):

    session_id = data.session_id

    # Check whether this is an existing conversation
    is_follow_up = session_id in SESSION_STORE

    if is_follow_up:
        session = SESSION_STORE[session_id]
        enriched_hits = session["sources"]
        history = session["history"]

    else:
        # Retrieve passages only for a new conversation
        try:
            from .vector_store import search_pauris

            hits = search_pauris(
                query=data.message,
                n_results=data.limit,
                emotion=data.emotional_state
            )

            enriched_hits = []

            for hit in hits:
                number = hit['pauri_number']

                if number == 0:
                    scripture = japji_db.get_salok()
                else:
                    scripture = japji_db.get_pauri(number)

                if scripture is None:
                    continue

                enriched_hits.append({
                    **hit,
                    'original_gurmukhi':
                        scripture.get('original_gurmukhi') or '',
                    'transliteration':
                        scripture.get('transliteration') or '',
                    'english_translation':
                        scripture.get('english_translation') or '',
                    'section_type':
                        'salok' if number == 0 else 'pauri'
                })

        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f'Japji Sahib retrieval failed: {exc}'
            )

        history = []

        if not enriched_hits:
            return {
                'session_id': session_id,
                'answer': "I couldn't find a sufficiently relevant Japji Sahib passage. Please try expressing your thoughts differently.",
                'sources': [],
                'retrieval_status': 'no_results',
                'generation_status': 'not_attempted'
            }

        locked_sources = enriched_hits[:1]

        SESSION_STORE[session_id] = {
            "sources": locked_sources,
            "history": history,
            "emotional_state": data.emotional_state,
            "energy_level": data.energy_level
        }

        enriched_hits = locked_sources

    # Prepare conversation context
    conversation_context = "\n".join(
        f"{item['role']}: {item['content']}"
        for item in history[-10:]
    )

    contextual_message = f"""
Conversation type: {"Follow-up" if is_follow_up else "Initial reflection"}

Emotional state: {
    SESSION_STORE[session_id]['emotional_state'] or 'Not specified'
}
Energy level: {
    SESSION_STORE[session_id]['energy_level'] or 'Not specified'
}

Previous conversation:
{conversation_context}

Current user message:
{data.message}
"""

    # Generate response using the SAME retrieved passages
    try:
        from .groq_service import generate_response

        answer = generate_response(
    user_message=contextual_message,
    retrieved_passages=enriched_hits[:1],
    is_follow_up=is_follow_up
)

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f'Groq response generation failed: {exc}'
        )

    # Save conversation history
    history.append({
        "role": "user",
        "content": data.message
    })

    history.append({
        "role": "assistant",
        "content": answer
    })

    # Keep only the latest 10 messages
    SESSION_STORE[session_id]["history"] = history[-10:]

    return {
        'session_id': session_id,
        'answer': answer,
        'sources': enriched_hits,
        'retrieval_status': 'success',
        'generation_status': 'success',
        'conversation_mode': (
            'follow_up' if is_follow_up else 'initial'
        ),
        'retrieval_method':
            'ChromaDB cosine similarity + SQLite emotion filter',
        'generation_model': 'Groq'
    }


@app.get('/api/v1/sessions/{session_id}',status_code=503)
def session(session_id:str): raise HTTPException(503,'Session storage is not configured')
@app.get('/api/v1/sessions/{session_id}/messages',status_code=503)
def messages(session_id:str): raise HTTPException(503,'Session storage is not configured')
@app.delete('/api/v1/sessions/{session_id}',status_code=503)
def delete_session(session_id:str): raise HTTPException(503,'Session storage is not configured')
@app.post('/api/v1/feedback',status_code=503)
def feedback(): raise HTTPException(503,'Feedback storage is not configured')
