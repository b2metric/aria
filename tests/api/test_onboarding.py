from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_register_invalid_data():
    response = client.post("/api/onboarding/register", json={
        "name": "Test",
        # Missing email and password
    })
    assert response.status_code == 422
