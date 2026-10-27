# Privacidade e dados pessoais

Este documento descreve o que o SalesOS **faz hoje** com dados pessoais (Fases 02 a 04 e estabilização) e o que ele **não** consegue garantir. Não é parecer jurídico sobre a LGPD.

## Quais dados pessoais existem

| Onde | Dados |
|---|---|
| Cliente | nome ou razão social, nome fantasia, e-mail, observações |
| Contato | nome, cargo, e-mail |
| Interação | resumo livre do que aconteceu (pode conter qualquer coisa que for digitada) |
| Oportunidade (Fase 03) | título, observações e detalhe do motivo de perda (texto livre, pode conter dados pessoais); valor, etapa e datas (dados comerciais ligados ao cliente) |

**Não existem** no sistema: CPF, CNPJ e telefone. Ficam bloqueados até que as regras oficiais (Receita Federal e Anatel) sejam lidas, documentadas e aprovadas (decisões D6, D11 e D12). A coluna `documento` existe no banco, mas nenhum formulário a preenche.

## Onde os dados ficam

- **Banco:** `data/salesos.db` (com os arquivos `-wal` e `-shm` enquanto o servidor roda).
- **Backups:** `data/backups/` (ou `SALESOS_BACKUP_DIR`): cada `salesos-<data>.db` é uma cópia completa do banco.
- **Cópias de restauração:** ao restaurar, o banco anterior fica como `data/salesos.db.pre-restore-<data>` e um backup de segurança `data/backups/pre-restore-<data>.db`. Se uma restauração for desfeita, o banco que falhou fica como `data/salesos.db.failed-<data>`.
- **Backups migrados (`restore --migrar`):** `data/backups/migrado-<data>.db` (0600 em POSIX) guarda os dados do backup **antigo** que foi migrado, mas leva a data da migração no nome. Uma pasta `data/backups/.migracao-*` só sobra se a migração for interrompida à força; ela contém uma cópia completa do backup antigo.
- Nada disso vai para o Git (`/data/` e `*.db.*` estão no `.gitignore`).
- O SalesOS **nunca apaga** backups nem cópias automaticamente (D7). Cada cópia guarda os dados pessoais do momento em que foi feita.

## Proteções em uso

- O servidor só escuta em `127.0.0.1` e recusa outros nomes de host.
- **Eventos** da linha do tempo registram só a ação e o nome dos campos ("Cliente atualizado: email, nome"), nunca os valores (D4). Eventos de oportunidades levam só o número, a ação e a etapa: nunca título, observações, detalhe do motivo nem valor (R9). Eventos de tarefas levam só o número e a ação ("Tarefa #12 concluída"), e na edição o nome dos campos: nunca título nem descrição (D6, ADR 0007).
- **Logs:** o log de acesso do servidor está desligado (a URL da busca traria nomes e e-mails), e os erros do banco não levam os valores dos parâmetros.
- **Navegador:** todas as páginas saem com `Cache-Control: no-store`, para não ficarem guardadas no cache depois de uma anonimização.
- **Permissões (Linux e macOS):** banco, backups e cópias com `0600` e a pasta de backups com `0700`. **No Windows** os bits POSIX não se aplicam; a proteção depende das permissões (ACL) da pasta onde o projeto está. Mantenha o projeto dentro da sua pasta de usuário. Não verificado no Windows.
- O manifesto de cada backup (`.db.json`) guarda só nome do arquivo, SHA-256, revisão do esquema, tamanho e data.

## Anonimização

Na tela do cliente, em **Anonimizar cliente**, digitando o número do cliente para confirmar.

O que acontece, de forma irreversível **dentro do SalesOS** (D9):

| Item | Resultado |
|---|---|
| Nome | vira "Cliente anonimizado #&lt;número&gt;" |
| Nome fantasia, e-mail, observações, documento | apagados |
| Contatos | removidos |
| Interações registradas por pessoas | o resumo vira "[conteúdo removido]"; tipo e data ficam |
| Eventos do sistema | ficam (não têm dados pessoais) e ganham "Cliente anonimizado" |
| Oportunidades | título vira "Oportunidade #&lt;número&gt;"; observações e detalhe do motivo de perda apagados; **valor, etapa, motivo da lista e datas ficam** (ver pendência abaixo) |
| Histórico de etapas | fica como está (só etapas e datas) |
| Tarefas | título vira "Tarefa #&lt;número&gt;"; descrição apagada; **tipo, prioridade, estado, prazo e datas ficam** (ver pendência abaixo); saem da agenda e do contador de vencidas e só aparecem na página do cliente |
| Histórico das tarefas | fica como está (só ações e datas) |
| Busca | os dados antigos não são mais encontrados |
| Alterações | o cliente passa a recusar qualquer mudança |

No arquivo do banco, `secure_delete` zera o conteúdo apagado e um checkpoint esvazia o `-wal`. Um teste automatizado confirma que os valores fictícios usados no teste não ficam nos bytes do `.db` nem do `-wal`.

### Limites da anonimização (leia antes de usar)

- **Não é apagamento forense.** Podem continuar existindo cópias em: backups e cópias de restauração feitos antes, Lixeira do Windows, histórico de versões do OneDrive ou de outro serviço de sincronização, cópias de sombra do Windows (Restauração do Sistema), cópias manuais e setores antigos de SSD.
- Se um leitor estiver com o banco aberto no momento, o checkpoint do `-wal` pode ficar incompleto; o servidor registra um aviso (sem dados pessoais) e o conteúdo antigo some no próximo checkpoint completo.
- **Restaurar um backup antigo traz os dados de volta.** Por isso a restauração recusa um backup em que um cliente hoje anonimizado ainda tinha dados, e só aceita com `--aceitar-reintroducao`. Clientes criados depois do backup não disparam esse aviso.

## Política de retenção após a anonimização (P1, aprovada em 2026-10-27)

Definida pelo responsável pelo tratamento. Este documento descreve a política e o comportamento do software; não é parecer jurídico sobre a LGPD.

**Finalidade.** Depois de anonimizar um cliente, os registros que sobram são mantidos **só** para indicadores comerciais históricos e análise operacional interna da WE TECH. Eles **não podem** ser usados para contatar, traçar perfil ou tomar decisões sobre a pessoa.

**O que fica durante o prazo**, ligado ao número do cliente:
- oportunidades: valor, etapa, motivo da lista, datas e histórico de etapas;
- tarefas: tipo, prioridade, situação, prazo, datas e histórico de ações;
- eventos da linha do tempo sem dados pessoais (por exemplo, "Tarefa #12 concluída").

**Esses dados não são declarados anônimos**: continuam ligados ao registro do cliente, e a combinação com outras informações pode permitir identificá-lo.

**Prazo: 12 meses contados da anonimização** (data gravada em `anonimizado_em`, contada em meses do calendário; um cliente anonimizado em 29/02 entra no dia 28/02 do ano seguinte).

**Expurgo: manual, pelo comando `uv run salesos expurgar`** (ADR 0008). Nada roda sozinho: nem o servidor, nem uma rota, nem uma tarefa agendada chama o expurgo.
1. Com o servidor desligado (o comando pega a trava do banco), rode `uv run salesos expurgar`.
2. Ele lista os clientes anonimizados há 12 meses ou mais (só o número e a data) e quantos registros de cada tipo saem.
3. Só apaga se você digitar exatamente `EXPURGAR <quantidade>`. Qualquer outra resposta não apaga nada.
4. Apaga, numa única transação, o cliente e **tudo** o que é dele: interações e eventos da linha do tempo, contatos, oportunidades, histórico de etapas, tarefas e histórico das tarefas. Não guarda agregados.
5. Se algum registro de **outro** cliente apontar para um expurgado (dado inconsistente), recusa tudo e não apaga nada.
6. Rodar de novo é seguro: o que já saiu não aparece mais.
7. Com outro programa usando o banco (DB Browser, por exemplo), o comando recusa e não apaga nada. Se um programa abrir o banco durante o expurgo, os registros saem, mas o comando avisa que o **expurgo físico não terminou** (o conteúdo apagado pode continuar no arquivo `-wal`) e não diz "concluído": feche os programas e rode de novo até ver "O arquivo -wal está vazio".

Sugestão de rotina: rodar uma vez por mês e guardar a saída do comando como registro do expurgo (ela não tem nomes).

**Consequência para os indicadores:** depois do expurgo, os números históricos (por exemplo, vendas ganhas num mês antigo, quando houver dashboard na Fase 06) **diminuem**, porque os registros saem e nenhum agregado é guardado.

**Backups: retenção máxima de 12 meses, com rotação manual.**
1. Uma vez por mês, apague de `data\backups\` (e das cópias fora do computador) os backups com mais de 12 meses: `salesos-*.db`, `pre-restore-*.db` e `migrado-*.db` (pela data **dos dados**: um `migrado-*` herda a data do backup que o originou), cada um com o seu `.db.json`; e também `data\salesos.db.pre-restore-*` e `data\salesos.db.failed-*` com mais de 12 meses. Antes de apagar, garanta que exista um backup recente e verificado.
2. **Em até 30 dias depois de cada anonimização**, tire do conjunto restaurável as cópias **anteriores** a ela que possam trazer de volta os dados pessoais (o procedimento da seção seguinte).
3. **Se for preciso restaurar uma cópia antiga:** antes, anote os números dos clientes anonimizados (na lista de clientes arquivados, aparecem como "Cliente anonimizado #N"). Restaure com `--aceitar-reintroducao`; com o servidor de pé, anonimize de novo **cada um** desses clientes e confira que a busca pelos dados antigos não acha nada. Só então volte a usar o sistema.

O SalesOS não apaga backups sozinho (D7): a rotação é feita por você.

## Backups antigos com dados de clientes anonimizados

Quando um cliente pede a exclusão dos dados e você o anonimiza, os backups anteriores continuam com os dados. Procedimento manual:

1. Liste os backups e cópias com data **anterior** à anonimização: `data\backups\salesos-*.db`, `data\backups\pre-restore-*.db`, `data\salesos.db.pre-restore-*` e `data\salesos.db.failed-*`, além de cópias em outros lugares (pendrive, nuvem). Os `data\backups\migrado-*.db` e as pastas `data\backups\.migracao-*` entram na lista **mesmo com data posterior** se vieram de um backup anterior à anonimização: a data no nome é a da migração, não a dos dados.
2. Verifique se existe obrigação legal ou contratual de guardar alguma delas.
3. Se não existir, apague esses arquivos (e o `.db.json` de cada backup), esvazie a Lixeira e confira as pastas sincronizadas (OneDrive guarda versões antigas).
4. Faça um backup novo (`uv run salesos backup`) para continuar tendo uma cópia recente.

Antes de apagar, garanta que exista pelo menos um backup recente e verificado.

## Dados de teste

Testes e verificações usam só dados fictícios e bancos temporários. Nenhum teste lê `data/`.
