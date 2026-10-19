# 0001 — Stack e Python 3.15

**Status:** aceita (Fase 01, 2026-10-19)

**Contexto:** a stack aprovada na Fase 00 tinha Python 3.15 como alvo, condicionado à compatibilidade.

**Decisão:** Python 3.15.0 (`requires-python >= 3.15`), uv com `uv.lock`, FastAPI, SQLAlchemy 2.1, Alembic, SQLite, Pydantic Settings, Jinja2; pytest, HTTPX, Ruff e mypy strict.

**Evidência:**
- Tag `v3.15.0` no CPython e PEP 790 ("3.15.0 final: 2026-10-09").
- Instalado com `uv python install 3.15.0` (CPython 3.15.0 com GIL, SQLite 3.53.1).
- Resolução e instalação de todas as dependências; 46 testes, Ruff e mypy limpos nesse interpretador.

**Consequências:**
- Todas as dependências binárias têm wheels `cp315` para Windows x64.
- O Starlette avisa sobre a troca `httpx` → `httpx2` (pendente de decisão).
- PostgreSQL só numa migração futura.
