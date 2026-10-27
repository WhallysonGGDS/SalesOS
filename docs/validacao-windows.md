# E8 — Validação no Windows e acessibilidade (roteiro e registro)

Roteiro da checklist B (`docs/setup.md`, itens 1–26) e do teste com leitor de tela. Quem executa é o proprietário, no Windows real; este documento registra o que foi pedido, o que foi observado e o estado de cada item. **O sistema continua bloqueado para dados reais.**

- **Código testado:** branch `claude/practical-bell-w2zwqp`, commit a confirmar no passo 1 (último publicado antes da E8: `e3513f5`).
- **Dados:** só fictícios, em `%TEMP%\salesos-e8\`. A pasta `data\` do projeto não é usada, aberta nem alterada.
- **Estados:** aprovado, reprovado, bloqueado, não executado. Um item só é aprovado com evidência do Windows; a suíte do Linux não substitui nenhum item.

## Ambiente de teste (cada terminal PowerShell, na raiz do projeto)

```powershell
$base = Join-Path $env:TEMP "salesos-e8"
New-Item -ItemType Directory -Force -Path $base, "$base\backups" | Out-Null
$env:SALESOS_DATABASE_URL = "sqlite:///" + ((Join-Path $base "salesos.db") -replace '\\','/')
$env:SALESOS_BACKUP_DIR = Join-Path $base "backups"
uv run python -c "from salesos.config import Settings; s = Settings(); print('BANCO:', s.database_url); print('BACKUPS:', s.backup_dir)"
```

Só continue se as duas linhas apontarem para `...\Temp\salesos-e8`. As variáveis valem só para aquele terminal: um terminal novo precisa do bloco de novo.

## Ambiente registrado

| Campo | Valor |
|---|---|
| Windows (versão e build) | — |
| Fuso horário | — |
| Python (`uv run python --version`) | — |
| uv | — |
| Git | — |
| Navegador e versão | — |
| Leitor de tela e versão | — |
| Branch e commit testados | — |

## Checklist B

O comando exato de cada item está em `docs/setup.md`, com o mesmo número.

| Item | Objetivo | Pré-condições | Resultado esperado | Observado | Estado | Evidência |
|---|---|---|---|---|---|---|
| 1 | Suíte completa no Windows | ambiente de teste; `uv sync --locked` | Brasília: `686 passed, 5 skipped, 1 warning`; outro fuso: `675 passed, 16 skipped, 1 warning`; `test_windows_refuses_swap_while_other_process_holds_the_file` roda e passa | — | não executado | — |
| 2 | Backup com o servidor ligado | servidor ligado no banco de teste | `.db` e `.db.json` criados | — | não executado | — |
| 3 | Restore recusado com o servidor ligado | item 2 | "Outro processo do SalesOS…" | — | não executado | — |
| 4 | Restore recusado com DB Browser aberto | servidor desligado; DB Browser no banco de teste | "Feche os programas…", nada alterado | — | não executado | — |
| 5 | Restore limpo | servidor desligado | dados voltam; `.pre-restore-*` e `backups\pre-restore-*.db` existem | — | não executado | — |
| 6 | Servidor encerrado à força sobe de novo | servidor ligado | sobe normalmente | — | não executado | — |
| 7 | Restore interrompido e `recover` | restore em andamento | servidor recusa iniciar; `recover` resolve e pode ser repetido | — | não executado | — |
| 8 | Anonimização | cliente fictício | busca pelos dados antigos vazia; edição recusada | — | não executado | — |
| 9 | Permissões da pasta | — | outras contas sem acesso a `data\` (só leitura das permissões; `data\` não é aberta) | — | não executado | — |
| 10 | Interface e leitor de tela no cliente | servidor ligado | data em pt-BR, hora local, teclado, leitor nas telas de cliente | — | não executado | — |
| 11 | Sem sobras | depois dos itens 2–7 | nenhum `.tmp`, `.staging-` ou `salesos.db.restore.json` | — | não executado | — |
| 12 | Backup com banco travado | DB Browser com alteração não gravada | ~15 s, "bloqueado por outro programa", sem arquivo novo | — | não executado | — |
| 13 | Diário adulterado | servidor desligado; diário de teste | "Diário de restauração inválido", nada movido | — | não executado | — |
| 14 | Funil completo | cliente fictício | valor `1.234,56`, etapas, perda, reabertura, ganho; histórico e horas no fuso local | — | não executado | — |
| 15 | Filtro de período no funil | oportunidade fechada perto da meia-noite | dia local certo; `De` > `Até` mostra a mensagem | — | não executado | — |
| 16 | Seletores de data do funil | — | dd/mm/aaaa | — | não executado | — |
| 17 | `restore --migrar` de backup da `0002` | banco de teste na `0002` | sem opção: recusado; com `--migrar`: cliente volta; SHA-256 do original igual; sem `.migracao-*` | — | não executado | — |
| 18 | Prazo de tarefa no fuso local | — | `10:00` no detalhe e na agenda; seletor em pt-BR | — | não executado | — |
| 19 | Tarefa vencida | prazo no passado | "Vencida", "Tarefas, 1 vencida"; histórico Criada, Concluída, Reaberta | — | não executado | — |
| 20 | Filtro por dia na agenda | prazo perto da meia-noite | dia local certo | — | não executado | — |
| 21 | Leitor de tela na agenda | NVDA ou Narrador | link lido com a linha de apoio | — | não executado | — |
| 22 | Trava com o servidor ligado | servidor ligado | `alembic upgrade`, `uvicorn` direto e `restore` recusados; revisão e banco sem mudança; depois do Ctrl+C, `alembic upgrade head` funciona | — | não executado | — |
| 23 | Fuso de Brasília e horário de verão | Windows em "(UTC-03:00) Brasília" | testes de fuso rodam (não skipped) e passam | — | não executado | — |
| 24 | Expurgo | cliente fictício anonimizado | recusa com o servidor ligado; "Nada a expurgar" no prazo; confirmação errada não apaga; testes automáticos passam | — | não executado | — |
| 25 | Paginação e páginas de erro | cliente com mais de 50 interações | "Interações mais antigas"; página 2 chega à primeira; `/tarefas/0` em HTML; "Formulário expirado" | — | não executado | — |
| 26 | Backups com cliente anonimizado | cliente fictício anonimizado | testes passam; backup legítimo restaura. Pedido da E8, além do item original: adulterado recusado no `restore`, `--migrar` e `--aceitar-reintroducao` | — | não executado | — |

## Acessibilidade (leitor de tela real)

Telas: clientes, funil, tarefas. Itens: teclado, ordem e visibilidade do foco, nomes e estados anunciados, títulos e cabeçalhos, rótulos e mensagens de validação, retorno de sucesso e erro, tabelas, listas, paginação e ações, confirmações, fluxos completos sem mouse. Este teste não prova conformidade integral com a WCAG.

| Tela e fluxo | Leitor e navegador | Observado | Defeitos | Estado |
|---|---|---|---|---|
| Clientes: criar, buscar, abrir, editar, interação, arquivar, anonimizar | — | — | — | não executado |
| Funil: criar, filtrar, mover etapa, perder, reabrir | — | — | — | não executado |
| Tarefas: criar, agenda, filtro, concluir, reabrir, cancelar | — | — | — | não executado |

## Falhas e correções

Nenhuma registrada.
