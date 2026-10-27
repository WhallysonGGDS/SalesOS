# WE TECH SalesOS

CRM comercial próprio da WE TECH. Roda localmente, para um único usuário, sem exposição à rede.

**Estado:** clientes, contatos, histórico (Fase 02) e o funil de oportunidades (Fase 03) implementados e verificados no Linux. **A validação no Windows está pendente.** Dados reais só depois da checklist de `docs/setup.md`, da confirmação no Windows da restauração de backups antigos (B1, `restore --migrar`) e da definição de retenção (P1, `docs/privacy.md`). CPF, CNPJ e telefone ainda não existem (aguardam as regras oficiais). Tarefas e propostas chegam nas próximas fases (`docs/phases.md`).

## Começar

Requisitos: [uv](https://docs.astral.sh/uv/) e Git. O `uv` instala o Python 3.15 sozinho.

```bash
uv sync --locked             # cria .venv e instala as dependências exatas do uv.lock
uv run alembic upgrade head  # cria/atualiza o banco em data/salesos.db
uv run salesos               # abre em http://127.0.0.1:8000
```

Rode os comandos a partir da raiz do projeto. Passo a passo para Windows: `docs/onboarding.md`.

## Backup e restauração

```bash
uv run salesos backup                       # backup verificado em data/backups (servidor pode estar ligado)
uv run salesos restore data/backups/<arquivo>.db   # com o servidor desligado
uv run salesos restore <backup-antigo>.db --migrar  # backup de versão anterior: migra uma cópia e restaura
uv run salesos recover                      # termina com segurança uma restauração interrompida
```

Não copie a pasta `data/` com o servidor ligado. Backups contêm dados pessoais e nunca são apagados automaticamente: veja `docs/privacy.md`. Desenho e limites: ADR `0005`.

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
| `docs/onboarding.md` | Instalação, uso, backup e restauração (Windows) |
| `docs/privacy.md` | Dados pessoais, anonimização e seus limites, backups |
| `docs/quality.md` | Verificações e o que cada uma prova |
| `docs/setup.md` | Versões, evidências e a checklist antes de dados reais |
| `docs/dependencies.md` | Dependências e licenças |
| `docs/phases.md` | Registro das fases |
| `docs/decisions/` | Decisões de arquitetura (ADRs) |
| `docs/toolkit/` | Integração do Vibe Coding Toolkit |
