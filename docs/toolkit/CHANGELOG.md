# Changelog da integração do Toolkit

## 2026-10-19 — Integração inicial (revisão `790a895`)

Ambiente: container Linux na nuvem (Claude Code 2.1.303), clone do repositório `WhallysonGGDS/SalesOS`, branch `claude/practical-bell-w2zwqp`, sem commits anteriores. **Não houve commit, push nem PR.**

### Adicionado

- `tooling/vibe-coding-toolkit/`: cópia integral dos 119 arquivos versionados do Toolkit, sem `.git`, byte a byte idêntica à origem.
- `tooling/vibe-coding-toolkit.sha256`: manifesto de integridade.
- `.claude/settings.json`:
  - marketplaces `claude-plugins-official` e `ponytail`;
  - plugins `superpowers`, `ponytail` e `context7` (escopo projeto);
  - `claudeMdExcludes` para as instruções de mantenedor da cópia;
  - `ask` para `git commit`/`git push`;
  - `deny` para `git reset --hard`, `git clean`, push forçado e leitura de `.env`, `.env.local` e `data/**`.
- `AGENTS.md`: adaptado de `templates/AGENTS.md.template` para Python, mantendo as restrições e o fluxo de aprovação do SalesOS.
- `CLAUDE.md`: ponte `@AGENTS.md` mais regras específicas do Claude Code.
- `.gitignore`: segredos, `data/`, configuração local do Claude e caches Python.
- `.gitattributes`: a cópia do Toolkit sem conversão de fim de linha.
- `docs/toolkit/`: `INSTALLATION.md`, `INVENTORY.md`, `COMPATIBILITY.md`, `USAGE.md` e este arquivo.

### Verificado

Detalhes em INSTALLATION §5.

- Integridade: `diff -r` sem diferenças e `sha256sum -c` com 119 OK.
- Autotestes do Toolkit: 9/9 e 2/2. `validate-docs`: PASS, 614 links/âncoras.
- Plugins: enabled, scope project. Hooks do Superpowers e da Ponytail executados com saída esperada.
- Avaliador de harness numa cópia descartável da fixture: baseline com 5 pass e 2 fail (os 2 fails são intencionais).
- Sessão nova não interativa (`claude -p`), com evidência **autodeclarada pelo agente**, sem controle negativo:
  - identificou o `AGENTS.md`, a política de commit/push, as 6 skills da Ponytail e as 15 do Superpowers;
  - confirmou `PONYTAIL MODE ACTIVE — level: full`;
  - não carregou o `CLAUDE.md` de mantenedor, mesmo depois de ler um arquivo dentro de `tooling/vibe-coding-toolkit/`.

### Não verificado / pendente

- **Windows:** nada foi testado no Windows (hooks via `cmd.exe`/Git Bash, plugins, caminhos, PowerShell).
- **Context7:** configurado, mas a conexão falhou neste ambiente (`ERR_PROXY_TUNNEL`, política de rede do container).
- **Ponytail:** opção `ledger` não configurada. A recomendação de `ledger=false` está em INSTALLATION §2.
- **Python 3.15.0 final:** lançamento não confirmado daqui (COMPATIBILITY §4).
- **Documentos do manifesto do Toolkit** (`PRODUCT.md`, `README.md`, `docs/{architecture,design,onboarding,quality,setup}.md`): ficam para a Fase 01.

### Não instalado (motivos em INVENTORY §1)

Caveman, RTK, aia-harness, security-guidance, code-review oficial, skill-creator/hookify/feature-dev/code-simplifier, Harness2 CLI, memória Obsidian e skills Next/Vercel/shadcn.

Adiados para a fase em que forem úteis: Graphify, agent-browser ou Chrome DevTools MCP, playwright, pyright-lsp, PostgreSQL skill e differential-review.

## 2026-10-19 — Correções da auditoria pré-commit

- **`.gitignore`:** `data/` virou `/data/`, ancorado na raiz. A regra antiga ignorava qualquer diretório chamado `data` (ex.: `tests/data/`). Foram acrescentados `*.db`, `*.sqlite` e `*.sqlite3`, com os arquivos `-journal`, `-wal` e `-shm`, como defesa extra contra bancos fora de `/data/`. O layout planejado concentra em `/data/` o banco, `documents/`, `backups/` e os arquivos operacionais (logs, exportações). Verificado com `git check-ignore --no-index` em 23 caminhos hipotéticos: 13 ignorados e 10 rastreáveis, como esperado.
- **`CLAUDE.md`:** as regras de permissão passam a ser descritas como controle de risco, com as limitações (correspondência por prefixo; cobertura não comprovada de PowerShell, scripts e processos externos; não testado no Windows). Foi mantida a exigência de autorização explícita para commit, push e PR, e mantidas as proibições de comandos destrutivos e leitura de segredos.
- **Versões dos plugins:** não foram fixadas, porque não há mecanismo oficial que fixe o commit validado sem reinstalar (detalhes em INSTALLATION §7). `.claude/settings.json` ficou inalterado.
