# Qualidade

| Comando | Prova |
|---|---|
| `uv sync --locked` | Instalação reproduzível: falha se `uv.lock` estiver desatualizado |
| `uv run ruff check .` | Lint (pyflakes, pycodestyle, isort, bugbear, pyupgrade, bandit `S`, simplify, ruff) |
| `uv run ruff format --check .` | Formatação. `tooling/` fica excluído (cópia preservada do Toolkit) |
| `uv run mypy` | Tipos em modo `strict` em `src`, `tests` e `migrations` |
| `uv run pytest` | 578 testes (lista por área abaixo) |

## Resultado esperado do pytest

| Sistema | Resultado normal |
|---|---|
| Linux (verificado no Cloud) | `577 passed, 1 skipped, 1 warning` |
| Windows (**ainda não executado**; estimativa a partir dos testes pulados) | `562 passed, 16 skipped, 1 warning` |

- **Skipped no Linux (1):** o teste que prova que o Windows recusa trocar o banco enquanto outro processo o mantém aberto. Só faz sentido no Windows.
- **Skipped no Windows (16):** os 5 testes de permissões POSIX (`0600`/`0700`) e os 11 testes de período e de prazo local que fixam o fuso do processo com `time.tzset()` (só existe em POSIX; ADR 0006, P3). No Windows, a precisão histórica do fuso **não está verificada**.
- Qualquer outro `skipped`, uma falha ou um segundo aviso é novidade e precisa ser investigado.

### O aviso conhecido

```
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

- **Origem:** é emitido em `starlette/testclient.py` (Starlette 1.9.0, `warnings.warn`, linha 40) quando o `httpx2` não está instalado. Por causa do `stacklevel=2`, o pytest o mostra atribuído a `fastapi/testclient.py:1`, que importa o `TestClient`.
- **Categoria:** `StarletteDeprecationWarning` herda de `UserWarning` e por isso aparece em toda execução.
- **Por que não é problema:** o `TestClient` continua funcionando com o `httpx` 0.28.1, e os testes passam. A decisão D13 da Fase 02 mantém o `httpx` e não adota o `httpx2`.
- **O que observar:** mais de 1 aviso, ou um aviso com outro texto, é novidade e precisa ser investigado. O aviso não é filtrado nem silenciado de propósito.
- **Troca de dependência:** qualquer mudança futura (por exemplo, para `httpx2`) exige avaliação própria e autorização explícita.

## O que os testes cobrem

| Área | Arquivos | Testes | O que provam |
|---|---|---|---|
| Configuração | `test_config.py` | 13 | padrões locais, host só loopback, segredo forte, hosts não alteráveis por ambiente |
| Banco e migrações | `test_db.py`, `test_migrations.py`, `clientes/test_schema.py`, `oportunidades/test_schema.py`, `tarefas/test_schema.py` | 81 | PRAGMAs (FK, WAL, `secure_delete`), migração em batch sem perder filhos, `upgrade`/`downgrade`/`alembic check`, CHECKs, UNIQUEs, FKs, ausência de telefone, erros sem valores; CHECKs do funil (etapa, motivo só na perda, fechamento, ganha com valor, valor inteiro); `0003` upgrade → downgrade → upgrade; CHECKs e FKs `RESTRICT` das tarefas e do histórico, `0004` upgrade → downgrade → upgrade |
| Aplicação e segurança HTTP | `test_app.py`, `test_security.py` | 30 | hosts, cabeçalhos (CSP, `no-store`), cookie e token CSRF, sessão por requisição fechada, limite de 256 KiB do corpo (com e sem `Content-Length`, desconexão no meio) |
| Normalização e validação | `clientes/test_normalize.py`, `clientes/test_schemas.py`, `test_dinheiro.py`, `oportunidades/test_schemas.py`, `test_periodo.py`, `tarefas/test_schemas.py` | 159 | e-mail, busca sem acento, escape de `LIKE`, campos bloqueados (`documento`, `telefone`) recusados, datas em UTC; dinheiro só em formatos pt-BR (sem float, sinal, notação científica); datas AAAA-MM-DD; período local → UTC com horário de verão histórico; prazo das tarefas só por extenso, em UTC e em segundos inteiros (anos 2000–2100), sem timestamp nem estouro de fuso |
| Serviço e privacidade | `clientes/test_service.py`, `clientes/test_privacy.py`, `oportunidades/test_*.py` de serviço, listagem e privacidade, `tarefas/test_service.py`, `test_listagem.py`, `test_privacidade.py` | 74 | duplicados, eventos só com nomes de campos, interações só de acréscimo, anonimização (inclusive bytes do `.db` e `-wal`), logs sem dados pessoais; regras R1–R10 do funil, histórico de etapas imutável, operação e evento no mesmo commit, anonimização das oportunidades (bytes do `.db`/`-wal`), filtros de período e limites; tarefas: estados, reabertura, histórico só de acréscimo, oportunidade do mesmo cliente, vencidas no limite exato do prazo, anonimização (D10, bytes do `.db`/`-wal`) e clientes anonimizados fora da agenda |
| Rotas e interface | `clientes/test_routes.py`, `clientes/test_routes_seguranca.py`, `clientes/test_ui.py`, `oportunidades/test_routes.py`, `tarefas/test_routes.py`, `tarefas/test_routes_robustez.py` | 97 | CSRF em todas as rotas POST, maior formulário legítimo dentro do limite do corpo, GET sem efeito colateral, XSS escapado, 303, 404/409 sem dados pessoais, rótulos, foco semântico, estados vazios; agenda, contador de vencidas em texto, ids e datas extremos → 422 (nunca 500), contador que só silencia a tabela ausente |
| Backup, restauração e trava | `backup/test_*.py` | 124 | integridade, SHA-256, revisão e estrutura do backup; backup desiste com banco bloqueado; bloqueio separado de outros erros do SQLite; restauração com falha e queda em cada estado; `recover` idempotente e recusa de diário adulterado (caminhos, carimbo, JSON); backup da revisão `0002` recusado depois da `0003` sem `--migrar`; `restore --migrar` (B1): seis cenários de backup antigo, falhas e interrupções injetadas, sobras relatadas pelo recover, e regressão em toda revisão anterior ao head; conexões concorrentes; disco cheio; trava entre processos; permissões; CLI |

Mutações (alterar o código de propósito para ver o teste falhar) foram usadas nas proteções de privacidade, segurança, backup e restauração; os resultados estão em `docs/phases.md`.

## O que os testes não cobrem

- **Windows:** trava `msvcrt`, troca de arquivo aberto, ACLs, fuso do sistema, seletor de data em pt-BR, fonte Segoe UI Variable. Ver a checklist em `docs/setup.md`.
- **Navegador:** a interface foi auditada no Chromium (contraste, foco, teclado, alvos de 44 px, larguras de 320 a 1440 px, CSP) por scripts fora da suíte, nas Fases 02, 03 e 04; na Fase 04 também teclado no filtro recolhível e reflow equivalente a 200% (640 e 720 px). Leitor de tela real não foi testado.
- **Dependências:** a auditoria de vulnerabilidades (`uvx pip-audit`) foi feita na Fase 01; as Fases 02 a 04 não adicionaram dependências e não repetiram a auditoria.

## Revisões
- Diffs não triviais: `superpowers:requesting-code-review` (revisor independente, somente leitura) e `ponytail:ponytail-review`.
- Segurança: `tooling/vibe-coding-toolkit/docs/prompts/13-security-review.md`, com relatório privado fora do repositório.
- Dependências: `uvx pip-audit` (ver `docs/setup.md`).
