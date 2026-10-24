# Arquitetura

Este documento registra só o que está **implementado** (Fases 01 e 02). Planos ficam marcados como planos.

## Estrutura

```
src/salesos/
  config.py     Settings (pydantic-settings, prefixo SALESOS_, .env); host só loopback;
                segredo ≥ 32 caracteres; ALLOWED_HOSTS fixo; backup_dir
  db.py         Base declarativa, create_db_engine (PRAGMAs, permissões), get_session,
                controle de FK nas migrações, sqlite_file e restringir
  security.py   Cabeçalhos de segurança (inclui Cache-Control: no-store), cookie e CSRF
  main.py       create_app(settings) e run(): servidor e os comandos backup/restore/recover
  backup.py     Backup verificado e verificação de um backup (integridade, SHA-256,
                revisão, estrutura)
  restore.py    Restauração com diário de estados e recover
  lock.py       Trava cooperativa entre processos (flock no Linux, msvcrt no Windows)
  features/clientes/
    models.py     Cliente, Contato, Interacao
    normalize.py  e-mail, chave de busca, escape de LIKE
    schemas.py    Entrada validada (Pydantic, extra="forbid")
    service.py    Regras: CRUD, busca, eventos, anonimização (uma unidade de trabalho por função)
    router.py     Rotas finas e páginas de erro sem dados pessoais
  web/templates base.html, index.html, clientes/*.html (Jinja2, sem JavaScript)
  web/static    app.css
migrations/     Alembic; 0001 = linha de base vazia; 0002 = clientes, contatos, interações
tests/          pytest; cada teste roda numa pasta temporária, sem .env real e sem data/
```

## Fluxo de uma requisição

1. `TrustedHostMiddleware`: só `127.0.0.1`, `localhost` e `[::1]` (lista fixa, não configurável); outro `Host` → 400 (protege contra DNS rebinding).
2. `security_middleware`: garante o cookie `salesos_csrf` (aleatório, HttpOnly, SameSite=Strict) e aplica os cabeçalhos de segurança.
3. `require_csrf` (dependência global): em POST/PUT/PATCH/DELETE exige `csrf_token` no formulário ou `X-CSRF-Token` igual a `HMAC-SHA256(segredo, cookie)`; senão → 403. Vale só para rotas FastAPI (`@app.get/post…`, routers). Sub-apps montadas com `app.mount`, rotas Starlette puras e websockets **não** passam por ela: toda rota nova deve ser uma rota FastAPI.
4. Rota: lê só os campos permitidos do formulário, valida com o schema, chama o serviço e responde 303 depois de um POST bem-sucedido; validação inválida → 422 com a mensagem no campo; registro inexistente → 404; cliente anonimizado → 409.

Rotas: `GET /`, `GET /health`, `GET /clientes` (busca, arquivados, paginação de 20), `GET /clientes/novo` (formulário) e `POST /clientes` (cria), `GET /clientes/{id}`, `GET /clientes/{id}/editar` e `POST /clientes/{id}`, `POST /clientes/{id}/arquivar|desarquivar|anonimizar|contatos|interacoes`, `GET /contatos/{id}/editar`, `POST /contatos/{id}` e `/contatos/{id}/remover`. Não existe rota para editar ou excluir interações.

## Banco de dados

- SQLite em `data/salesos.db` (fora do Git). A pasta é criada quando o engine é criado; se o SalesOS a cria, ela fica `0700` (POSIX).
- Em toda conexão: permissão `0600` do arquivo (POSIX), `foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000`, `secure_delete=ON`. Erros do SQLAlchemy não levam os valores dos parâmetros (`hide_parameters`).
- Tabelas da Fase 02: ver ADR `0004-modelo-clientes.md`.
- Alembic com `render_as_batch=True` (SQLite não altera colunas em lugar). Durante a migração, a FK fica **desligada** naquela conexão (`foreign_keys_disabled`), porque o batch recria tabelas e, com FK ligada, o `DROP` apagaria linhas filhas em cascata. Antes do commit, `PRAGMA foreign_key_check` precisa estar vazio; se não estiver, a migração inteira é desfeita (`transactional_ddl=True`). Migrações nunca rodam no import nem em requisições: `uv run alembic upgrade head`.
- Cada migração gerada passa automaticamente por `ruff check --fix` e `ruff format` (`post_write_hooks` do `alembic.ini`).

## Backup, restauração e recuperação

Comandos `uv run salesos backup | restore <arquivo> [--aceitar-reintroducao] | recover`. O servidor (`uv run salesos`) segura a trava `data/salesos.lock` enquanto roda e não inicia com uma restauração pendente. Desenho, estados e limites: ADR `0005-backup-e-restauracao.md`. Uso no Windows: `docs/onboarding.md`.

## Planejado (não implementado)

- CPF, CNPJ e telefone: aguardam fonte oficial e aprovação (D6, D11, D12).
- Oportunidades, tarefas, propostas, relatórios (Fases 03–06).
- Autenticação e multiusuário: fora da primeira versão; os pontos de extensão serão registrados em ADR.

Decisões: `docs/decisions/`.
