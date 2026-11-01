from fastapi.testclient import TestClient

from ocean_backend.api.main import app


def test_ai_command_endpoint_accepts_supported_request():
    with TestClient(app) as client:
        response = client.post("/ai/command", json={
            "text": "show temperature volume",
            "dataset_id": "io-model-4d",
        })
    assert response.status_code == 200
    body = response.json()
    assert body["command"]["command"] == "SHOW_VOLUME"
    assert body["result"]["action"] == "show_volume"


def test_ai_command_endpoint_rejects_empty_request():
    with TestClient(app) as client:
        response = client.post("/ai/command", json={"text": ""})
    assert response.status_code == 400


def test_ai_command_endpoint_rejects_unknown_request():
    with TestClient(app) as client:
        response = client.post("/ai/command", json={"text": "make me a sandwich"})
    assert response.status_code == 400
