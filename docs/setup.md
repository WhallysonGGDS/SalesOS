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

## Evidências da Fase 02.1 (Cloud, Linux, 2026-10-25)

| Verificação | Resultado |
|---|---|
| Ruff, formatação e mypy strict | Sem erros |
| `uv run pytest` | 270 passed, 1 skipped (teste só do Windows), 1 aviso conhecido |
| CLI real (banco fictício no scratchpad): `alembic upgrade`, `backup`, `restore`, `recover`; `recover` com diário adulterado | Passou; diário adulterado recusado com mensagem, sem mover arquivos |
| Servidor real: busca com valor-sentinela fora do log; `Cache-Control: no-store` | Passou |
| Chromium: 7 telas × 320/390/768/1440 px; contraste de texto e bordas; foco em todas as paradas (inclui `datetime-local`); link "Ir para o conteúdo"; sem rolagem horizontal, erros de console ou CSP | Passou |
| Dados usados | Só fictícios, em bancos temporários; `data/` nunca foi aberto |

## Evidências da Fase 03 (Cloud, Linux, 2026-10-25)

| Verificação | Resultado |
|---|---|
| Ruff, formatação e mypy strict | Sem erros |
| `uv run pytest` | 426 passed, 1 skipped (teste só do Windows), 1 aviso conhecido |
| Migração `0003` num banco temporário: upgrade, downgrade, upgrade de novo e `alembic check` | Passou |
| Chromium: 9 telas do funil e 6 de clientes × 320/390/768/1440 px; contraste, foco no Tab, alvos de 44 px, rótulos, um `h1`, sem rolagem horizontal nem erro de CSP | Passou (dados fictícios no scratchpad) |
| Dados usados | Só fictícios, em bancos temporários; `data/` nunca foi aberto |

## Evidências da Fase 04 (Cloud, Linux, 2026-10-27)

| Verificação | Resultado |
|---|---|
| Ruff, formatação e mypy strict | Sem erros |
| `uv run pytest` | 577 passed, 1 skipped (teste só do Windows), 1 aviso conhecido |
| Migração `0004` num banco temporário: upgrade, downgrade, upgrade de novo e `alembic check`; backup da `0003` recusado sem `--migrar` e restaurado com ele | Passou |
| Chromium: 12 telas (agenda, filtros inválidos, detalhe, formulário, cliente, oportunidade) × 320/390/768/1440 px; contraste, foco no Tab, alvos de 44 px, rótulos, um `h1`, sem rolagem horizontal nem erro de CSP; teclado no filtro recolhível; reflow em 640 e 720 px | Passou (dados fictícios no scratchpad) |
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

1. `uv run pytest`: resultado esperado, com o Windows no fuso de Brasília, `655 passed, 5 skipped, 1 warning`; em outro fuso, `644 passed, 16 skipped, 1 warning` (estimativas; nunca executado no Windows). Se 3 testes de horário de verão de 2018–2019 falharem, veja o item 23. O teste `test_windows_refuses_swap_while_other_process_holds_the_file` precisa **rodar e passar** (não pode aparecer como skipped).
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
12. (Fase 02.1) Banco aberto no DB Browser **com uma alteração não gravada** (que segura o arquivo): `uv run salesos backup` termina em até cerca de 15 s com "bloqueado por outro programa", sem criar arquivo em `backups\`. Desfaça a alteração no DB Browser ao terminar.
13. (Fase 02.1) Com o servidor desligado, crie um `salesos.db.restore.json` de teste com o conteúdo `{"estado":"quiesced"}` na pasta do banco de teste: `uv run salesos recover` responde "Diário de restauração inválido" sem mover nada. Apague esse arquivo de teste depois.
14. (Fase 03) Funil com cliente fictício: criar oportunidade com valor `1.234,56`, mover entre etapas, perder com motivo, reabrir e ganhar; o histórico mostra todas as etapas, e as datas e horas aparecem no fuso do Windows.
15. (Fase 03) Filtro de período no funil: uma oportunidade fechada perto da meia-noite aparece no dia local certo; `De` depois de `Até` mostra a mensagem no campo.
16. (Fase 03) Seletor de data do filtro e da previsão de fechamento em pt-BR (dd/mm/aaaa).
17. (B1) Num banco de teste parado na revisão `0002` (`uv run alembic upgrade 0002` com `SALESOS_DATABASE_URL` de teste), criar um cliente fictício e um backup; voltar o banco de teste para o head (`uv run alembic upgrade head`). `uv run salesos restore <backup>` sem a opção é recusado; com `--migrar`, restaura o cliente fictício, o backup original continua com o mesmo SHA-256 (`Get-FileHash`) e não sobra pasta `.migracao-*` em `backups\`.

18. (Fase 04) Criar uma tarefa com prazo `10:00` de amanhã: o detalhe e a agenda mostram `10:00` no fuso do Windows; o seletor de data e hora aparece em pt-BR.
19. (Fase 04) Tarefa com prazo um minuto no passado: aparece em "Vencidas" com a palavra **Vencida** e a navegação mostra "Tarefas, 1 vencida"; ao concluir, o contador some; reabrir volta para pendente e o histórico mostra Criada, Concluída e Reaberta.
20. (Fase 04) Filtro de prazo por dia na agenda: uma tarefa com prazo perto da meia-noite aparece no dia local certo.
21. (Fase 04) Narrador ou NVDA na agenda: o link de cada tarefa é lido com a linha de apoio ("Vencida, Ligação, ...").
22. (Estabilização, E2) Com `uv run salesos` ligado num banco de teste: `uv run alembic upgrade head` é recusado ("Outro processo do SalesOS…") e a revisão não muda; num segundo terminal, `uv run uvicorn salesos.main:create_app --factory --port 8001` encerra com a mesma mensagem; `uv run salesos restore <backup>` é recusado. Depois de encerrar o servidor (Ctrl+C), `uv run alembic upgrade head` volta a funcionar. (Com o servidor ligado, também `alembic current` e `alembic history` são recusados: todo comando do Alembic que abre o banco pega a trava.)
23. (Estabilização, E4) Com o Windows no fuso "(UTC-03:00) Brasília": `uv run pytest tests/test_periodo.py tests/oportunidades/test_listagem.py tests/tarefas/test_listagem.py tests/tarefas/test_routes.py -rs`. Os testes de fuso precisam **rodar**, não aparecer como skipped. Uma falha em `test_historical_daylight_saving_uses_the_rules_of_that_date` ou `test_end_of_daylight_saving_day_has_25_hours` significa que o Windows não tem as regras do horário de verão de 2018–2019: anote a saída e não use filtros de período com datas dessa época até decidirmos o que fazer.

24. (Estabilização, E5) Expurgo num banco de teste com um cliente fictício anonimizado: com o servidor ligado, `uv run salesos expurgar` é recusado ("Outro processo do SalesOS…"). Com ele desligado e a data de anonimização dentro do prazo, o comando diz "Nada a expurgar". Para ver o expurgo, use o teste automático (`uv run pytest tests/test_expurgo.py tests/test_expurgo_cli.py`); no banco de teste, responda algo diferente de `EXPURGAR 1` e confira que nada foi apagado.
25. (Estabilização, E6) No navegador, num banco de teste: um cliente fictício com mais de 50 interações mostra **Interações mais antigas** e a página 2 chega à primeira interação; abrir `http://127.0.0.1:8000/tarefas/0` mostra a página "Endereço inválido" (não um texto em JSON); enviar um formulário depois de reiniciar o servidor sem `SALESOS_SECRET_KEY` fixo mostra a página "Formulário expirado".
26. (Anonimização nos backups) `uv run pytest tests/backup/test_restore_anonimizados.py tests/test_paginas_erro.py` passa. Num banco de teste com um cliente fictício anonimizado, `uv run salesos backup` e `uv run salesos restore <esse backup>` restauram normalmente.

Só depois disso (os itens 17 a 26 confirmam B1, a trava, os backups, o fuso, o expurgo, as telas da estabilização e a checagem dos clientes anonimizados no Windows), e com a sua aprovação, cadastrar dados reais. A política de retenção (P1) está em `docs/privacy.md`: siga a rotina mensal de expurgo e de rotação dos backups. Também pendentes antes de dados reais: as fontes oficiais de CPF, CNPJ e telefone, se forem necessários.

## Limitações conhecidas

- Context7 indisponível no Cloud (bloqueio de rede, `ERR_PROXY_TUNNEL`). Consultas feitas na documentação oficial e no PyPI.
- Sem segredo fixo em `.env`, reiniciar o servidor invalida formulários abertos.
- `database_url` relativo: rode os comandos a partir da raiz do projeto.
