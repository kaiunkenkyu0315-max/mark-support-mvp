from fastapi.testclient import TestClient

from app.main import APP_NAME, app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_ok_json():
    response = client.get("/health")
    assert response.json() == {"status": "ok"}


def test_index_returns_200():
    response = client.get("/")
    assert response.status_code == 200


def test_index_contains_app_name():
    response = client.get("/")
    assert APP_NAME in response.text
