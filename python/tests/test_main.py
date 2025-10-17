from fastapi.testclient import TestClient
from app.main import app

def test_read_root():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_health_check():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_get_time():
    client = TestClient(app)
    response = client.get("/time")
    assert response.status_code == 200
    # Check if the response has a 'time' key with a string value
    assert "time" in response.json()
    assert isinstance(response.json()["time"], str)
