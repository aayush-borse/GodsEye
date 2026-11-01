from fastapi.testclient import TestClient

from ocean_backend.api.main import app


def test_ai_command_returns_structured_action():
    with TestClient(app) as client:
        response = client.post("/ai/command", json={
            "text": "show temperature volume",
            "dataset_id": "io-model-4d",
        })
    assert response.status_code == 200
    body = response.json()
    assert body["command"]["variable"] == "temperature"
    assert body["result"]["status"] == "ready"
