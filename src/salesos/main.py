import platform
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware

from salesos.config import ALLOWED_HOSTS, Settings
from salesos.db import create_db_engine
from salesos.security import form_token, require_csrf, security_middleware

WEB_DIR = Path(__file__).parent / "web"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = create_db_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    # Sem /docs: a interface do Swagger carrega scripts externos, bloqueados pela CSP.
    app = FastAPI(
        title="SalesOS",
        version=version("salesos"),
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
        dependencies=[Depends(require_csrf)],
    )
    app.state.settings = settings
    app.state.engine = engine
    templates = Jinja2Templates(directory=WEB_DIR / "templates")
    templates.env.globals["csrf_token"] = form_token
    app.state.templates = templates

    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    app.middleware("http")(security_middleware)
    # Adicionado por último = executado primeiro: barra hosts estranhos (DNS rebinding).
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

    @app.get("/health")
    def health() -> dict[str, str]:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "app_version": app.version,
                "python_version": platform.python_version(),
                # IPv6 precisa de colchetes para virar um endereço utilizável no navegador.
                "address": f"[{settings.host}]:{settings.port}"
                if ":" in settings.host
                else f"{settings.host}:{settings.port}",
            },
        )

    return app


def run() -> None:
    """Ponto de entrada `salesos`: sobe o servidor só em loopback."""
    settings = Settings()
    uvicorn.run("salesos.main:create_app", factory=True, host=settings.host, port=settings.port)
