# Compatibilidade e adaptações para Python

O Toolkit (revisão `790a895`) foi escrito para **Next.js + TypeScript + Drizzle/PostgreSQL + Zod + Pino + Vitest + ESLint**. O próprio prompt 12 orienta: *"Other stacks use native tools; do not install ESLint in a codebase without JavaScript merely to satisfy a checklist."* O SalesOS mantém a stack Python. Esta tabela registra como cada convenção foi traduzida.

## 1. Mapeamento de convenções

| Convenção do Toolkit | Intenção | Equivalente no SalesOS | Situação |
|---|---|---|---|
| Next.js / App Router | Servidor web e UI | FastAPI + Jinja2 (renderização no servidor) | Implementado (Fase 01) |
| Drizzle ORM + PostgreSQL | Persistência tipada e migrações versionadas | SQLAlchemy 2.x (`Mapped`) + Alembic + SQLite. PostgreSQL só numa migração futura. | Implementado (Fase 01; sem tabelas ainda) |
| `db:generate` revisado antes de aplicar | Nunca migrar às cegas | `alembic revision --autogenerate` → revisar → `alembic upgrade head` só em banco autorizado. `alembic check` nos testes. | Implementado (Fase 01) |
| Zod (env, entradas, respostas) | Validação em tempo de execução | Pydantic v2 + `pydantic-settings` | Configuração implementada; validação de entradas a partir da Fase 02 |
| Pino com redação | Logs estruturados sem segredos | `logging` da biblioteca padrão, com filtro de campos sensíveis | Planejado |
| `server-only`, nada em `NEXT_PUBLIC_*` | Segredos fora do cliente | Segredos só em `.env` (ignorado no Git); templates nunca recebem configuração sensível | Implementado (Fase 01) |
| Vitest | Testes | pytest + HTTPX (`TestClient`), SQLite temporário por teste | Implementado (Fase 01) |
| ESLint / Biome + regras locais | Qualidade estática | Ruff (lint + formatação) + mypy `--strict` | Implementado (Fase 01) |
| Limite de 350 linhas por arquivo (regra ESLint) | Arquivos coesos | Convenção no `AGENTS.md`. Se for preciso, um teste pytest simples mede o tamanho dos arquivos de `src/`. | Convenção ativa |
| Typed lint (`no-floating-promises`) | Correção assíncrona | mypy strict; Ruff com regras `ASYNC` se houver código assíncrono | mypy strict ativo; regras `ASYNC` quando surgir código assíncrono relevante |
| `npm run verify` | Comando único de verificação | `ruff check` → `ruff format --check` → `mypy` → `pytest` | Implementado (README, `docs/quality.md`) |
| `docs/setup.md` (revisão e evidências) | Rastreabilidade | `docs/setup.md` (versões e evidências) + `docs/toolkit/*` | Ativo |
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

**Confirmado na Fase 01 (2026-10-19)** e registrado no ADR `docs/decisions/0001-stack-e-python.md`:

- O lançamento final existe: tag `v3.15.0` no repositório `python/cpython`, e a PEP 790 traz "3.15.0 final: 2026-10-09".
- No Cloud: `uv` atualizado para 0.13.1, `uv python install 3.15.0` → CPython 3.15.0 (com GIL, SQLite 3.53.1).
- Todas as dependências resolvem e instalam no 3.15.0 (`uv.lock`). Ruff 0.17.1 (`target-version = "py315"`, sem aviso), mypy 2.4.0 (`python_version = "3.15"`) e os 46 testes passam.
- Há wheels `cp315-win_amd64` para as dependências binárias (`pydantic-core`, `SQLAlchemy`, `MarkupSafe`, `mypy`).

**Ainda não verificado:** o mesmo resultado no Windows. Rode `uv sync --locked` e a verificação completa (README).
