from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text

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


def test_request_session_is_usable_and_closed_after_request(app: FastAPI) -> None:
    from sqlalchemy.orm import Session

    from salesos.db import get_session

    sessions: list[Session] = []

    @app.get("/_sessao")
    def _rota(session: Annotated[Session, Depends(get_session)]) -> dict[str, int]:
        sessions.append(session)
        return {"um": int(session.execute(text("SELECT 1")).scalar_one())}

    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.get("/_sessao").json() == {"um": 1}
    assert len(sessions) == 1
    assert not sessions[0].in_transaction()
