import json
from pathlib import Path
from backend import japji_db

DATA = Path(__file__).resolve().parents[1] / 'backend' / 'data_templates' / 'japji_pauris_extracted.json'

def test_imports_38_pauris_and_salok(tmp_path, monkeypatch):
    monkeypatch.setenv('COGNICONTEXT_DB', str(tmp_path / 'test.sqlite3'))
    assert japji_db.import_pauris(DATA) == 38
    rows = japji_db.list_pauris()
    assert len(rows) == 38
    assert rows[0]['pauri_number'] == 1
    assert rows[-1]['pauri_number'] == 38
    assert 'sochai soch' in rows[0]['transliteration']
    assert 'By thinking' in rows[0]['english_translation']
    assert japji_db.get_salok()['id'] == 'concluding_salok'

def test_emotion_mapping_is_empty_until_reviewed(tmp_path, monkeypatch):
    monkeypatch.setenv('COGNICONTEXT_DB', str(tmp_path / 'test.sqlite3'))
    japji_db.import_pauris(DATA)
    assert japji_db.get_pauri(1)['emotions'] == []
    count = japji_db.replace_emotion_mappings({1: ['lost', 'overwhelmed']}, confirmed=False)
    assert count == 2
    assert set(japji_db.get_pauri(1)['emotions']) == {'lost', 'overwhelmed'}
