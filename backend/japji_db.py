"""Local SQLite storage for the Japji Sahib Pauri corpus and reviewed emotion tags.

This is intentionally separate from the existing Sri Guru Granth Sahib `scriptures`
 table: Japji Pauri numbers are not Ang numbers.
"""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from .local_db import db_path

EMOTIONS = {'grateful', 'at_peace', 'overwhelmed', 'heavy_sad', 'frustrated', 'lost'}

SCHEMA = '''
CREATE TABLE IF NOT EXISTS japji_pauris (
    pauri_number INTEGER PRIMARY KEY CHECK (pauri_number BETWEEN 1 AND 38),
    transliteration TEXT NOT NULL,
    english_translation TEXT NOT NULL,
    combined_text TEXT NOT NULL,
    source_file TEXT NOT NULL,
    pdf_page_start INTEGER,
    pdf_page_end INTEGER,
    original_gurmukhi TEXT,
    extraction_status TEXT NOT NULL DEFAULT 'needs_review',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS japji_salok (
    id TEXT PRIMARY KEY CHECK (id = 'concluding_salok'),
    transliteration TEXT NOT NULL,
    english_translation TEXT NOT NULL,
    combined_text TEXT NOT NULL,
    source_file TEXT NOT NULL,
    pdf_page_start INTEGER,
    pdf_page_end INTEGER,
    extraction_status TEXT NOT NULL DEFAULT 'needs_review',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS japji_emotion_map (
    pauri_number INTEGER NOT NULL REFERENCES japji_pauris(pauri_number) ON DELETE CASCADE,
    emotion TEXT NOT NULL CHECK (emotion IN ('grateful','at_peace','overwhelmed','heavy_sad','frustrated','lost')),
    mapping_type TEXT NOT NULL DEFAULT 'secondary' CHECK (mapping_type IN ('primary','secondary')),
    annotation_source TEXT NOT NULL DEFAULT 'pending_user_review',
    review_status TEXT NOT NULL DEFAULT 'draft' CHECK (review_status IN ('draft','user_confirmed')),
    PRIMARY KEY (pauri_number, emotion)
);
'''

def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.executescript(SCHEMA)
    return con

def import_pauris(json_path: str | Path) -> int:
    payload = json.loads(Path(json_path).read_text(encoding='utf-8'))
    pauris = payload.get('pauris', [])
    if len(pauris) != 38:
        raise ValueError(f'Expected 38 Pauris; found {len(pauris)}')
    expected = list(range(1, 39))
    actual = [int(p['pauri_number']) for p in pauris]
    if actual != expected:
        raise ValueError('Pauri numbers must be sequential from 1 through 38')
    con = connect()
    try:
        for p in pauris:
            transliteration = str(p.get('transliteration') or '').strip()
            translation = str(p.get('english_translation') or '').strip()
            if not transliteration or not translation:
                raise ValueError(f'Pauri {p["pauri_number"]} has missing text')
            combined = transliteration + '\n' + translation
            con.execute('''INSERT INTO japji_pauris
                (pauri_number, transliteration, english_translation, combined_text,
                 source_file, pdf_page_start, pdf_page_end, original_gurmukhi, extraction_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pauri_number) DO UPDATE SET
                  transliteration=excluded.transliteration,
                  english_translation=excluded.english_translation,
                  combined_text=excluded.combined_text,
                  source_file=excluded.source_file,
                  pdf_page_start=excluded.pdf_page_start,
                  pdf_page_end=excluded.pdf_page_end,
                  original_gurmukhi=excluded.original_gurmukhi,
                  extraction_status=excluded.extraction_status,
                  updated_at=CURRENT_TIMESTAMP''',
                (int(p['pauri_number']), transliteration, translation, combined,
                 p.get('source_file', 'Japji-Sahib-GRE.pdf'), p.get('pdf_page_start'),
                 p.get('pdf_page_end'), p.get('original_gurmukhi'),
                 p.get('extraction_status', 'needs_review')))
        salok = payload.get('concluding_salok') or {}
        salok_translit = str(salok.get('transliteration') or '').strip()
        salok_translation = str(salok.get('english_translation') or '').strip()
        if salok_translit and salok_translation:
            con.execute('''INSERT INTO japji_salok
                (id, transliteration, english_translation, combined_text, source_file,
                 pdf_page_start, pdf_page_end, extraction_status)
                VALUES ('concluding_salok', ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET transliteration=excluded.transliteration,
                  english_translation=excluded.english_translation, combined_text=excluded.combined_text,
                  source_file=excluded.source_file, pdf_page_start=excluded.pdf_page_start,
                  pdf_page_end=excluded.pdf_page_end, extraction_status=excluded.extraction_status,
                  updated_at=CURRENT_TIMESTAMP''',
                (salok_translit, salok_translation, salok_translit + '\n' + salok_translation,
                 payload.get('source', {}).get('file', 'Japji-Sahib-GRE.pdf'),
                 salok.get('pdf_page_start'), salok.get('pdf_page_end'),
                 salok.get('extraction_status', 'needs_review')))
        con.commit()
        return len(pauris)
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def list_pauris():
    con = connect()
    try:
        rows = con.execute('''SELECT p.*, GROUP_CONCAT(m.emotion) AS emotions
            FROM japji_pauris p LEFT JOIN japji_emotion_map m USING(pauri_number)
            GROUP BY p.pauri_number ORDER BY p.pauri_number''').fetchall()
        return [dict(r) | {'emotions': (r['emotions'].split(',') if r['emotions'] else [])} for r in rows]
    finally:
        con.close()

def get_pauri(number: int):
    con = connect()
    try:
        row = con.execute('SELECT * FROM japji_pauris WHERE pauri_number=?', (number,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result['emotions'] = [r['emotion'] for r in con.execute(
            'SELECT emotion FROM japji_emotion_map WHERE pauri_number=? ORDER BY mapping_type, emotion', (number,))]
        return result
    finally:
        con.close()

def get_salok():
    con = connect()
    try:
        row = con.execute("SELECT * FROM japji_salok WHERE id='concluding_salok'").fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def replace_emotion_mappings(mapping: dict[int, list[str]], *, confirmed: bool = False) -> int:
    """Replace mappings only when explicitly called with user-reviewed classifications."""
    for pauri, emotions in mapping.items():
        if not 1 <= int(pauri) <= 38:
            raise ValueError(f'Invalid Pauri number: {pauri}')
        unknown = set(emotions) - EMOTIONS
        if unknown:
            raise ValueError(f'Unknown emotions: {sorted(unknown)}')
    con = connect()
    try:
        con.execute('DELETE FROM japji_emotion_map')
        count = 0
        for pauri, emotions in mapping.items():
            for emotion in dict.fromkeys(emotions):
                con.execute('''INSERT INTO japji_emotion_map
                    (pauri_number, emotion, mapping_type, annotation_source, review_status)
                    VALUES (?, ?, 'secondary', ?, ?)''',
                    (int(pauri), emotion, 'user_reviewed_mapping' if confirmed else 'draft_mapping',
                     'user_confirmed' if confirmed else 'draft'))
                count += 1
        con.commit()
        return count
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
