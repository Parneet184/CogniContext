import pytest
from fastapi.testclient import TestClient
from backend import local_db
from backend.main import app

@pytest.fixture
def local(monkeypatch,tmp_path):
    monkeypatch.setenv('COGNICONTEXT_DB',str(tmp_path/'test.sqlite3'))
    local_db.initialize()
    return TestClient(app)

def test_empty_database(local):
    h=local.get('/api/v1/health').json()
    assert h['source_corpus']=='empty'
    assert h['scripture_records']==0
    assert local.get('/api/v1/scriptures?emotion=lost').json()['results']==[]

def test_import_and_retrieve(local):
    n=local_db.import_records([{
        'external_id':'example1','ang_number':1,'original_gurmukhi':'TEST GURMUKHI PLACEHOLDER NOT SCRIPTURE',
        'english_translation':'Test record, not a translation', 'themes':['guidance','discernment']
    }],edition_id='test',title='Test corpus',source_url='https://example.com/test',rights_note='Test only; synthetic')
    assert n==1
    r=local.post('/api/v1/assess',json={'energy_level':'low','emotional_state':'lost'})
    assert r.status_code==200
    hit=r.json()['sources'][0]
    assert hit['review_status']=='unreviewed'
    assert local.get('/api/v1/scriptures/'+hit['id']).status_code==200
    assert local.get('/api/v1/scriptures?emotion=grateful').json()['results']==[]
    assert local.get('/api/v1/scriptures?reviewed_only=true').json()['results']==[]
    assert local_db.import_records([{'external_id':'example1','ang_number':1,'original_gurmukhi':'TEST'}],edition_id='test',title='Test corpus',source_url='https://example.com/test',rights_note='Test only')==0

def test_invalid_import_rolls_back(local):
    with pytest.raises(ValueError):
        local_db.import_records([{'external_id':'a','ang_number':2000,'original_gurmukhi':'Bad'}],edition_id='test',title='test',source_url='https://example.com',rights_note='testing')
    assert local.get('/api/v1/health').json()['scripture_records']==0
