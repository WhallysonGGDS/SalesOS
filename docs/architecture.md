# Arquitetura

Este documento registra só o que está **implementado** (Fases 01 e 02). Planos ficam marcados como planos.

## Estrutura

```
src/salesos/
  config.py     Settings (pydantic-settings, prefixo SALESOS_, .env); host só loopback;
                segredo ≥ 32 caracteres; ALLOWED_HOSTS fixo; backup_dir
  db.py         Base declarativa, create_db_engine (PRAGMAs, permissões), get_session,
                controle de FK nas migrações, sqlite_file e restringir
  security.py   Cabeçalhos de segurança (inclui Cache-Control: no-store), cookie, CSRF e
                limite do corpo das requisições
  main.py       create_app(settings) e run(): servidor e os comandos backup/restore/recover
  backup.py     Backup verificado e verificação de um backup (integridade, SHA-256,
                revisão, estrutura)
  restore.py    Restauração com diário de estados e recover
  dinheiro.py   Centavos inteiros: centavos() lê só formatos pt-BR (0 a 10¹²), reais() formata
  formularios.py  Auxiliares das rotas HTML: campos permitidos, validação com mensagens
                por campo, 303 e datas locais (compartilhado pelas features)
  lock.py       Trava cooperativa entre processos (flock no Linux, msvcrt no Windows)
  features/clientes/
    models.py     Cliente, Contato, Interacao
    normalize.py  e-mail, chave de busca, escape de LIKE
    schemas.py    Entrada validada (Pydantic, extra="forbid")
    service.py    Regras: CRUD, busca, eventos, anonimização (uma unidade de trabalho por função)
    router.py     Rotas finas e páginas de erro sem dados pessoais
  features/oportunidades/  (Fase 03)
    models.py     Oportunidade e Movimentacao; CHECKs de etapa, motivo, fechamento e valor
    periodo.py    Dias locais → intervalo UTC (regras de fuso do sistema para cada data)
    schemas.py    Entrada validada: valor pt-BR, datas AAAA-MM-DD, motivo só na perda, filtros
    service.py    Regras R1–R10; operação, movimentação e evento no mesmo commit
    router.py     Rotas finas; 422 no campo para RegraViolada e filtros inválidos
  web/templates base.html, index.html, clientes/*.html, oportunidades/*.html (Jinja2, sem JavaScript)
  web/static    app.css
migrations/     Alembic; 0001 = linha de base vazia; 0002 = clientes, contatos, interações;
                0003 = oportunidades e movimentações (Fase 03)
tests/          pytest; cada teste roda numa pasta temporária, sem .env real e sem data/
```

## Fluxo de uma requisição

1. `TrustedHostMiddleware`: só `127.0.0.1`, `localhost` e `[::1]` (lista fixa, não configurável); outro `Host` → 400 (protege contra DNS rebinding).
2. `LimiteCorpo` (Fase 02.1, item S2): lê o corpo até `LIMITE_CORPO` (256 KiB; o maior formulário legítimo tem cerca de 65 KB) e o entrega inteiro à aplicação; acima disso → 413 com texto simples, com ou sem `Content-Length`; fica fora do `security_middleware` para que um cliente que desiste no meio do envio não vire erro 500. Protege a leitura do formulário pelo CSRF e pelas rotas.
3. `security_middleware`: garante o cookie `salesos_csrf` (aleatório, HttpOnly, SameSite=Strict) e aplica os cabeçalhos de segurança.
4. `require_csrf` (dependência global): em POST/PUT/PATCH/DELETE exige `csrf_token` no formulário ou `X-CSRF-Token` igual a `HMAC-SHA256(segredo, cookie)`; senão → 403. Vale só para rotas FastAPI (`@app.get/post…`, routers). Sub-apps montadas com `app.mount`, rotas Starlette puras e websockets **não** passam por ela: toda rota nova deve ser uma rota FastAPI.
5. Rota: lê só os campos permitidos do formulário, valida com o schema, chama o serviço e responde 303 depois de um POST bem-sucedido; validação inválida → 422 com a mensagem no campo; registro inexistente → 404; cliente anonimizado → 409.

Rotas: `GET /`, `GET /health`, `GET /clientes` (busca, arquivados, paginação de 20), `GET /clientes/novo` (formulário) e `POST /clientes` (cria), `GET /clientes/{id}`, `GET /clientes/{id}/editar` e `POST /clientes/{id}`, `POST /clientes/{id}/arquivar|desarquivar|anonimizar|contatos|interacoes`, `GET /contatos/{id}/editar`, `POST /contatos/{id}` e `/contatos/{id}/remover`. Não existe rota para editar ou excluir interações.

Rotas do funil (Fase 03): `GET /oportunidades` (colunas por etapa, até 20 cada; filtros `situacao`, `de`, `ate`), `GET /oportunidades/lista` (20 por página; também `etapa`), `GET /oportunidades/nova?cliente_id=` e `POST /oportunidades`, `GET /oportunidades/{id}`, `GET /oportunidades/{id}/editar` e `POST /oportunidades/{id}`, `POST /oportunidades/{id}/etapa`. Só a criação e `/etapa` gravam movimentações; nenhuma rota as edita ou apaga. Ids fora do inteiro de 64 bits → 422 (em `/clientes/{id}` isso ainda gera 500: pendência registrada).

## Banco de dados

- SQLite em `data/salesos.db` (fora do Git). A pasta é criada quando o engine é criado; se o SalesOS a cria, ela fica `0700` (POSIX).
- Em toda conexão: permissão `0600` do arquivo (POSIX), `foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000`, `secure_delete=ON`. Erros do SQLAlchemy não levam os valores dos parâmetros (`hide_parameters`).
- Tabelas da Fase 02: ver ADR `0004-modelo-clientes.md`.
- Tabelas da Fase 03 (`oportunidades`, `movimentacoes`): ver ADR `0006-funil.md`. Depois da `0003`, backups da `0002` são recusados pelo `restore` (bloqueio B1 antes de dados reais).
- Alembic com `render_as_batch=True` (SQLite não altera colunas em lugar). Durante a migração, a FK fica **desligada** naquela conexão (`foreign_keys_disabled`), porque o batch recria tabelas e, com FK ligada, o `DROP` apagaria linhas filhas em cascata. Antes do commit, `PRAGMA foreign_key_check` precisa estar vazio; se não estiver, a migração inteira é desfeita (`transactional_ddl=True`). Migrações nunca rodam no import nem em requisições: `uv run alembic upgrade head`.
- Cada migração gerada passa automaticamente por `ruff check --fix` e `ruff format` (`post_write_hooks` do `alembic.ini`).

## Backup, restauração e recuperação

Comandos `uv run salesos backup | restore <arquivo> [--aceitar-reintroducao] | recover`. O servidor (`uv run salesos`) segura a trava `data/salesos.lock` enquanto roda e não inicia com uma restauração pendente. Desenho, estados e limites: ADR `0005-backup-e-restauracao.md`. Uso no Windows: `docs/onboarding.md`.

## Planejado (não implementado)

- CPF, CNPJ e telefone: aguardam fonte oficial e aprovação (D6, D11, D12).
- Oportunidades, tarefas, propostas, relatórios (Fases 03–06).
- Autenticação e multiusuário: fora da primeira versão; os pontos de extensão serão registrados em ADR.

Decisões: `docs/decisions/`.
