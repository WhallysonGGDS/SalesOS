# B1 — Restaurar backup de revisão anterior (`salesos restore <backup> --migrar`)

> **Aprovado em 2026-10-27 (Opção B).** Escopo: só B1. Sem dependência nova; sem Fases 04–08; só dados fictícios em pastas temporárias.

**Objetivo:** restaurar um backup feito antes de uma migração, migrando uma **cópia temporária** até a revisão atual e entregando o resultado ao `restaurar` que já existe, sem enfraquecer nenhuma proteção.

## Desenho

Novo módulo `src/salesos/migracao_backup.py` (o `restore.py` já tem 310 linhas), com:

- `revisoes_anteriores() -> tuple[str, ...]`: revisões da cadeia do Alembic, da base até a anterior ao head.
- `migrar_backup(arquivo: Path, pasta_backups: Path) -> Path`, que devolve o caminho de um backup verificado na revisão atual:
  1. `verificar_backup(arquivo, exigir_revisao=False)`: manifesto, SHA-256 e `integrity_check`. O original só é lido.
  2. Lê a revisão do backup. Se já for a atual, devolve o próprio arquivo (nada a migrar). Se não estiver em `revisoes_anteriores()` (desconhecida ou mais nova), recusa.
  3. Cria `pasta_backups/.migracao-<carimbo>/` (0700) e copia o backup para lá (0600). Confere de novo o SHA-256 da cópia contra o manifesto, porque o arquivo pode mudar entre a verificação e a cópia.
  4. `alembic upgrade head` **só na cópia** (`Config` sem arquivo, `sqlalchemy.url` da cópia): FK checada e transação única, como em qualquer migração.
  5. `criar_backup(copia, pasta_backups, prefixo="migrado")` e `verificar_backup(novo)`, que exige a revisão atual e a estrutura esperada. Se a verificação falhar, o `migrado-*` desta execução é apagado.
  6. `finally`: apaga a pasta `.migracao-<carimbo>` criada nesta execução, e só ela.
  - Qualquer falha vira `RestauracaoRecusada("... Nada foi alterado.")`, com o nome do tipo de erro e sem conteúdo do banco.
- CLI: `restore --migrar` chama `migrar_backup` e depois `restaurar` sem nenhuma mudança. Sem `--migrar`, nada muda: a mesma recusa e a mesma mensagem.
- `recuperar()` passa a relatar, **sem apagar**, as pastas `.migracao-*` deixadas por uma interrupção abrupta. São só diretórios com esse prefixo exato dentro da pasta de backups.

**Backup migrado mantido:** `pasta_backups/migrado-<carimbo>.db` mais `.db.json`, com permissões 0600 (POSIX). A pasta fica com 0700. Retenção igual à de todos os backups: nunca apagado automaticamente (D7); a limpeza manual está em `docs/privacy.md`.

## Testes (`tests/backup/test_restore_migracao.py`)

- Os seis cenários do scratchpad:
  - válido;
  - alterado depois do manifesto;
  - não é SQLite;
  - objeto estrutural extra;
  - referência órfã;
  - anterior à anonimização.
- Revisão desconhecida ou mais nova.
- Falha injetada durante a migração.
- Em toda falha:
  - banco atual com SHA igual;
  - backup original com SHA igual;
  - nenhuma `.migracao-*` sobrando;
  - nenhum `migrado-*` inválido sobrando.
- Interrupção abrupta simulada (pasta `.migracao-*` deixada): o `recover` relata, não apaga, e ignora nomes parecidos e backups válidos.
- CLI com `--migrar` e sem `--migrar` (recusa inalterada).
- **Regressão da cadeia:** para cada revisão anterior ao head (hoje 0001 e 0002; a 0004 entra sozinha quando existir), o backup migra e restaura. Demonstração: uma migração quebrada temporária faz o teste falhar; sem ela, o teste passa.

## Aceite

- Testes passando; suíte completa, Ruff, formatação e mypy.
- Mutações detectadas: sem a checagem do SHA; migrar o original; sem a limpeza; aceitar revisão desconhecida.
- Revisão de segurança independente sem achado crítico, alto ou médio pendente.
- Documentação: ADR 0005, `docs/onboarding.md` (PowerShell, marcado como não testado no Windows), checklist B, `docs/privacy.md`, `AGENTS.md`, `docs/quality.md` e `docs/phases.md`.
