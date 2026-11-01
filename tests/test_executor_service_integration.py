from fastapi.testclient import TestClient

from ocean_backend.api.main import app


def test_ai_command_routes_to_validated_executor_action():
    with TestClient(app) as client:
        response = client.post("/ai/command", json={
            "text": "show temperature volume",
            "dataset_id": "io-model-4d",
        })
    assert response.status_code == 200
    body = response.json()
    assert body["command"]["command"] == "SHOW_VOLUME"
    assert body["result"]["action"] == "show_volume"
