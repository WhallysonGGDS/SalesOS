from fastapi.testclient import TestClient
from pydantic import SecretStr

from salesos.config import Settings
from salesos.main import create_app


def test_health_reports_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_home_page_renders(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert '<html lang="pt-BR">' in html
    assert "<title>SalesOS</title>" in html
    assert "SQLite" in html
    assert "<script" not in html


def test_static_stylesheet_is_served(client: TestClient) -> None:
    response = client.get("/static/app.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")


def test_home_shows_usable_ipv6_address() -> None:
    settings = Settings(host="::1", secret_key=SecretStr("x" * 32))
    with TestClient(create_app(settings), base_url="http://[::1]") as client:
        assert "[::1]:8000" in client.get("/").text
