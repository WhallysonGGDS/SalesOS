# Qualidade

| Comando | Prova |
|---|---|
| `uv sync --locked` | Instalação reproduzível: falha se `uv.lock` estiver desatualizado |
| `uv run ruff check .` | Lint (pyflakes, pycodestyle, isort, bugbear, pyupgrade, bandit `S`, simplify, ruff) |
| `uv run ruff format --check .` | Formatação. `tooling/` fica excluído (cópia preservada do Toolkit) |
| `uv run mypy` | Tipos em modo `strict` em `src`, `tests` e `migrations` |
| `uv run pytest` | 46 testes: configuração, banco, segurança, páginas e migrações |

## Resultado esperado do pytest: 1 aviso conhecido

`N passed, 1 warning` é o resultado **normal** e não indica falha. Esse aviso é:

```
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

- **Origem:** é emitido em `starlette/testclient.py` (Starlette 1.9.0, `warnings.warn`, linha 40) quando o `httpx2` não está instalado. Por causa do `stacklevel=2`, o pytest o mostra atribuído a `fastapi/testclient.py:1`, que importa o `TestClient`.
- **Categoria:** `StarletteDeprecationWarning` herda de `UserWarning` e por isso aparece em toda execução.
- **Por que não é problema:** o `TestClient` continua funcionando com o `httpx` 0.28.1, e os testes passam. A decisão D13 da Fase 02 mantém o `httpx` e não adota o `httpx2`.
- **O que observar:** mais de 1 aviso, ou um aviso com outro texto, é novidade e precisa ser investigado. O aviso não é filtrado nem silenciado de propósito.
- **Troca de dependência:** qualquer mudança futura (por exemplo, para `httpx2`) exige avaliação própria e autorização explícita.

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
