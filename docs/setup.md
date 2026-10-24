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

## Evidências da Fase 02 (Cloud, Linux, 2026-10-24)

| Verificação | Resultado |
|---|---|
| Ruff, formatação e mypy strict | Sem erros |
| `uv run pytest` | 230 passed, 1 skipped (teste só do Windows), 1 aviso conhecido |
| Cada commit da fase testado num worktree isolado | E0: 46 passed; E1: 67; E2–E6: 210 (+1 skipped); E7: 214; A: 217; B: 225; C: 230 |
| CLI real (bancos no scratchpad): backup com servidor ligado; restore e recover recusados com o servidor ligado; restore com servidor desligado; backup forjado com view recusado | Passou |
| Permissões com umask 022 (banco do `alembic upgrade`, backup e manifesto) | `0600`; pasta de backups `0700` |
| Servidor real: busca com valor-sentinela fora do log; `Cache-Control: no-store` | Passou |
| Chromium: 7 telas × 320/390/768/1440 px; contraste de texto e bordas; foco em todas as paradas (inclui `datetime-local`); link "Ir para o conteúdo"; sem rolagem horizontal, erros de console ou CSP | Passou |
| Dados usados | Só fictícios, em bancos temporários; `data/` nunca foi aberto |

## Pendente no Windows

Fase 01:

1. `uv sync --locked`: confirma o Python 3.15.0 e as wheels `win_amd64`.
2. A verificação completa do README.
3. `uv run alembic upgrade head` e `uv run salesos`: abrir http://127.0.0.1:8000, conferir a página e o `/health`.
4. Fonte Segoe UI Variable (só existe no Windows; no Cloud a página usa outra fonte do sistema).
5. Plugins e Context7 numa sessão do Claude Code (`docs/toolkit/INSTALLATION.md`).

## Antes de usar dados reais (checklist B, Windows)

Sempre com um banco de teste: no `.env`, `SALESOS_DATABASE_URL=sqlite:///C:/Users/<você>/AppData/Local/Temp/salesos-teste/salesos.db` e `SALESOS_BACKUP_DIR` numa pasta de teste, com dados fictícios. Ao terminar, remova essas linhas do `.env`.

1. `uv run pytest`: resultado `227 passed, 4 skipped, 1 warning`. O teste `test_windows_refuses_swap_while_other_process_holds_the_file` precisa **rodar e passar** (não pode aparecer como skipped).
2. Com o servidor ligado, `uv run salesos backup` cria o backup e o `.db.json`.
3. Com o servidor ligado, `uv run salesos restore <backup>` é recusado ("Outro processo do SalesOS…").
4. Servidor desligado e o banco aberto no DB Browser: o restore é recusado ("Feche os programas…") sem alterar nada.
5. Restore limpo: os dados do backup voltam, e existem `salesos.db.pre-restore-<data>` e `backups\pre-restore-<data>.db`.
6. Encerrar o servidor pelo Gerenciador de Tarefas e iniciar de novo: sobe normalmente.
7. Fechar o terminal no meio de um restore (ou simular): o servidor recusa iniciar; `uv run salesos recover` resolve e pode ser repetido.
8. Anonimizar um cliente fictício: busca vazia pelos dados antigos, edição recusada.
9. Conferir que a pasta do projeto está dentro do seu usuário e que outras contas do Windows não têm acesso a `data\` (Propriedades → Segurança).
10. Interface: seletor de data em pt-BR, hora local correta na linha do tempo, navegação por teclado, Narrador ou NVDA nas telas de cliente.
11. Nenhum `.tmp`, `.staging-` ou `salesos.db.restore.json` sobrando ao final.

Só depois disso, e com a sua aprovação, cadastrar dados reais. Também pendentes antes de dados reais: as fontes oficiais de CPF, CNPJ e telefone, se forem necessários.

## Limitações conhecidas

- Context7 indisponível no Cloud (bloqueio de rede, `ERR_PROXY_TUNNEL`). Consultas feitas na documentação oficial e no PyPI.
- Sem segredo fixo em `.env`, reiniciar o servidor invalida formulários abertos.
- `database_url` relativo: rode os comandos a partir da raiz do projeto.
