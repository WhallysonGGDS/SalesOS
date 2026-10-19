# Fase 01 — Fundação técnica: plano de implementação

> Criado com `superpowers:writing-plans`. Execução nativa (o agente principal implementa) e revisão independente no fim. Adaptação aprovada pelo usuário: **um único commit ao final da fase**, em vez de commits por tarefa.

**Objetivo:** uma aplicação FastAPI vazia, mas segura, testada e documentada, sobre a qual as fases de CRM se apoiam.

**Arquitetura:**
- Pacote `src/salesos` com fábrica de aplicação.
- Configuração via `pydantic-settings` (prefixo `SALESOS_`).
- SQLAlchemy 2 + SQLite (WAL, `foreign_keys`) e Alembic com linha de base vazia.
- Jinja2 renderizado no servidor, sem JavaScript.
- Proteções: TrustedHost, cabeçalhos de segurança e CSRF por double-submit assinado (HMAC, biblioteca padrão).

**Stack:** Python 3.15.0, uv, FastAPI, Starlette, Uvicorn, SQLAlchemy, Alembic, Pydantic Settings, Jinja2, python-multipart; pytest, HTTPX, Ruff, mypy.

**Especificação:** aprovação da Fase 01 (conversa de 2026-10-19) e `AGENTS.md`.

## Restrições globais

- `requires-python = ">=3.15"`. Nada de downgrade silencioso.
- O servidor escuta só em loopback (`127.0.0.1`, `::1`, `localhost`). Outro host é rejeitado na configuração.
- Sem funcionalidades de CRM, sem Docker, sem IA, sem serviços externos, sem JavaScript na interface.
- Dados reais só em `/data/` (ignorado pelo Git). Testes usam `tmp_path`.
- Arquivos com menos de 350 linhas. Ruff, `mypy --strict` e pytest limpos.

## Pontos de atenção (cobertos por testes)

1. `SALESOS_HOST=0.0.0.0` → erro de configuração, nunca expor a aplicação na rede.
2. Primeiro POST sem cookie CSRF → 403, sem erro 500.
3. Pasta `data/` inexistente → criada ao criar o engine.
4. Header `Host` falsificado (DNS rebinding) → 400.
5. Token CSRF de outro segredo ou adulterado → 403.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `pyproject.toml`, `uv.lock`, `.python-version` | Dependências, ferramentas, entrada `salesos` |
| `src/salesos/config.py` | `Settings`, `LOOPBACK_HOSTS`, `ALLOWED_HOSTS` |
| `src/salesos/db.py` | `Base`, `create_db_engine(url) -> Engine` (PRAGMAs), `foreign_keys_disabled`, `check_foreign_keys` |
| `src/salesos/security.py` | `security_middleware`, `require_csrf` (dependência), `sign_token(secret, token) -> str` |
| `src/salesos/main.py` | `create_app(settings: Settings \| None = None) -> FastAPI`, rotas `/` e `/health`, `run()` |
| `src/salesos/web/templates/{base,index}.html`, `web/static/app.css` | Casca visual |
| `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/0001_linha_de_base.py` | Migrações |
| `tests/` | `conftest`, config, db, security, app, migrations |
| Documentação | `README.md`, `PRODUCT.md`, `docs/{architecture,onboarding,quality,setup,dependencies,phases}.md`, `docs/decisions/0001-0003`, `docs/toolkit/COMPATIBILITY.md` §4 |

## Tarefas

1. **Ambiente:** `uv init` manual em `pyproject.toml`; `uv sync` no 3.15.0; registrar versões.
2. **Configuração (TDD):** `test_config.py` (padrões, override por env, host não loopback rejeitado) → `config.py`.
3. **Banco (TDD):** `test_db.py` (`foreign_keys=1`, `journal_mode=wal`, FK aplicada de fato, pasta criada) → `db.py`.
4. **Segurança e aplicação (TDD):** `test_security.py` + `test_app.py` (`/health` 200; host inválido 400; cabeçalhos; cookie CSRF; POST sem token, com token errado e com token válido via formulário e via header) → `security.py`, `main.py`, templates.
5. **Migrações (TDD):** `test_migrations.py` (upgrade → `alembic_version` = `0001`; downgrade → vazio; `command.check` sem diferenças) → Alembic.
6. **Verificação completa:** `ruff check`, `ruff format --check`, `mypy`, `pytest`, servidor real + `curl`, navegador (Playwright), auditoria de dependências, varredura de segredos.
7. **Documentação e licenças;** revisão independente; correções; verificação de novo; commit e push únicos.
