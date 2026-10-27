# 0006 — Oportunidades e funil

**Status:** aceita (Fase 03; plano `docs/superpowers/plans/2026-10-25-fase-03-funil.md`, aprovado em 2026-10-25)

**Contexto:** o briefing (7.3) pede oportunidades por cliente, etapas do funil, valor, datas, motivos de perda, histórico das mudanças de etapa e filtros por status e período. Dashboard, tarefas e propostas dependem disso.

**Decisão:**
- Pacote `features/oportunidades/` e migração `0003` (depois de `0002`), com duas tabelas:
  - `oportunidades`;
  - `movimentacoes`, só de acréscimo: nenhuma função nem rota edita ou apaga uma movimentação.
- Etapas fixas:
  - abertas: `novo_lead`, `qualificacao`, `proposta_enviada`, `negociacao`;
  - finais: `ganha`, `perdida`.
- "Venda ganha" é só **oportunidade ganha**. Não equivale a contrato assinado, cobrança registrada nem valor recebido (briefing 7.8).
- Regras R1–R10 do plano aprovado:
  - Criar grava `novo_lead`, a movimentação `NULL → novo_lead` e o evento "Oportunidade #N criada", na mesma transação.
  - **R1:** movimentação livre entre as etapas abertas.
  - **R2:** as etapas finais são finais. Reabrir exige escolher uma etapa aberta e limpa `fechada_em`, `motivo_perda` e `motivo_detalhe`. Para ir de ganha a perdida (ou o contrário), é preciso reabrir antes (P2). O histórico nunca é alterado.
  - **R3:** ganhar exige `valor_centavos > 0`, inclusive ao editar uma oportunidade já ganha.
  - **R4:** perder exige motivo da lista.
  - **R5:** mover para a etapa atual não gera nada.
  - **R6:** cliente anonimizado recusa criar e alterar (409); cliente arquivado aceita.
  - **R7 (período):** a data de referência é a abertura para as abertas e o fechamento para ganhas e perdidas. Os dias do calendário local viram um intervalo UTC `[início de de, início de ate+1)`. Só uma das datas basta; intervalo invertido ou data inválida → 422.
  - **R8:** valores em centavos `int`, de 0 a 10¹². Entrada só em pt-BR; sem `float`, sinal, notação científica ou arredondamento.
  - **R9:** eventos na linha do tempo do cliente, no mesmo commit da operação, sem valor, título, observações ou motivo detalhado.
  - **R10:** anonimizar o cliente apaga título, observações e detalhe do motivo. Valor, etapa e datas ficam. Esses dados **não são declarados anônimos**: a finalidade e o prazo de retenção são a pendência P1, em `docs/privacy.md`.
- **Fuso (P3):** a conversão do dia local para UTC usa a biblioteca padrão. Um `datetime` ingênuo à meia-noite, com `.astimezone(UTC)`, aplica as regras do sistema operacional **para aquela data**, não o offset de hoje.
  - Não se usa `zoneinfo`: o `uv.lock` não tem `tzdata`, o Windows não traz a base IANA e a biblioteca padrão não descobre o nome IANA do fuso local.
  - Verificado no Linux contra o `zoneinfo` (America/Sao_Paulo, horário de verão de 2018–2019, incluindo a meia-noite inexistente de 2018-11-04, cujo dia começa às 01:00 local).
- **Responsável comercial:** fora desta versão (briefing: "futura expansão"). Ponto de extensão: uma coluna `responsavel_id` em `oportunidades`, numa migração própria, quando houver usuários (ADR futuro de autenticação).

**Consequências e limites:**
- **B1 (bloqueia dados reais):** depois da `0003`, o `salesos restore` recusa backups da `0002`, por desenho. Antes do uso real, precisa existir um procedimento testado para restaurar backups antigos e migrá-los, com verificação de integridade. Ele não fez parte da Fase 03; foi implementado depois como `salesos restore <backup> --migrar` (ADR 0005), testado só no Linux.
- **P1 (bloqueia dados reais):** finalidade e prazo de retenção dos dados comerciais de clientes anonimizados ainda não estão definidos. Isto não é parecer jurídico.
- **Fuso no Windows: não verificado.** Lá, a precisão histórica depende das regras de fuso do Windows usadas pelo runtime do Python; não é garantida para datas antigas com horário de verão. Os testes de horário de verão histórico mudam o fuso do processo com `time.tzset()`, que só existe em POSIX, então são pulados no Windows.
- O funil mostra até 20 oportunidades por coluna; a lista completa é paginada (20).
- Não há exclusão de oportunidade; a correção é por edição, que gera evento.
