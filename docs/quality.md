# Qualidade

| Comando | Prova |
|---|---|
| `uv sync --locked` | Instalação reproduzível: falha se `uv.lock` estiver desatualizado |
| `uv run ruff check .` | Lint (pyflakes, pycodestyle, isort, bugbear, pyupgrade, bandit `S`, simplify, ruff) |
| `uv run ruff format --check .` | Formatação. `tooling/` fica excluído (cópia preservada do Toolkit) |
| `uv run mypy` | Tipos em modo `strict` em `src`, `tests` e `migrations` |
| `uv run pytest` | 46 testes: configuração, banco, segurança, páginas e migrações |

## O que os testes cobrem
- **Configuração:** padrões locais, variáveis de ambiente, host não loopback recusado, segredo aleatório, segredo vazio ignorado, segredo curto recusado, `ALLOWED_HOSTS` não alterável por ambiente.
- **Banco:** PRAGMAs (FK, WAL, busy_timeout), FK aplicada de fato (inserção órfã falha), criação da pasta, migração em batch preservando linhas filhas, `foreign_key_check` acusando órfãos, FK religada mesmo após falha.
- **Segurança:** hosts aceitos e recusados, cabeçalhos em `/` e `/health`, atributos do cookie; POST, PUT, PATCH e DELETE sem token; primeiro POST sem cookie; token forjado; token válido por formulário, header e renderizado pelo template; endereço IPv6 exibido com colchetes.
- **Migrações:** `upgrade head` → `downgrade base` num banco temporário, e `alembic check` sem diferenças. Uma migração que deixa um filho órfão é desfeita por inteiro (versão não avança, tabelas não ficam).

## O que os testes não cobrem
- Rotas POST de produção: ainda não existem. O CSRF é provado com rotas criadas só dentro dos testes.
- Navegador: verificado manualmente com Playwright (`docs/setup.md`), sem teste automatizado.

## Revisões
- Diffs não triviais: `superpowers:requesting-code-review` (revisor independente, somente leitura) e `ponytail:ponytail-review`.
- Segurança: `tooling/vibe-coding-toolkit/docs/prompts/13-security-review.md`, com relatório privado fora do repositório.
- Dependências: `uvx pip-audit` (ver `docs/setup.md`).
