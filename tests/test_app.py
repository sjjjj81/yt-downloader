import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health(client):
    rv = client.get("/api/health")
    assert rv.status_code == 200
    assert rv.get_json() == {"status": "ok"}


def test_index(client):
    rv = client.get("/")
    assert rv.status_code == 200
    assert b"YouTube Downloader" in rv.data
