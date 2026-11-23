from fastapi.testclient import TestClient
from backend.main import app
client=TestClient(app)

def test_health_is_honest():
    r=client.get('/api/v1/health')
    assert r.status_code==200
    assert r.json()['source_corpus'] in ('empty','loaded_unreviewed')
    assert r.json()['llm_service']=='not_configured'

def test_invalid_emotion_rejected():
    r=client.post('/api/v1/assess',json={'energy_level':'low','emotional_state':'invalid'})
    assert r.status_code==422

def test_local_assessment_has_honest_status():
    r=client.post('/api/v1/assess',json={'energy_level':'low','emotional_state':'overwhelmed'})
    assert r.status_code==200
    assert r.json()['generation_status']=='not_configured'
