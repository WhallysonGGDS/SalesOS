# 0005 — Backup, restauração e recuperação

**Status:** aceita (Fase 02)

**Contexto:** o banco é um arquivo SQLite em modo WAL num computador Windows. Copiar a pasta com o servidor ligado pode gerar uma cópia inconsistente, e uma restauração interrompida (queda de energia, processo encerrado) não pode perder o banco.

**Decisão:**
- **Backup** (`uv run salesos backup`): API de backup do SQLite (cópia consistente mesmo com o servidor ligado), arquivo em modo DELETE, `integrity_check`, SHA-256 e revisão do esquema num manifesto `.db.json` sem dados pessoais. Nunca sobrescreve e nunca apaga (D7). Falha no meio não deixa arquivos parciais.
  - Se outro programa segurar o banco com bloqueio exclusivo, o backup desiste depois de `ESPERA_BLOQUEIO` (10 s; até cerca de 15 s somando a espera da conexão) com a mensagem "bloqueado por outro programa" (Fase 02.1, item D). Sem esse prazo, `Connection.backup` do Python repetiria a tentativa para sempre.
- **Verificação de um backup antes de restaurar:** manifesto presente, SHA-256 igual, `integrity_check` ok, revisão igual ao head e **estrutura igual** à do head (tabelas, colunas, índices, views e triggers), obtida rodando as migrações reais num banco temporário. Arquivos externos são abertos com `trusted_schema=OFF`.
- **Restauração** (`uv run salesos restore <arquivo>`): trava cooperativa (`data/salesos.lock`, `flock` no Linux, `msvcrt` no Windows) que o servidor também segura; diário de estados `salesos.db.restore.json` gravado e sincronizado antes de cada passo: `validating` → `quiesced` → `safety_backed_up` → `original_moved` → `swapped` → `verified`.
  - O banco é "aquietado" sem esperar: `BEGIN IMMEDIATE` (escritores), checkpoint completo (leitores) e saída do WAL (falha com qualquer conexão aberta, inclusive ociosa). Qualquer sinal de uso recusa antes de mudar algo.
  - Só `SQLITE_BUSY`/`SQLITE_LOCKED` (e os códigos estendidos) viram "Feche os programas". Outro erro do SQLite (banco não migrado, erro de disco, permissão) é mostrado com o nome do erro real, também sem alterar nada (Fase 02.1, item D). A regra fica em `backup.bloqueado()`.
  - Backup de segurança verificado e o original preservado como `.pre-restore-<data>` antes da troca.
  - Recusa um backup que traria de volta dados de cliente anonimizado, salvo `--aceitar-reintroducao`.
- **Recuperação** (`uv run salesos recover`): idempotente; decide olhando os arquivos reais. Antes de `verified`, volta o original e guarda o banco novo como `.failed-<data>`; depois de `verified`, mantém o restaurado. Nunca apaga.
- O diário é conferido antes de qualquer movimentação (Fase 02.1, item E): carimbo no formato de `carimbo()`, estado conhecido, banco igual ao atual e caminhos de `staging` e `.pre-restore` iguais aos derivados do banco e do carimbo. Os caminhos usados são sempre os derivados, nunca os lidos. Diário ilegível ou adulterado → `recover` recusa sem mover nada e o diário fica pendente para análise manual.
- O servidor não inicia com um diário pendente.

**Invariantes:** em todo momento existe o original intacto (no lugar ou como `.pre-restore`) ou um backup de segurança verificado; toda mudança de estado vai para o disco antes da ação seguinte.

**Consequências e limites:**
- No Linux, um programa que abrir o banco **depois** da sondagem não impede a troca; ele fica com o arquivo antigo (`.pre-restore`). No Windows, a troca falha nesse caso e é desfeita (teste escrito, **não executado**: só roda no Windows).
- A trava só coordena processos do SalesOS: DB Browser e outros programas são detectados pelo SQLite, não pela trava. `uv run alembic upgrade head` e um servidor iniciado fora do `salesos` não pegam a trava.
- `salesos backup` não pega a trava (para funcionar com o servidor ligado) e recusa quando há restauração pendente.
- Um backup de outra revisão do esquema é recusado; restaurar backup antigo depois de uma migração futura exigirá um procedimento próprio, a aprovar.
- O SHA-256 detecta arquivo corrompido, não prova a origem (o manifesto não é assinado); a checagem de estrutura cobre o caso de arquivo forjado com objetos extras. CHECKs e chaves estrangeiras alterados não são comparados.
- Backups e cópias acumulam com dados pessoais; a limpeza é manual (`docs/privacy.md`).
