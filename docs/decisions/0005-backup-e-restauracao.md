# 0005 — Backup, restauração e recuperação

**Status:** aceita (Fase 02)

**Contexto:** o banco é um arquivo SQLite em modo WAL num computador Windows. Copiar a pasta com o servidor ligado pode gerar uma cópia inconsistente, e uma restauração interrompida (queda de energia, processo encerrado) não pode perder o banco.

**Decisão:**
- **Backup** (`uv run salesos backup`): API de backup do SQLite (cópia consistente mesmo com o servidor ligado), arquivo em modo DELETE, `integrity_check`, SHA-256 e revisão do esquema num manifesto `.db.json` sem dados pessoais. Nunca sobrescreve e nunca apaga (D7). Falha no meio não deixa arquivos parciais.
  - Se outro programa segurar o banco com bloqueio exclusivo, o backup desiste depois de `ESPERA_BLOQUEIO` (10 s; até cerca de 15 s somando a espera da conexão) com a mensagem "bloqueado por outro programa" (Fase 02.1, item D). Sem esse prazo, `Connection.backup` do Python repetiria a tentativa para sempre.
- **Verificação de um backup antes de restaurar:** manifesto presente, SHA-256 igual, `integrity_check` ok, revisão igual ao head e **estrutura igual** à do head (tabelas, colunas, índices e as colunas de cada um, views, triggers e chaves estrangeiras), obtida rodando as migrações reais num banco temporário. Arquivos externos são abertos com `trusted_schema=OFF`.
- **Restauração** (`uv run salesos restore <arquivo>`): trava cooperativa (`data/salesos.lock`, `flock` no Linux, `msvcrt` no Windows) que o servidor e as migrações também seguram; diário de estados `salesos.db.restore.json` gravado e sincronizado antes de cada passo: `validating` → `quiesced` → `safety_backed_up` → `original_moved` → `swapped` → `verified`.
  - O banco é "aquietado" sem esperar: `BEGIN IMMEDIATE` (escritores), checkpoint completo (leitores) e saída do WAL (falha com qualquer conexão aberta, inclusive ociosa). Qualquer sinal de uso recusa antes de mudar algo.
  - Só `SQLITE_BUSY`/`SQLITE_LOCKED` (e os códigos estendidos) viram "Feche os programas". Outro erro do SQLite (banco não migrado, erro de disco, permissão) é mostrado com o nome do erro real, também sem alterar nada (Fase 02.1, item D). A regra fica em `backup.bloqueado()`.
  - Backup de segurança verificado e o original preservado como `.pre-restore-<data>` antes da troca.
  - Recusa um backup que traria de volta dados de cliente anonimizado, salvo `--aceitar-reintroducao`.
- **Recuperação** (`uv run salesos recover`): idempotente; decide olhando os arquivos reais. Antes de `verified`, volta o original e guarda o banco novo como `.failed-<data>`; depois de `verified`, mantém o restaurado. Nunca apaga.
- O diário é conferido antes de qualquer movimentação (Fase 02.1, item E): carimbo no formato de `carimbo()`, estado conhecido, banco igual ao atual e caminhos de `staging` e `.pre-restore` iguais aos derivados do banco e do carimbo. Os caminhos usados são sempre os derivados, nunca os lidos. Diário ilegível ou adulterado → `recover` recusa sem mover nada e o diário fica pendente para análise manual.
- O servidor não inicia com um diário pendente.
- **Backup de revisão anterior (B1, `restore --migrar`, módulo `migracao_backup.py`):** sem a opção, a recusa por revisão diferente continua igual. Com `--migrar`:
  1. Verifica manifesto, SHA-256 e integridade do backup; o original só é lido.
  2. Aceita só revisões anteriores reconhecidas na cadeia do Alembic; uma desconhecida ou mais nova é recusada. Se o backup já estiver na revisão atual, restaura direto.
  3. Copia o backup para `<pasta de backups>/.migracao-<carimbo>/` (0700, cópia 0600) e confere o SHA-256 da cópia de novo.
  4. Roda `alembic upgrade head` **só na cópia** (`Config()` sem arquivo e URL da cópia; nunca `SALESOS_DATABASE_URL`).
  5. Gera o backup `migrado-<carimbo>.db` e o verifica **dentro da pasta temporária** (revisão atual e estrutura); só depois o publica na pasta de backups, sem sobrescrever.
  6. Apaga a pasta temporária ao final (sucesso ou erro) e registra um aviso se não conseguir.
  7. Entrega o `migrado-*` ao `restaurar` de sempre, com todas as proteções (estrutura, anonimização, troca atômica, `recover`).
  - Qualquer falha vira "Backup não migrado: ... Nada foi alterado.", sem conteúdo do banco na mensagem. O `recover` relata pastas `.migracao-*` deixadas por interrupção abrupta, sem apagá-las.
  - Um teste percorre toda revisão anterior ao head: uma migração nova que quebre esse caminho (por exemplo, uma migração de dados que só falha com linhas antigas) faz a suíte falhar.

**Invariantes:** em todo momento existe o original intacto (no lugar ou como `.pre-restore`) ou um backup de segurança verificado; toda mudança de estado vai para o disco antes da ação seguinte.

**Consequências e limites:**
- No Linux, um programa que abrir o banco **depois** da sondagem não impede a troca; ele fica com o arquivo antigo (`.pre-restore`). No Windows, a troca falha nesse caso e é desfeita (teste escrito, **não executado**: só roda no Windows).
- A trava só coordena processos do SalesOS: DB Browser e outros programas são detectados pelo SQLite, não pela trava.
- **Quem segura a trava (estabilização, E2):**
  - **A aplicação, ao iniciar:** vale para `uv run salesos` e para `uvicorn salesos.main:create_app --factory` iniciado direto. Enquanto ela estiver de pé, restore, recover, `alembic upgrade` e um segundo servidor no mesmo banco são recusados ("Outro processo do SalesOS..."). Com uma restauração pendente, a aplicação não sobe.
  - **O comando `salesos`, só para a mensagem:** pega e solta a trava antes de chamar o uvicorn. Segurá-la durante o uvicorn faria a aplicação, no mesmo processo, recusar a si mesma (a trava é por descritor de arquivo, não por processo). Entre a checagem e a aplicação há uma janela curta; nela, quem ganha é quem pegar a trava primeiro, e o outro é recusado.
  - **`migrations/env.py`:** segura a trava do banco-alvo durante toda a migração, quando o alvo é um arquivo SQLite. O `restore --migrar` migra uma cópia na pasta temporária, cuja trava fica ao lado da cópia e é apagada com ela.
  - Todo comando do Alembic que abre o banco (inclusive `current` e `history`) pega a trava e é recusado com o servidor ligado; o modo offline (`--sql`) só imprime SQL e não pega.
  - Suportado: um único processo de servidor. `uvicorn --workers N` faria os processos extras falharem na trava.
  - A trava fica em `<banco>.lock` (`with_suffix`): dois bancos com o mesmo nome e extensões diferentes na mesma pasta dividiriam a trava (recusa a mais, nunca a menos). Aceito para um usuário.
  - Verificado no Linux com o servidor real (`salesos` e `uvicorn` em subprocesso); no Windows (`msvcrt`), checklist B, item 22.
- `salesos backup` não pega a trava (para funcionar com o servidor ligado) e recusa quando há restauração pendente.
- Um backup de outra revisão do esquema é recusado sem `--migrar`. Com `--migrar`, só revisões **anteriores** da cadeia são aceitas; um backup de versão mais nova do SalesOS continua recusado.
- O `migrado-<carimbo>.db` fica na pasta de backups com os dados do backup **antigo**, mas com a data da migração no nome: na limpeza manual de dados de clientes anonimizados (`docs/privacy.md`), ele precisa ser tratado como uma cópia antiga.
- Se a publicação do manifesto falhar (inclusive por interrupção com Ctrl+C), o `migrado-*.db` desta execução é apagado. Só uma queda de energia exatamente entre as duas operações de arquivo pode deixar um `migrado-*.db` sem manifesto, que o `restore` recusa ("manifesto ausente").
- Durante a migração, triggers e views do backup antigo podem rodar **na cópia** (o Alembic usa o engine normal). O efeito fica na cópia, e o resultado só é aceito se a estrutura final for a esperada.
- Validado só no Linux; no Windows, o comando entra na checklist B (`docs/setup.md`).
- O SHA-256 detecta arquivo corrompido, não prova a origem (o manifesto não é assinado); a checagem de estrutura cobre o caso de arquivo forjado com objetos extras, com chaves estrangeiras reescritas (`writable_schema`) ou com índices de mesmo nome em outras colunas (estabilização, E3; pelos PRAGMAs, sem texto SQL).
- **Em aberto (estabilização, E3), aguardando decisão do usuário:**
  - **CHECKs reescritos não são comparados.** A sondagem mostrou o SQL das 8 tabelas idêntico num banco criado do zero, num migrado em cadeia desde a `0002` e num migrado pelo `restore --migrar`. Uma comparação só dos CHECKs normalizados foi implementada e **retirada**: a revisão de segurança mostrou um CHECK escondido num comentário e um CHECK enfraquecido pela caixa ou por espaços dentro das aspas passando.
  - **Dados que violam as regras passam:** em modo só leitura, o `integrity_check` do SQLite (3.53.1) não confere CHECKs, e nada roda `foreign_key_check`. Um backup com uma linha que viola um CHECK, ou com um contato sem cliente, é aceito (reproduzido com dados fictícios). Pré-existente desde a Fase 02.
- Backups e cópias acumulam com dados pessoais; a limpeza é manual (`docs/privacy.md`).
