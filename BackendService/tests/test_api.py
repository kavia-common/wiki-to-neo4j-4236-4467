from fastapi.testclient import TestClient
from src.api.main import app
from src.api.auth import create_access_token

client = TestClient(app)

def get_auth_header():
    token = create_access_token("test-user")
    return {"Authorization": f"Bearer {token}"}

def test_health():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["message"] == "Healthy"

def test_submit_requires_auth():
    r = client.post("/api/v1/input/submit", json={"input_type": "topic", "value": "Python"})
    assert r.status_code in (401, 403)

def test_submit_job_flow():
    r = client.post("/api/v1/input/submit", headers=get_auth_header(), json={"input_type": "topic", "value": "Python"})
    assert r.status_code == 200
    data = r.json()
    job_id = data["job_id"]
    assert data["status"] in ("pending", "processing")

    # fetch status
    s = client.get(f"/api/v1/status/{job_id}", headers=get_auth_header())
    assert s.status_code == 200
