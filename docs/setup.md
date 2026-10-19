# Setup, versões e evidências

Toolkit: Vibe Coding Toolkit, revisão `790a895` (detalhes em `docs/toolkit/`).

## Ambiente da Fase 01 (Cloud, Linux, 2026-10-19)

| Item | Versão |
|---|---|
| Python | 3.15.0 (CPython, GIL ativo; SQLite embutido 3.53.1), instalado por `uv python install 3.15.0` |
| uv | 0.13.1 (atualizado de 0.11.32 com `uv self update`, só neste container) |
| Dependências | `uv.lock` (lista e licenças em `docs/dependencies.md`) |
| Navegador de verificação | Chromium via Playwright, já presente no ambiente |

## Evidências (executadas na Fase 01)

| Verificação | Resultado |
|---|---|
| `uv sync --locked` (cópia limpa no scratchpad) | 37 pacotes no CPython 3.15.0; Ruff, mypy e testes passam na cópia |
| `uv run ruff check .` / `ruff format --check .` | Sem erros / formatado |
| `uv run mypy` (strict) | Sem erros |
| `uv run pytest` | 46 passaram, 1 aviso (`httpx` → `httpx2`, ver `docs/dependencies.md`) |
| Servidor real (`uv run salesos`, banco temporário) | `/health` 200 com CSP, X-Frame-Options e cookie CSRF; `Host` falso → 400; `/docs` → 404; socket em escuta só em `127.0.0.1` |
| Banco real criado pelo servidor | `journal_mode = wal` |
| Chromium 1440×900 e 390×844 | Status 200, sem erros de console nem CSP, sem rolagem horizontal, primeiro Tab no link de pular conteúdo |
| `uvx pip-audit` | Sem vulnerabilidades conhecidas |
| Modelo de migração | Revisão gerada numa cópia descartável sai limpa no Ruff (post-write hooks) |

## Pendente no Windows

1. `uv sync --locked`: confirma o Python 3.15.0 e as wheels `win_amd64`.
2. A verificação completa do README.
3. `uv run alembic upgrade head` e `uv run salesos`: abrir http://127.0.0.1:8000, conferir a página e o `/health`.
4. Fonte Segoe UI Variable (só existe no Windows; no Cloud a página usa outra fonte do sistema).
5. Plugins e Context7 numa sessão do Claude Code (`docs/toolkit/INSTALLATION.md`).

## Limitações conhecidas

- Context7 indisponível no Cloud (bloqueio de rede, `ERR_PROXY_TUNNEL`). Consultas feitas na documentação oficial e no PyPI.
- Não há rotas POST de produção: o CSRF é provado com rotas criadas só nos testes.
- Sem segredo fixo em `.env`, reiniciar o servidor invalida formulários abertos.
- `database_url` relativo: rode os comandos a partir da raiz do projeto.
