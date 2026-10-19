# Onboarding (Windows)

1. Instale o Git for Windows e o uv (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`. Esse é o instalador oficial; leia-o antes de executar, se preferir.
2. Baixe o repositório pelo GitHub Desktop (branch `claude/practical-bell-w2zwqp`) e abra o terminal na pasta do projeto.
3. `uv sync --locked`: o uv baixa o Python 3.15 e instala as versões exatas do `uv.lock` em `.venv`.
4. `uv run alembic upgrade head`: cria `data\salesos.db`.
5. `uv run salesos` e abra http://127.0.0.1:8000.
6. Opcional: copie `.env.example` para `.env` para fixar a porta ou o segredo.

Para encerrar, use Ctrl+C. Os dados ficam em `data\` (nunca vão para o Git). Faça uma cópia dessa pasta para guardar; o procedimento formal de backup chega na Fase 07.
