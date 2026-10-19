# Arquitetura

Este documento registra só o que está **implementado**. Planos ficam marcados como planos.

## Estrutura (Fase 01)

```
src/salesos/
  config.py     Settings (pydantic-settings, prefixo SALESOS_, .env); host só loopback;
                segredo ≥ 32 caracteres; ALLOWED_HOSTS fixo
  db.py         Base declarativa, create_db_engine (PRAGMAs) e o controle de FK nas migrações
  security.py   Cabeçalhos de segurança, cookie e verificação CSRF
  main.py       create_app(settings) e run(); rotas / e /health
  web/templates base.html, index.html (Jinja2, sem JavaScript)
  web/static    app.css
migrations/     Alembic; 0001 = linha de base vazia
tests/          pytest; cada teste roda numa pasta temporária, sem .env real
```

## Fluxo de uma requisição

1. `TrustedHostMiddleware`: só `127.0.0.1`, `localhost` e `[::1]` (lista fixa, não configurável); outro `Host` → 400 (protege contra DNS rebinding).
2. `security_middleware`: garante o cookie `salesos_csrf` (aleatório, HttpOnly, SameSite=Strict) e aplica os cabeçalhos de segurança.
3. `require_csrf` (dependência global): em POST/PUT/PATCH/DELETE exige `csrf_token` no formulário ou `X-CSRF-Token` igual a `HMAC-SHA256(segredo, cookie)`; senão → 403. Vale só para rotas FastAPI (`@app.get/post…`, routers). Sub-apps montadas com `app.mount`, rotas Starlette puras e websockets **não** passam por ela: toda rota nova deve ser uma rota FastAPI.
4. Rota. Hoje: `GET /` (página base) e `GET /health` (consulta `SELECT 1` no banco).

## Banco de dados

- SQLite em `data/salesos.db` (fora do Git). A pasta é criada quando o engine é criado (ao iniciar a aplicação ou as migrações).
- Em toda conexão: `foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000`.
- Alembic com `render_as_batch=True` (SQLite não altera colunas em lugar). Durante a migração, a FK fica **desligada** naquela conexão (`foreign_keys_disabled`), porque o batch recria tabelas e, com FK ligada, o `DROP` apagaria linhas filhas em cascata. Antes do commit, `PRAGMA foreign_key_check` precisa estar vazio; se não estiver, a migração inteira é desfeita (`transactional_ddl=True`: a versão não avança e nada fica meio aplicado). Ao sair, a FK é religada. Migrações nunca rodam no import nem em requisições: `uv run alembic upgrade head`.
- Cada migração gerada passa automaticamente por `ruff check --fix` e `ruff format` (`post_write_hooks` do `alembic.ini`).
- Nenhuma tabela de negócio ainda: a migração `0001` é a linha de base.

## Planejado (não implementado)

- Camadas por domínio a partir da Fase 02: `features/<domínio>/{router,service,schemas,models}.py`.
- Sessões SQLAlchemy por requisição, auditoria e histórico de mudanças, documentos privados, backup e restauração (Fases 02–07).
- Autenticação e multiusuário: fora da primeira versão; os pontos de extensão serão registrados em ADR.

Decisões: `docs/decisions/`.
