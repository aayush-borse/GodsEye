from fastapi.testclient import TestClient

from ocean_backend.api.main import app


def test_ai_can_resolve_argo_observation_for_comparison():
    with TestClient(app) as client:
        response = client.post("/ai/command", json={
            "text": "compare temperature for argo 1902675",
            "dataset_id": "io-model-4d",
        })
    assert response.status_code == 200
    body = response.json()
    assert body["command"]["command"] == "COMPARE_MODEL_OBSERVATION"
    assert body["command"]["variable"] == "temperature"
    assert body["command"]["observation_id"] == "1902675"
    assert body["result"] is not None
