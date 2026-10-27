# 0008 — Retenção após a anonimização e expurgo manual

**Status:** aceita e implementada no Linux (estabilização pós-Fase 04, E5; política aprovada pelo usuário em 2026-10-27). Windows não verificado.

**Contexto:** a anonimização (Fases 02 a 04) mantém dados comerciais ligados ao cliente (valor, etapa, datas, tipo e situação das tarefas, históricos). A pendência P1 pedia finalidade, prazo e o que acontece ao fim dele, e bloqueava dados reais.

**Decisão:**
- **Finalidade:** indicadores comerciais históricos e análise operacional interna da WE TECH; nunca contatar, traçar perfil ou decidir sobre a pessoa. Os dados não são declarados anônimos.
- **Prazo:** 12 meses do calendário contados de `anonimizado_em` (29/02 vira 28/02 do ano seguinte).
- **Expurgo manual**, módulo `salesos/expurgo.py`, comando `uv run salesos expurgar`:
  - pega a trava do banco (servidor, restore e migração ficam de fora) e recusa com restauração pendente;
  - mostra a abrangência (número do cliente, data da anonimização e quantos registros de cada tipo saem) e só apaga com a resposta exata `EXPURGAR <quantidade>`; qualquer outra resposta, ou entrada vazia, não apaga nada;
  - apaga o cliente e tudo o que é dele, das folhas para a raiz (todas as chaves são RESTRICT): histórico das tarefas → tarefas → histórico de etapas → oportunidades → interações e eventos → contatos → cliente; uma só lista de tabelas e condições serve para contar e para apagar;
  - reconfere o prazo de cada cliente dentro da transação; um único commit; falha no meio desfaz tudo;
  - se um registro de **outro** cliente apontar para um expurgado (tarefa de outro cliente numa oportunidade dele, ou interação com um contato dele; D1 proíbe, o banco não impede), recusa tudo: apagar mexeria no registro de outra pessoa;
  - depois do commit, checkpoint do WAL, como na anonimização (`secure_delete` já zera o conteúdo). Se outro programa estiver lendo o banco (DB Browser, ferramenta de backup), o checkpoint fica incompleto e o comando avisa que os dados apagados podem continuar no `-wal` até o próximo checkpoint;
  - banco ausente: recusa sem criar arquivo; banco não migrado: mensagem com o tipo do erro, sem traceback e sem o SQL;
  - até 200 clientes por execução; o resto aparece na seguinte. Repetir é seguro;
  - relatório só com números (clientes pelo número, contagens em português), sem nomes.
- **Nada roda sozinho:** só o `main.py` chama `expurgar` (teste que percorre o código-fonte).
- **Sem agregados** nesta etapa.
- **Backups:** retenção máxima de 12 meses com rotação manual; cópias anteriores a uma anonimização saem do conjunto restaurável em até 30 dias; restaurar uma cópia antiga exige reaplicar e verificar a anonimização antes de voltar a usar o sistema (procedimento em `docs/privacy.md`).

**Consequências e limites:**
- Os indicadores históricos diminuem depois de cada expurgo (Fase 06 vai mostrar números menores para períodos antigos).
- Backups anteriores continuam com os dados até a rotação; o SalesOS não apaga backups sozinho (D7).
- A rotação dos backups e a reaplicação da anonimização depois de uma restauração antiga são manuais.
- O prazo compara `anonimizado_em` como texto, no formato que o SalesOS grava (UTC, sem fuso). Uma data escrita à mão com fuso (`...-03:00`) seria comparada errado (horas de diferença); o SalesOS nunca grava nesse formato.
- Validado só no Linux; no Windows, checklist B, item 24. Revisão de segurança independente: nenhum caminho apaga registro fora do escopo; achados baixos corrigidos (teste com caminho fixo, aviso de WAL incompleto, banco ausente ou não migrado).
