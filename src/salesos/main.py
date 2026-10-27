import argparse
import platform
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, nullcontext
from importlib.metadata import version
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware

from salesos import expurgo, paginas_erro
from salesos.backup import BackupInvalido, criar_backup
from salesos.config import ALLOWED_HOSTS, Settings
from salesos.db import create_db_engine, sqlite_file
from salesos.features.clientes import router as clientes
from salesos.features.oportunidades import router as oportunidades
from salesos.features.tarefas import router as tarefas
from salesos.lock import Travado, caminho_trava, trava
from salesos.migracao_backup import migrar_backup
from salesos.restore import (
    FECHE_OS_PROGRAMAS,
    RestauracaoRecusada,
    aquietar,
    controle_pendente,
    recuperar,
    restaurar,
    voltar_wal,
)
from salesos.security import LimiteCorpo, form_token, require_csrf, security_middleware

WEB_DIR = Path(__file__).parent / "web"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = create_db_engine(settings.database_url)
    db = _arquivo(settings.database_url)

    # A trava vale para qualquer servidor, inclusive `uvicorn` direto (E2, ADR 0005): com ela,
    # restore, recover e `alembic upgrade` são recusados enquanto a aplicação estiver de pé.
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            with trava(caminho_trava(db)) if db else nullcontext():
                if db and controle_pendente(db):
                    raise RuntimeError(PENDENTE)
                yield
        finally:
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
    clientes.configurar(app)
    oportunidades.configurar(app)
    tarefas.configurar(app)
    paginas_erro.configurar(app)
    app.middleware("http")(security_middleware)
    # Fora do BaseHTTPMiddleware: cliente que desiste no meio do envio não vira erro 500.
    app.add_middleware(LimiteCorpo)
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


def _arquivo(database_url: str) -> Path | None:
    """Banco em arquivo (com trava); `None` para bancos que não são arquivos SQLite."""
    try:
        return sqlite_file(database_url)
    except ValueError:
        return None


AVISO_EXPURGO = (
    "Isso apaga definitivamente esses clientes e tudo o que é deles (interações, oportunidades, "
    "histórico de etapas, tarefas e histórico das tarefas). Os indicadores históricos mudam. "
    "Backups anteriores continuam com os dados até a rotação (docs/privacy.md)."
)


EXPURGO_OCUPADO = (
    "Outro programa está com o banco aberto (por exemplo, o DB Browser). "
    "Feche-o e rode o comando de novo. Nada foi apagado."
)
EXPURGO_INCOMPLETO = (
    "O expurgo físico NÃO terminou: um programa abriu o banco durante o expurgo, e o conteúdo "
    "apagado pode continuar no arquivo -wal. Feche os outros programas e rode "
    "`uv run salesos expurgar` de novo para terminar."
)


def _expurgar(db: Path, database_url: str) -> None:
    """Expurgo manual (P1): mostra a abrangência e só apaga com a confirmação exata."""
    with trava(caminho_trava(db)):  # servidor, restore e migração ficam de fora
        if controle_pendente(db):
            raise SystemExit(PENDENTE)
        # Como no restore: qualquer outra conexão aberta (até ociosa) impediria esvaziar o -wal
        # depois do expurgo. Um checkpoint só não basta: com o -wal vazio, ele não acusa leitores.
        try:
            aquietar(db)
        except RestauracaoRecusada as erro:
            # Só bloqueio é "outro programa"; outro erro do SQLite mantém o diagnóstico real.
            if str(erro) == FECHE_OS_PROGRAMAS:
                raise SystemExit(EXPURGO_OCUPADO) from erro
            texto = str(erro).replace("Nada foi alterado.", "Nada foi apagado.")
            raise SystemExit(texto) from erro
        finally:
            voltar_wal(db)
        engine = create_db_engine(database_url)
        try:
            with Session(engine) as session:
                escopo = expurgo.abrangencia(session)
                if not escopo:
                    print(
                        "Nenhum cliente anonimizado há 12 meses ou mais. Nada a expurgar. "
                        "O arquivo -wal está vazio."
                    )
                    return
                print(f"Expurgo de {len(escopo)} cliente(s) anonimizado(s) há 12 meses ou mais:")
                for item in escopo:
                    quando = f"{item.anonimizado_em:%d/%m/%Y}"
                    linhas = expurgo.descrever(item.linhas)
                    print(f"  Cliente #{item.cliente_id} (anonimizado em {quando}): {linhas}")
                print(AVISO_EXPURGO)
                pedido = f"EXPURGAR {len(escopo)}"
                try:
                    resposta = input(f"Para confirmar, digite {pedido}: ")
                except EOFError:
                    resposta = ""
                if resposta.strip() != pedido:
                    raise SystemExit("Confirmação diferente. Nada foi apagado.")
                resultado = expurgo.expurgar(session, [item.cliente_id for item in escopo])
                linhas = expurgo.descrever(resultado.linhas)
                if not resultado.fisico_completo:
                    print(f"Registros apagados do banco: {linhas}.")
                    raise SystemExit(EXPURGO_INCOMPLETO)
                print(f"Expurgo concluído: {linhas}.")
        finally:
            engine.dispose()


PENDENTE = "Há uma restauração inacabada. Rode `uv run salesos recover` antes de continuar."


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="salesos", description="CRM local da WE TECH.")
    comandos = parser.add_subparsers(dest="comando")
    comandos.add_parser("backup", help="cria um backup verificado (SHA-256 e integridade)")
    restore = comandos.add_parser("restore", help="restaura um backup (servidor desligado)")
    restore.add_argument("arquivo", type=Path)
    restore.add_argument(
        "--aceitar-reintroducao",
        action="store_true",
        help="aceita um backup anterior a uma anonimização (os dados voltam)",
    )
    restore.add_argument(
        "--migrar",
        action="store_true",
        help="migra uma cópia de um backup de versão anterior antes de restaurar",
    )
    comandos.add_parser("recover", help="termina com segurança uma restauração interrompida")
    comandos.add_parser(
        "expurgar", help="apaga clientes anonimizados há 12 meses ou mais (pede confirmação)"
    )
    return parser.parse_args()


def run() -> None:
    """Ponto de entrada `salesos`: servidor (só loopback), backup, restore e recover."""
    args = _argumentos()
    settings = Settings()
    try:
        db = sqlite_file(settings.database_url)
        if args.comando == "backup":
            if not db.exists():
                raise SystemExit(f"Banco não encontrado: {db}")
            if controle_pendente(db):
                raise SystemExit(PENDENTE)
            print(f"Backup criado: {criar_backup(db, settings.backup_dir)}")
        elif args.comando == "restore":
            arquivo = args.arquivo
            if args.migrar:
                if controle_pendente(db):
                    raise SystemExit(PENDENTE)
                arquivo = migrar_backup(arquivo, settings.backup_dir)
                if arquivo != args.arquivo:
                    print(f"Backup migrado para a versão atual: {arquivo}")
            pre = restaurar(db, arquivo, settings.backup_dir, args.aceitar_reintroducao)
            print(f"Banco restaurado. O anterior foi preservado em: {pre}")
        elif args.comando == "expurgar":
            if not db.exists():
                raise SystemExit(f"Banco não encontrado: {db}")
            _expurgar(db, settings.database_url)
        elif args.comando == "recover":
            relatorio = recuperar(db, settings.backup_dir)
            if relatorio.estado is None:
                print("Nenhuma restauração pendente.")
            else:
                print(
                    f"Restauração interrompida em '{relatorio.estado}' foi concluída com segurança."
                )
            for residuo in relatorio.residuos:
                print(f"Arquivo temporário residual (apague se não precisar): {residuo}")
        else:
            # Só para dar a mensagem antes de subir: quem segura a trava é a aplicação ao iniciar
            # (segurá-la aqui também faria a aplicação, no mesmo processo, recusar a si mesma).
            with trava(caminho_trava(db)):
                pass
            if controle_pendente(db):
                raise SystemExit(PENDENTE)
            uvicorn.run(
                "salesos.main:create_app",
                factory=True,
                host=settings.host,
                port=settings.port,
                access_log=False,  # a URL da busca (?q=) traria nomes e e-mails para o log
            )
    # OSError: arquivo inexistente, disco cheio ou arquivo em uso; o banco já foi protegido.
    # RuntimeError: recover sem banco nem cópia; sqlite3.Error: banco ilegível ou não migrado.
    except (
        Travado,
        RestauracaoRecusada,
        BackupInvalido,
        ValueError,
        OSError,
        RuntimeError,
        sqlite3.Error,
    ) as erro:
        raise SystemExit(str(erro)) from erro
    except SQLAlchemyError as erro:
        # Só o tipo: o texto traria o SQL. Banco sem as tabelas: rode `alembic upgrade head`.
        tipo = type(getattr(erro, "orig", None) or erro).__name__
        raise SystemExit(f"Erro do banco ({tipo}). O banco está migrado?") from erro
