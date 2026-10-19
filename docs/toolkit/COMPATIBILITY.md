# Compatibilidade e adaptações para Python

O Toolkit (revisão `790a895`) foi escrito para **Next.js + TypeScript + Drizzle/PostgreSQL + Zod + Pino + Vitest + ESLint**. O próprio prompt 12 orienta: *"Other stacks use native tools; do not install ESLint in a codebase without JavaScript merely to satisfy a checklist."* O SalesOS mantém a stack Python. Esta tabela registra como cada convenção foi traduzida.

## 1. Mapeamento de convenções

| Convenção do Toolkit | Intenção | Equivalente no SalesOS | Situação |
|---|---|---|---|
| Next.js / App Router | Servidor web e UI | FastAPI + Jinja2 (renderização no servidor) | Planejado (Fase 01) |
| Drizzle ORM + PostgreSQL | Persistência tipada e migrações versionadas | SQLAlchemy 2.x (`Mapped`) + Alembic + SQLite. PostgreSQL só numa migração futura. | Planejado |
| `db:generate` revisado antes de aplicar | Nunca migrar às cegas | `alembic revision --autogenerate` → revisar → `alembic upgrade head` só em banco autorizado. `alembic check` nos testes. | Planejado |
| Zod (env, entradas, respostas) | Validação em tempo de execução | Pydantic v2 + `pydantic-settings` | Planejado |
| Pino com redação | Logs estruturados sem segredos | `logging` da biblioteca padrão, com filtro de campos sensíveis | Planejado |
| `server-only`, nada em `NEXT_PUBLIC_*` | Segredos fora do cliente | Segredos só em `.env` (ignorado no Git); templates nunca recebem configuração sensível | Planejado |
| Vitest | Testes | pytest + HTTPX (`TestClient`), SQLite temporário por teste | Planejado |
| ESLint / Biome + regras locais | Qualidade estática | Ruff (lint + formatação) + mypy `--strict` | Planejado |
| Limite de 350 linhas por arquivo (regra ESLint) | Arquivos coesos | Convenção no `AGENTS.md`. Se for preciso, um teste pytest simples mede o tamanho dos arquivos de `src/`. | Convenção ativa |
| Typed lint (`no-floating-promises`) | Correção assíncrona | mypy strict; Ruff com regras `ASYNC` se houver código assíncrono | Planejado |
| `npm run verify` | Comando único de verificação | `ruff check` → `ruff format --check` → `mypy` → `pytest` | Planejado |
| `docs/setup.md` (revisão e evidências) | Rastreabilidade | `docs/toolkit/*` agora; `docs/setup.md` na Fase 01 com link para cá | Ativo |
| Skills Vercel / shadcn / next-dev-loop | Especialização em Next/React | Não aplicável. Para UI: skills de design disponíveis no cliente, escolhidas por fase. | Não aplicável |
| Avaliação da harness (fixture em Node) | Testar o comportamento do agente | A fixture é em JS e roda com Node, de forma independente da stack do produto. Fica usável como está. | Ativo (USAGE §6) |

## 2. Restrições do SalesOS que o Toolkit não pode alterar

- Uso local, aplicação só em `127.0.0.1`. Sem Docker, sem IA no produto, sem integrações externas de negócio.
- Nenhum plugin, skill ou template autoriza commit, push, publicação, instalação global ou uso de dados reais.
- O Toolkit não justifica trocar a stack. Adoção de Next.js, Drizzle ou ESLint está fora de questão.

## 3. Windows

| Item | Requisito no Windows | Situação |
|---|---|---|
| Claude Code | Instalador nativo; a ferramenta Bash usa o Git Bash | Verificar na sua máquina |
| Superpowers | `bash` acessível: o hook `run-hook.cmd` procura o Git for Windows | Não testado no Windows |
| Ponytail | `node` no PATH | Não testado no Windows |
| Context7 | Só rede (MCP HTTP) | Não testado; bloqueado no container |
| Caminhos com espaços | Os comandos documentados usam caminhos relativos ao projeto. Use aspas se o caminho do projeto tiver espaços. | — |
| PowerShell × Bash | Os comandos de `docs/toolkit/` funcionam nos dois, exceto onde indicado. `sha256sum` só existe no Git Bash; a alternativa em PowerShell está em INSTALLATION §5. | — |
| Fim de linha | Para manter a verificação SHA-256 da cópia válida, o Git não pode converter os finais de linha dela (ver INSTALLATION §6) | Ação recomendada |

## 4. Python 3.15.0 como alvo

Verificado em 2026-10-19, pelo PyPI:

- Há wheels `cp315-win_amd64` publicadas para as dependências binárias essenciais: `pydantic-core` 2.50.1, `SQLAlchemy` 2.1.5, `greenlet` 3.5.6 e `MarkupSafe` 3.0.4.
- `pydantic-settings`, `uvicorn`, `fastapi`, `alembic`, `jinja2` e `httpx` são Python puro.

**Ainda não verificado:**

- O lançamento final do 3.15.0. O `python.org` está bloqueado neste container, e o `uv` 0.11.32 local só lista a `3.15.0b4`. Confirme na sua máquina com `py -3.15 --version` ou `uv python list`.
- O suporte do Ruff e do mypy a `target-version`/`python_version` 3.15. Isso fica para a Fase 01.

Se algum desses itens falhar, a Fase 01 usará a versão estável compatível mais recente e registrará o motivo.
