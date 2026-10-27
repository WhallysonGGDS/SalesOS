# Fase 04 — Tarefas e follow-ups: plano de implementação

> **VERSÃO FINAL — D1–D10 aprovadas pelo usuário em 2026-10-27, sem mudança de escopo.** B1 já foi implementado (pré-requisito pedido pelo usuário). Implementação ainda não iniciada.
> Criado com `superpowers:writing-plans`. Execução proposta: nativa (o agente principal implementa), com revisão de segurança independente por etapa de código e revisão geral no fim, como nas Fases 02.1 e 03.

**Objetivo:** registrar tarefas comerciais com prazo, prioridade e situação, mostrar o que está vencido e guardar o histórico de conclusão, sem enviar nada para fora do computador.

**Arquitetura:** novo pacote `src/salesos/features/tarefas/` (modelo, schemas, serviço, rotas), no padrão de `features/oportunidades/`. Migração `0004`. Interface Jinja2 sem JavaScript.

**Stack:** a mesma das Fases 02 e 03. **Nenhuma dependência nova.**

**Especificação:** briefing da Fase 00, seção 7.4 (e 7.1, só para saber o que o dashboard vai precisar), seções 8, 9 e 11 ("Fase 04 — Tarefas e agenda: implementar tarefas, prioridades, prazos e follow-ups"); `PRODUCT.md`; `AGENTS.md`; `docs/privacy.md`; ADR 0006.

## O que o briefing pede (7.4, literal)

| Item do briefing | Como o plano propõe tratar |
|---|---|
| Ligações | tipo `ligacao` |
| Reuniões | tipo `reuniao` |
| Mensagens registradas manualmente | tipo `mensagem`; nada é enviado (registro manual) |
| Retornos comerciais | tipo `retorno` |
| Datas e prazos | `prazo` (data e hora, UTC no banco, hora local na tela) |
| Prioridades | lista fixa (D4) |
| Status | lista fixa (D5) |
| Histórico de conclusão | tabela só de acréscimo `tarefa_eventos` (D6) |
| Alertas internos para tarefas vencidas | aviso calculado a cada página, sem notificação externa nem JavaScript (D7) |
| "Não enviar mensagens ou realizar integrações externas automaticamente nesta versão" | nenhum envio, nenhum agendamento em segundo plano, nenhuma notificação do sistema operacional |

O briefing **não** diz:
- a quem a tarefa se liga;
- se o prazo tem hora;
- quais são as prioridades e os estados;
- se uma tarefa concluída pode ser reaberta;
- o que é "agenda" na Fase 04.

Essas são as decisões D1 a D10 abaixo. Nenhuma foi tomada por conta própria.

## Decisões aprovadas (2026-10-27)

Todas as propostas abaixo foram aprovadas como estão. Esclarecimentos do usuário, que valem como regra:

- **Vencida:** tarefa `pendente` cujo prazo já passou no horário local aplicável. Concluídas e canceladas nunca entram no contador.
- **Reabrir** uma tarefa concluída ou cancelada muda o estado para `pendente`, limpa `concluida_em` ou `cancelada_em` e preserva todos os eventos anteriores. É uma ação explícita e registrada (`tarefa_eventos` e linha do tempo do cliente).
- **D6:** o evento vai na mesma transação da operação e não leva texto livre.
- **D7:** sem notificações externas.
- **D10:** P1 continua como bloqueio explícito para dados reais; os dados restantes não são declarados anônimos.


| # | Pergunta | Decisão aprovada | Alternativas descartadas |
|---|---|---|---|
| D1 | A que a tarefa se liga? | Sempre a um **cliente** (obrigatório) e, opcionalmente, a uma **oportunidade desse mesmo cliente**. Proposta minha: o briefing não define o vínculo. | Tarefas avulsas, sem cliente; só cliente, sem oportunidade |
| D2 | Tipos | `ligacao`, `reuniao`, `mensagem`, `retorno` (os quatro do briefing) | Acrescentar `outro` (sugestão, fora do briefing) |
| D3 | Prazo | Data **e hora** obrigatórias (`datetime-local`), guardadas em UTC | Só data (vence no fim do dia local); hora opcional |
| D4 | Prioridades | `baixa`, `normal` (padrão), `alta` | Outra escala |
| D5 | Estados | `pendente` → `concluida` ou `cancelada`. **Reabrir** volta para `pendente` e fica no histórico | Sem reabertura; sem `cancelada` (só excluir) |
| D6 | Histórico de conclusão | Tabela `tarefa_eventos` só de acréscimo (criação, conclusão, cancelamento, reabertura), com a data de cada uma, como as `movimentacoes` da Fase 03; e um evento sem texto livre na linha do tempo do cliente, no mesmo commit (como R9) | Só `concluida_em`, sem histórico de reaberturas |
| D7 | Alertas de vencidas | Calculados a cada página: um contador "Tarefas (N vencidas)" na navegação, uma seção "Vencidas" no topo de `/tarefas` e um aviso na página do cliente e da oportunidade. Vencida = `pendente` com `prazo` no passado | Só a lista filtrada, sem contador na navegação |
| D8 | Edição e exclusão | Edição (título, tipo, prioridade, prazo, descrição, oportunidade) só enquanto `pendente`; **sem exclusão** (cancelar em vez de apagar) | Permitir excluir |
| D9 | "Agenda" do nome da fase | **Agenda = lista ordenada por prazo**, com filtro de período. Sem calendário em grade (exigiria JavaScript ou uma tela nova não pedida no 7.4) | Grade de calendário mensal sem JavaScript (estimativa extra de cerca de 4 h) |
| D10 | Anonimização do cliente | Apaga título e descrição das tarefas dele (texto livre). Tipo, prioridade, estado e datas ficam, sob a mesma pendência **P1** (retenção) já registrada; não são declarados anônimos | Apagar também as datas |

## Requisitos excluídos (e por quê)

- Envio de mensagens, lembretes por e-mail, WhatsApp ou notificações do sistema: proibidos pelo briefing nesta versão.
- Recorrência de tarefas, responsável e atribuição a outra pessoa: não estão no 7.4 (o responsável é "futura expansão" no 7.3).
- Indicador de "tarefas atrasadas" no dashboard: Fase 06 (7.1). A Fase 04 só deixa a consulta pronta no serviço.
- Gerar uma interação automaticamente ao concluir uma ligação ou reunião: **sugestão** (ver abaixo), fora do briefing.
- F, G, CPF/CNPJ/telefone, `certifi`, B1 e P1: fora do escopo desta fase.

## Sugestões de melhoria (fora do escopo por decisão do usuário: S-a, S-b e S-c não entram)

- **S-a:** ao concluir uma tarefa do tipo ligação ou reunião, oferecer o registro de uma interação na linha do tempo com o resumo.
- **S-b:** tipo `outro`.
- **S-c:** corrigir o erro 500 de `/clientes/{id}` com id enorme usando o mesmo `IdDep` do funil. São cerca de 4 linhas, mas é um defeito antigo fora do escopo, por isso fica no backlog até você decidir.

## Restrições globais

- Datas em UTC no banco; a tela mostra no fuso do computador. Os limites de dia usam `intervalo_utc` (regras do sistema para cada data, ADR 0006 P3).
- Listagens com limite: 20 por página em `/tarefas`, até 50 na página do cliente e da oportunidade, até 200 eventos por tarefa.
- Rotas finas; Pydantic com `extra="forbid"`; CSRF em todo POST; 303 depois de POST bem-sucedido; ids no caminho com `IdDep` (de 1 a 2^63 − 1); sem JavaScript; CSP atual.
- Acessibilidade no nível das Fases 02 e 03: rótulos, erros no campo com "Erro:", foco visível, alvos de 44 px, estado e prioridade em texto (nunca só cor), sem rolagem horizontal em 320 px.
- Testes só com dados fictícios e banco temporário, nunca `data/`. Arquivos com menos de 350 linhas. Sem dependência nova; sem tocar em `pyproject.toml` nem em `uv.lock`.

## Pontos de atenção (cada um vira teste na etapa dona)

1. "Vencida" na virada do prazo: uma tarefa com prazo daqui a 1 minuto não está vencida; com prazo 1 minuto atrás, está. O teste injeta o "agora" e não depende do relógio. (Etapa 3)
2. Envio duplo de "Concluir": um evento só, e `concluida_em` não muda na segunda vez. (Etapa 3)
3. Oportunidade de **outro** cliente informada no formulário → erro no campo, nada gravado (IDOR). (Etapas 3 e 4)
4. Prazo digitado sem fuso (`datetime-local`) é hora local: 23h30 local de 31/10 entra no dia 31 no filtro, não no dia 1º UTC. (Etapa 3)
5. Cliente anonimizado: criar, editar, concluir, cancelar e reabrir dão 409; título e descrição somem dos bytes do `.db` e do `-wal`. (Etapas 3 e 4)

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/salesos/periodo.py` (movido de `features/oportunidades/periodo.py`) | `intervalo_utc`, compartilhado pelo funil e pelas tarefas (Etapa 1) |
| `src/salesos/formularios.py` | passa a ter o `IdDep` compartilhado (hoje no router do funil) |
| `src/salesos/features/tarefas/models.py` | `Tarefa`, `TarefaEvento`, `TIPOS_TAREFA`, `PRIORIDADES`, `ESTADOS` |
| `.../tarefas/schemas.py` | `TarefaIn`, `FiltroTarefas` |
| `.../tarefas/service.py` | regras D1–D10, listagens com limite, contagem de vencidas |
| `.../tarefas/router.py` | rotas finas |
| `src/salesos/web/templates/tarefas/*.html` | lista (agenda), detalhe, formulário |
| `migrations/versions/0004_tarefas.py` | tabelas, CHECKs, índices, FKs (`down_revision = "0003"`) |
| `clientes/service.py` | `anonimizar_cliente` limpa as tarefas (D10) |
| `clientes/detalhe.html`, `oportunidades/detalhe.html`, `base.html` | seções "Tarefas" e contador de vencidas na navegação |
| `docs/decisions/0007-tarefas.md` e documentos existentes | documentação |

## Modelo proposto (Etapa 2)

**`tarefas`:**
- Colunas:
  - `id`;
  - `cliente_id` (FK `RESTRICT`, obrigatório);
  - `oportunidade_id` (FK `RESTRICT`, opcional);
  - `tipo`;
  - `titulo` (de 1 a 200 caracteres);
  - `descricao` (até 5.000 caracteres);
  - `prioridade` (padrão `normal`);
  - `prazo` (UTC, obrigatório);
  - `estado` (padrão `pendente`);
  - `concluida_em`;
  - `cancelada_em`;
  - `created_at`;
  - `updated_at`.
- Índices: `(estado, prazo)`, `(cliente_id)` e `(oportunidade_id)`.
- CHECKs:
  - tipo, prioridade e estado na lista;
  - `concluida_em` preenchida se e somente se `estado = 'concluida'`;
  - `cancelada_em` preenchida se e somente se `estado = 'cancelada'`.
- Que a oportunidade pertença ao mesmo cliente é garantido pelo serviço, porque um CHECK do SQLite não consulta outra tabela.

**`tarefa_eventos`:**
- Colunas: `id`, `tarefa_id` (FK `RESTRICT`), `acao` (`criada`, `concluida`, `cancelada` ou `reaberta`) e `ocorrida_em`.
- Índice: `(tarefa_id, ocorrida_em)`.
- Só de acréscimo: nenhuma função nem rota edita ou apaga um evento.

## Rotas propostas (Etapa 4)

| Método e caminho | Faz |
|---|---|
| `GET /tarefas` | Agenda: seção "Vencidas" e depois a lista ordenada por prazo; filtros `estado`, `prioridade`, `tipo`, `de`, `ate`; 20 por página |
| `GET /tarefas/nova?cliente_id=&oportunidade_id=` e `POST /tarefas` | Criar |
| `GET /tarefas/{id}` | Detalhe e histórico de conclusão |
| `GET /tarefas/{id}/editar` e `POST /tarefas/{id}` | Editar (só pendente) |
| `POST /tarefas/{id}/concluir`, `/cancelar`, `/reabrir` | Mudar estado |

## Etapas

Cada etapa termina com a verificação completa e, depois da aprovação, commit e push automáticos conforme o `AGENTS.md`. As durações são **estimativas**, não medições: não há registro do tempo gasto nas fases anteriores.

### Etapa 0 — ADR 0007 (estimativa: 0,5 h)
- D1–D10 conforme aprovadas e o impacto em backups (B1).
- Aceite: ADR revisado; nenhum código.

### Etapa 1 — Compartilhar período e `IdDep` (estimativa: 1 h)
- Mover `intervalo_utc` para `src/salesos/periodo.py` e `IdDep` para `src/salesos/formularios.py`, sem mudar comportamento.
- Aceite: os mesmos testes coletados antes e depois (comparação de IDs; 451 hoje); funil intacto.

### Etapa 2 — Modelo e migração 0004 (estimativa: 2 h)
- Testes com SQL direto, sempre em banco temporário:
  - cada CHECK (estado e datas coerentes; tipo, prioridade e estado fora da lista);
  - FKs `RESTRICT` (não apagar cliente, oportunidade ou tarefa com eventos);
  - `upgrade` → `alembic check` → `downgrade 0003` → `upgrade` de novo, preservando clientes e oportunidades;
  - backup da `0003` recusado **sem** `--migrar` depois da `0004`, e restaurado **com** `--migrar` (regressão de B1, já automática);
  - backup novo aprovado pela checagem de estrutura.
- Aceite: testes passando; mutação de pelo menos um CHECK detectada.

### Etapa 3 — Serviço e schemas (estimativa: 3,5 h)
- `TarefaIn`:
  - `prazo` vindo de `datetime-local` é interpretado no fuso do computador (reusa `hora_local`);
  - campos internos (`estado`, `concluida_em`, `cliente_id`) recusados;
  - mensagens no campo.
- Funções do serviço:
  - `criar_tarefa`;
  - `atualizar_tarefa` (só pendente);
  - `concluir_tarefa`;
  - `cancelar_tarefa`;
  - `reabrir_tarefa`;
  - `obter_tarefa`;
  - `listar_tarefas`;
  - `tarefas_vencidas`;
  - `contar_vencidas`;
  - `tarefas_do_cliente`;
  - `tarefas_da_oportunidade`;
  - `eventos`.
- Cada função tem um único commit com a operação, o evento da tarefa e o evento do cliente.
- Testes:
  - pontos de atenção 1–5;
  - repetir o mesmo estado não gera nada;
  - editar uma tarefa concluída ou cancelada → erro;
  - oportunidade de outro cliente → erro;
  - histórico imutável depois de uma sequência completa;
  - eventos do cliente sem título nem descrição (sentinela);
  - falha injetada no evento desfaz tudo;
  - limites;
  - ordem por prazo;
  - filtro de período local → UTC (com a fixture de fuso; pulado no Windows);
  - D10 nos bytes do `.db` e do `-wal`.
- Aceite: testes e mutações detectados (vencida com `<=` no lugar de `<`, conclusão duplicada, oportunidade de outro cliente aceita, evento com título, anonimização sem limpar a descrição).

### Etapa 4 — Rotas e telas (estimativa: 3,5 h)
- Rotas da tabela acima.
- Seções "Tarefas" no cliente e na oportunidade, com "Nova tarefa" já vinculada.
- Contador de vencidas na navegação, em texto (por exemplo "Tarefas, 3 vencidas"), não só um ponto colorido.
- Testes:
  - CSRF em todo POST novo, com o percurso das rotas usando ids reais;
  - GET sem efeito (comparando o dump completo do banco);
  - XSS escapado em título e descrição;
  - 303;
  - 404/409 sem dados pessoais;
  - 422 no campo (prazo inválido, oportunidade de outro cliente, filtros invertidos ou inválidos);
  - id enorme → 422, não 500.
- Aceite: testes passando; arquivos abaixo de 350 linhas. Se `clientes/router.py` (279) ou `clientes/detalhe.html` (153) se aproximarem do limite, dividir por responsabilidade.

### Etapa 5 — Acessibilidade e revisões (estimativa: 2 h)
- Auditoria no Chromium com o mesmo roteiro da Fase 03 (contraste, foco, alvos de 44 px, rótulos, um `h1`, sem rolagem horizontal nem erro de CSP; 320/390/768/1440 px), dados fictícios no scratchpad.
- Revisão de segurança independente (prompt 13 do Toolkit) e revisão geral da fase (`superpowers:requesting-code-review`).
- Aceite: nenhum achado crítico, alto ou médio sem correção.

### Etapa 6 — Documentação (estimativa: 1 h)
- ADR 0007 final; arquitetura; privacidade (D10 e P1); qualidade (contagens, incluindo o resultado esperado no Windows calculado pelos testes pulados, **como estimativa**); fases; onboarding; `PRODUCT.md`; `AGENTS.md`; checklist B com os itens das tarefas.
- Aceite: os documentos distinguem o implementado do pendente; Windows, B1 e P1 continuam como bloqueios para dados reais.

**Total estimado: cerca de 13,5 h de trabalho do agente** (mais cerca de 4 h se D9 escolher a grade de calendário), sem contar esperas por aprovação.

## Dependências

- **Funcionais:** clientes (Fase 02) e oportunidades (Fase 03). D1 e D10 dependem de `anonimizar_cliente` e de `cliente_editavel`.
- **Técnicas:**
  - `formularios.py` (`hora_local`, `validar`, `Mensagem`);
  - `periodo.intervalo_utc`;
  - `registrar_evento`;
  - o padrão de teste de rotas da Fase 03;
  - a migração `0003` como `down_revision`.

## Riscos

- **B1 e a migração `0004`:** B1 já existe (`restore --migrar`). O teste de regressão da cadeia (`test_every_previous_revision_can_be_migrated_and_restored`) passa a incluir a `0003` automaticamente quando a `0004` existir. Se a `0004` quebrar a restauração de backups antigos (por exemplo, uma migração de dados que falha com linhas antigas), a suíte falha. Critério de aceite da Etapa 2: esse teste passando com a `0004`.
- **Fuso:**
  - o prazo com hora e o "vencida" dependem do relógio e do fuso do computador;
  - no Windows, a precisão histórica (P3) continua não verificada;
  - os testes injetam o "agora", e os de fuso são pulados no Windows.
- **Escopo:** pressão para lembretes, recorrência e calendário em grade. Ficam fora sem nova aprovação.
- **Tamanho de arquivo:** `clientes/router.py` e `clientes/detalhe.html` crescem com mais uma seção; a Etapa 4 prevê dividir se for preciso.

## Ordem de B1

Decidida pelo usuário: B1 antes da Fase 04. Concluído no Linux (commits `0e78278`, `88011a1`, `47c20f7`, `58c87b4`); a confirmação no Windows está no item 17 da checklist B.

## Backlog de defeitos antigos (fora do escopo; impacto avaliado)

| Item | Impacto | Relação com a Fase 04 |
|---|---|---|
| `/clientes/{id}` com id enorme → 500 | Baixo: só com URL digitada à mão; não vaza dado | As rotas novas usam `IdDep` e não repetem o defeito; S-c corrige o antigo se aprovado |
| A checagem de estrutura do backup não compara o texto dos CHECKs | Médio para backups forjados; nulo para backups feitos pelo próprio SalesOS | As tabelas novas também ficam sujeitas; corrigir é hardening próprio |
| `alembic upgrade` e servidor fora do `salesos` sem trava | Baixo, num único usuário | A `0004` precisa de `alembic upgrade` com o servidor desligado, como já está documentado |
| F (paginação da linha do tempo) e G (páginas de erro em HTML) | UX | Os eventos de tarefa aumentam a linha do tempo do cliente; F fica mais útil |
| `certifi` | Baixo, só no ambiente de desenvolvimento | Nenhuma |

## Uso previsto do Toolkit

| Momento | Recurso |
|---|---|
| Plano | `superpowers:writing-plans` (usado nesta execução) |
| Etapas 2 a 4 | `superpowers:test-driven-development`, acionada no início da fase; mutações manuais |
| Falha inesperada | `superpowers:systematic-debugging` |
| Etapa 4 | `frontend-design` para a agenda |
| Etapa 5 | `design:accessibility-review`, prompt 13 do Toolkit (revisor independente), `superpowers:requesting-code-review` |
| Antes de declarar pronto | `superpowers:verification-before-completion` |
| API de biblioteca | Context7, se autenticado; senão documentação oficial e código em `.venv` (limitação registrada) |
