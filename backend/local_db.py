"""SQLite scripture catalogue. No sample verses are inserted as authentic scripture."""
import csv
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent / 'data' / 'cognicontext.sqlite3'
THEMES = {
    'grateful': ('gratitude', 'humility', 'remembrance'),
    'at_peace': ('balance', 'contentment', 'contemplation'),
    'overwhelmed': ('steadiness', 'acceptance', 'resilience'),
    'heavy_sad': ('compassion', 'impermanence', 'hope'),
    'frustrated': ('patience', 'humility', 'self-reflection'),
    'lost': ('purpose', 'guidance', 'discernment'),
}
SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS source_editions (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, publisher TEXT,
  source_url TEXT NOT NULL, rights_note TEXT NOT NULL, imported_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS scriptures (
  id TEXT PRIMARY KEY, edition_id TEXT NOT NULL REFERENCES source_editions(id),
  external_id TEXT NOT NULL, ang_number INTEGER NOT NULL CHECK(ang_number BETWEEN 1 AND 1430),
  shabad_id TEXT, raag TEXT, author_attribution TEXT,
  original_gurmukhi TEXT NOT NULL, transliteration TEXT, english_translation TEXT,
  translation_source TEXT, canonical_reference TEXT, source_url TEXT,
  review_status TEXT NOT NULL DEFAULT 'unreviewed',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(edition_id, external_id)
);
CREATE TABLE IF NOT EXISTS scripture_themes (
  scripture_id TEXT NOT NULL REFERENCES scriptures(id) ON DELETE CASCADE,
  theme TEXT NOT NULL, annotation_source TEXT NOT NULL,
  review_status TEXT NOT NULL DEFAULT 'unreviewed',
  PRIMARY KEY(scripture_id, theme)
);
CREATE INDEX IF NOT EXISTS idx_scripture_ang ON scriptures(ang_number);
CREATE INDEX IF NOT EXISTS idx_scripture_theme ON scripture_themes(theme);
CREATE TABLE IF NOT EXISTS assessment_theme_map (
  emotion TEXT NOT NULL, theme TEXT NOT NULL, rank INTEGER NOT NULL,
  PRIMARY KEY (emotion, theme)
);
'''

def db_path():
    return Path(os.environ.get('COGNICONTEXT_DB', str(DEFAULT_PATH))).expanduser()

@contextmanager
def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def initialize():
    with connect() as con:
        con.executescript(SCHEMA)
        for emotion, themes in THEMES.items():
            for rank, theme in enumerate(themes):
                con.execute('INSERT OR IGNORE INTO assessment_theme_map VALUES (?,?,?)', (emotion, theme, rank))

def stats():
    initialize()
    with connect() as con:
        return {'scripture_records': con.execute('SELECT count(*) FROM scriptures').fetchone()[0],
                'editions': con.execute('SELECT count(*) FROM source_editions').fetchone()[0],
                'reviewed_records': con.execute("SELECT count(*) FROM scriptures WHERE review_status='reviewed'").fetchone()[0]}

def search(query='', emotion=None, limit=10, reviewed_only=False):
    initialize()
    limit = min(max(int(limit), 1), 50)
    where = ['1=1']
    args = []
    if reviewed_only:
        where.append("s.review_status='reviewed'")
    if query:
        where.append('(s.original_gurmukhi LIKE ? OR s.english_translation LIKE ? OR s.raag LIKE ? OR s.author_attribution LIKE ? OR s.canonical_reference LIKE ?)')
        args += [f'%{query}%'] * 5
    if emotion:
        if emotion not in THEMES: raise ValueError('Unsupported emotion')
        where.append('EXISTS (SELECT 1 FROM scripture_themes t JOIN assessment_theme_map m ON t.theme=m.theme WHERE t.scripture_id=s.id AND m.emotion=?)')
        args.append(emotion)
    sql = '''SELECT s.*,e.title AS edition_title,e.rights_note AS rights_note,
          (SELECT group_concat(theme, ', ') FROM scripture_themes t WHERE t.scripture_id=s.id) AS themes
          FROM scriptures s JOIN source_editions e ON e.id=s.edition_id WHERE ''' + ' AND '.join(where) + ' ORDER BY s.ang_number,s.external_id LIMIT ?'
    with connect() as con:
        return [dict(x) for x in con.execute(sql, (*args, limit)).fetchall()]

def get_source(source_id):
    initialize()
    with connect() as con:
        r = con.execute('SELECT s.*,e.title AS edition_title,e.rights_note FROM scriptures s JOIN source_editions e ON e.id=s.edition_id WHERE s.id=?',(source_id,)).fetchone()
        return dict(r) if r else None

REQUIRED = ('external_id', 'ang_number', 'original_gurmukhi')

def import_records(records, *, edition_id, title, source_url, rights_note, publisher='', allow_update=False):
    if not all([edition_id, title, source_url, rights_note]):
        raise ValueError('Edition id, title, source URL, and rights note are mandatory')
    if not source_url.startswith(('https://', 'http://')):
        raise ValueError('Source URL must start with https:// or http://')
    initialize()
    imported = 0
    with connect() as con:
        old = con.execute('SELECT * FROM source_editions WHERE id=?',(edition_id,)).fetchone()
        if old and (old['title'] != title or old['source_url'] != source_url):
            raise ValueError('Edition ID already assigned to another title/source')
        con.execute('INSERT OR IGNORE INTO source_editions(id,title,publisher,source_url,rights_note) VALUES(?,?,?,?,?)', (edition_id,title,publisher,source_url,rights_note))
        for record in records:
            for field in REQUIRED:
                if not str(record.get(field, '')).strip(): raise ValueError(f'Missing {field} in a scripture record')
            try: ang = int(record['ang_number'])
            except (ValueError, TypeError): raise ValueError('ang_number must be an integer')
            if not 1 <= ang <= 1430: raise ValueError('ang_number out of range')
            external_id = str(record['external_id']).strip()
            existing = con.execute('SELECT id FROM scriptures WHERE edition_id=? AND external_id=?',(edition_id,external_id)).fetchone()
            if existing and not allow_update: continue
            sid = existing['id'] if existing else str(uuid.uuid4())
            cols = ('shabad_id','raag','author_attribution','transliteration','english_translation','translation_source','canonical_reference','source_url')
            values = [str(record.get(c) or '') for c in cols]
            # Import never marks content verified automatically.
            con.execute('''INSERT INTO scriptures(id,edition_id,external_id,ang_number,original_gurmukhi,shabad_id,raag,author_attribution,transliteration,english_translation,translation_source,canonical_reference,source_url,review_status)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?, 'unreviewed')
              ON CONFLICT(edition_id,external_id) DO UPDATE SET ang_number=excluded.ang_number,original_gurmukhi=excluded.original_gurmukhi,
              shabad_id=excluded.shabad_id,raag=excluded.raag,author_attribution=excluded.author_attribution,transliteration=excluded.transliteration,
              english_translation=excluded.english_translation,translation_source=excluded.translation_source,canonical_reference=excluded.canonical_reference,
              source_url=excluded.source_url,review_status='unreviewed' ''', (sid,edition_id,external_id,ang,str(record['original_gurmukhi']).strip(),*values))
            if existing and allow_update:
                con.execute('DELETE FROM scripture_themes WHERE scripture_id=?',(sid,))
            themes = record.get('themes') or []
            if isinstance(themes,str): themes = [x.strip() for x in themes.split('|') if x.strip()]
            for theme in themes:
                con.execute('INSERT OR IGNORE INTO scripture_themes(scripture_id,theme,annotation_source) VALUES(?,?,?)', (sid,theme,'dataset-import:unreviewed'))
            imported += 1
    return imported

def read_dataset(path):
    path = Path(path)
    if path.suffix.lower() == '.csv':
        with path.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
    if path.suffix.lower() in ('.jsonl','.ndjson'):
        with path.open(encoding='utf-8') as f: return [json.loads(line) for line in f if line.strip()]
    if path.suffix.lower() == '.json':
        obj = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(obj,list): raise ValueError('JSON dataset must be an array')
        return obj
    raise ValueError('Use CSV, JSON, or JSONL')
