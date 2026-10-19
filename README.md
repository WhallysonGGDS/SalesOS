# WE TECH SalesOS

CRM comercial próprio da WE TECH. Roda localmente, para um único usuário, sem exposição à rede.

**Estado:** Fase 01 (fundação técnica) concluída. Ainda não há funcionalidades de CRM: clientes, funil, tarefas e propostas chegam nas próximas fases (`docs/phases.md`).

## Começar

Requisitos: [uv](https://docs.astral.sh/uv/) e Git. O `uv` instala o Python 3.15 sozinho.

```bash
uv sync --locked             # cria .venv e instala as dependências exatas do uv.lock
uv run alembic upgrade head  # cria/atualiza o banco em data/salesos.db
uv run salesos               # abre em http://127.0.0.1:8000
```

Rode os comandos a partir da raiz do projeto. Passo a passo para Windows: `docs/onboarding.md`.

## Verificar

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
```

O que cada verificação prova está em `docs/quality.md`.

## Documentos

| Documento | Conteúdo |
|---|---|
| `PRODUCT.md` | Problema, escopo, restrições e critérios de aceite |
| `AGENTS.md` / `CLAUDE.md` | Regras para agentes de programação |
| `docs/architecture.md` | Estrutura e decisões técnicas |
| `docs/design.md` | Direção visual e acessibilidade |
| `docs/onboarding.md` | Instalação e primeiro uso (Windows) |
| `docs/quality.md` | Verificações e o que cada uma prova |
| `docs/setup.md` | Versões, ferramentas, evidências e pendências |
| `docs/dependencies.md` | Dependências e licenças |
| `docs/phases.md` | Registro das fases |
| `docs/decisions/` | Decisões de arquitetura (ADRs) |
| `docs/toolkit/` | Integração do Vibe Coding Toolkit |
