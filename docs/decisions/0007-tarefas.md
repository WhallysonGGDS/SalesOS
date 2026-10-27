# 0007 — Tarefas e follow-ups

**Status:** aceita (Fase 04; plano `docs/superpowers/plans/2026-10-25-fase-04-tarefas.md`, decisões aprovadas em 2026-10-27)

**Contexto:** o briefing (7.4) pede ligações, reuniões, mensagens registradas manualmente e retornos comerciais, com datas e prazos, prioridades, status, histórico de conclusão e alertas internos para tarefas vencidas, sem enviar mensagens nem integrar nada externamente.

**Decisão:**
- Pacote `features/tarefas/` e migração `0004` (depois de `0003`), com duas tabelas:
  - `tarefas`;
  - `tarefa_eventos`, só de acréscimo: nenhuma função nem rota edita ou apaga um evento.
- **D1:** toda tarefa tem um cliente. A oportunidade é opcional e precisa ser do **mesmo** cliente, regra garantida pelo serviço, porque um CHECK do SQLite não consulta outra tabela.
- **D2:** tipos `ligacao`, `reuniao`, `mensagem` (registrada manualmente; nada é enviado) e `retorno`.
- **D3:** `prazo` com data e hora. O `datetime-local` é lido no fuso do computador e gravado em UTC.
- **D4:** prioridade `baixa`, `normal` (padrão) ou `alta`.
- **D5:** estados `pendente`, `concluida` e `cancelada`. **Reabrir** (ação explícita) volta para `pendente` e limpa `concluida_em`/`cancelada_em`; os eventos anteriores ficam.
- **D6:** cada criação, edição (só os nomes dos campos), conclusão, cancelamento e reabertura gera, no mesmo commit:
  - um `tarefa_eventos` (salvo a edição, que não muda o estado);
  - um evento na linha do tempo do cliente, sem título nem descrição: "Tarefa #N concluída".
- **D7, vencida:** `pendente` com `prazo` anterior ao momento atual. O prazo está em UTC, então a comparação vale para o horário local do computador. Concluídas e canceladas nunca contam. O contador é calculado a cada página (navegação e avisos); não há notificação externa nem tarefa em segundo plano.
- **D8:** editar só enquanto `pendente`; sem exclusão (cancelar em vez de apagar). Repetir o estado atual não gera nada.
- **D9:** a agenda é uma lista ordenada por prazo; não há calendário em grade.
- **D10:** anonimizar o cliente apaga título e descrição das tarefas dele. Tipo, prioridade, estado e datas ficam, sob a pendência **P1** (`docs/privacy.md`); não são declarados anônimos. As tarefas dele não aceitam mais mudanças (409); por decisão do usuário em 2026-10-27, as pendentes **saem do contador de vencidas e da agenda** e continuam visíveis, só para leitura, na página do cliente. Nada é gravado nelas por causa disso.
- `intervalo_utc` passa a ficar em `salesos/periodo.py`, compartilhado com o funil (regras de fuso do sistema para cada data, P3 do ADR 0006), e `IdDep` em `salesos/formularios.py`.

**Consequências e limites:**
- Depois da `0004`, backups da `0003` são recusados sem `--migrar`. Com `--migrar` (B1, ADR 0005), são migrados; o teste de regressão da cadeia passa a incluir a `0003`.
- "Vencida" depende do relógio do computador. Os testes injetam o momento atual em vez de depender do relógio.
- Os filtros de período por dia local herdam a limitação de P3: no Windows, a precisão histórica do fuso não está verificada.
- Sem recorrência, responsável, lembretes nem calendário. As sugestões S-a, S-b e S-c ficaram fora por decisão do usuário.
