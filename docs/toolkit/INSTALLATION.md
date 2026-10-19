# Instalação e atualização do Toolkit no SalesOS

## 1. O que foi instalado e onde

| Item | Local | Escopo |
|---|---|---|
| Cópia integral do Toolkit (revisão `790a895`) | `tooling/vibe-coding-toolkit/` | Repositório |
| Manifesto de integridade (SHA-256 dos 119 arquivos) | `tooling/vibe-coding-toolkit.sha256` | Repositório |
| Marketplaces `claude-plugins-official` e `ponytail` | `.claude/settings.json` → `extraKnownMarketplaces` | Projeto |
| Plugins `superpowers`, `ponytail`, `context7` | `.claude/settings.json` → `enabledPlugins` | Projeto |
| Regras de permissão e `claudeMdExcludes` | `.claude/settings.json` | Projeto |
| Instruções | `AGENTS.md`, `CLAUDE.md` | Repositório |

Nada foi instalado em escopo global. A configuração de plugins é declarativa: em cada máquina, o Claude Code baixa os plugins para o cache do usuário (`~/.claude/plugins/cache`) quando a pasta é confiada.

**Por que uma cópia sem `.git`:** um repositório Git aninhado (ou submódulo) não seria versionado pelo SalesOS e exigiria passos extras para clonar. A cópia simples, com revisão e hash registrados, permite auditoria (`sha256`) e atualização controlada (§4).

## 2. Primeiro uso no Windows

**Pré-requisitos:**

- Claude Code instalado;
- **Git for Windows**, que fornece o `bash` exigido pelo Claude Code e pelo hook do Superpowers;
- **Node.js** no PATH, exigido pelos hooks da Ponytail.

**Passos:**

1. Atualize a pasta local do SalesOS com o conteúdo deste branch. O commit e o push dependem da sua autorização: ver o relatório da integração.
2. No PowerShell, dentro da pasta: `claude`.
3. Aceite a confiança da pasta e a instalação dos marketplaces e plugins do projeto.
4. Na sessão, execute `/plugin` e confirme os três plugins habilitados.
5. Recomendado: `/plugin configure ponytail@ponytail`, com `ledger` = `false` e `webhookUrl` vazio. Isso evita a gravação de métricas em `%APPDATA%\ponytail`.
6. Faça os testes do §5 que estão marcados como "Windows".

## 3. Verificação rápida (qualquer sistema)

```bash
claude plugin list          # superpowers, ponytail e context7: "enabled", "Scope: project"
claude mcp list             # context7: deve aparecer "Connected"
```

## 4. Atualizar o Toolkit

1. Obtenha a nova revisão numa pasta temporária fora do projeto: `git clone https://github.com/soumatheusgomes/vibe-coding-toolkit.git <temp>`. Registre `git -C <temp> rev-parse HEAD`.
2. Leia o diff entre a revisão registrada e a nova: `git -C <temp> diff 790a895..HEAD --stat`, depois os arquivos relevantes. **Inspecione scripts novos antes de executar qualquer um.**
3. Substitua o conteúdo de `tooling/vibe-coding-toolkit/` pelos arquivos de `git -C <temp> ls-files`, sem `.git`. Faça isso numa mudança própria, para o diff mostrar só o Toolkit.
4. Regenere `tooling/vibe-coding-toolkit.sha256` dentro de `<temp>`: `git ls-files -z | xargs -0 sha256sum > …`.
5. Revise `AGENTS.md` e `docs/toolkit/*` contra as mudanças (templates, prompts e ferramentas novas) e registre tudo em `docs/toolkit/CHANGELOG.md`.
6. Plugins: `claude plugin marketplace update` e `claude plugin update <plugin>`. Antes, leia o changelog do plugin, principalmente os hooks.

## 5. Evidências registradas nesta integração

Ambiente da integração: container Linux na nuvem (Claude Code 2.1.303, Node 22.22.0, Python 3.13.16). **Não foi no Windows.**

| Teste | Comando | Resultado |
|---|---|---|
| Cópia idêntica à origem | `diff -r -q --exclude=.git <clone> tooling/vibe-coding-toolkit` | Sem diferenças |
| Integridade | `sha256sum -c tooling/vibe-coding-toolkit.sha256` (dentro da cópia) | 119 arquivos OK |
| Nenhum arquivo do Toolkit ignorado pelo Git | `git check-ignore -v …` | Só a regra de re-inclusão `!.env.example` aparece; nada ignorado |
| Autotestes do validador de documentos | `node --test scripts/validate-docs.test.mjs` | 9/9 pass |
| Autoteste do avaliador de harness | `node --test scripts/validate-harness.test.mjs` | 2/2 pass |
| Links e âncoras do Toolkit | `node scripts/validate-docs.mjs` | `PASS documentation: 614 local links/anchors…` |
| Plugins habilitados | `claude plugin list` | superpowers 7.0.0, ponytail 5.3.2, context7 (`ea10b213`): enabled, scope project |
| Hook Superpowers | `run-hook.cmd session-start` | JSON com `additionalContext` (skill using-superpowers) |
| Hook Ponytail | `ponytail-activate.js` | `PONYTAIL MODE ACTIVE — level: full` |
| Context7 | `claude mcp list` / `curl` no endpoint | **Falhou neste ambiente:** `ERR_PROXY_TUNNEL` / 403 do proxy de rede. Não validado. |
| Descoberta das instruções numa sessão nova | `claude -p` (ver CHANGELOG) | Ver CHANGELOG |

**Pendentes no Windows:** carregamento dos plugins numa sessão real, hooks via `cmd.exe`/Git Bash, conexão do Context7 com uma consulta real (ex.: "FastAPI form CSRF"), e conferência do hash.

Conferência do hash no PowerShell (sem `sha256sum`):

```powershell
Get-Content tooling\vibe-coding-toolkit.sha256 | ForEach-Object {
  $h, $p = $_ -split '  ', 2
  $f = Join-Path 'tooling\vibe-coding-toolkit' $p
  if ((Get-FileHash -Algorithm SHA256 -LiteralPath $f).Hash.ToLower() -ne $h) { "DIFERENTE: $p" }
}
```

Sem saída = íntegro.

## 6. Finais de linha (Windows)

Com `core.autocrlf=true` (padrão no Git for Windows), os arquivos da cópia ganhariam CRLF no checkout e o hash deixaria de bater. Por isso o `.gitattributes` da raiz marca `tooling/vibe-coding-toolkit/**` e o manifesto `.sha256` como `-text`: o Git não converte os finais de linha desses arquivos. O resto do repositório não é afetado.

## 7. Versões dos plugins: fixação e limitações

Estas são as versões instaladas e validadas neste container, conforme `installed_plugins.json`:

| Plugin | Versão | Commit | Marketplace (commit no momento da instalação) |
|---|---|---|---|
| superpowers | 7.0.0 | `bb92a77741419a4ab5f06e711a283343f1ada0c3` | `claude-plugins-official` @ `ea10b213686c90bb1984b2016937310e05336cf3` |
| ponytail | 5.3.2 | `09c434ab73ca43761c5d8b0c5d341926c2fba710` | `ponytail` @ `09c434ab73ca43761c5d8b0c5d341926c2fba710` |
| context7 | `ea10b213686c` | `ea10b213686c90bb1984b2016937310e05336cf3` | `claude-plugins-official` @ `ea10b213686c…` |

**A versão não foi fixada no `.claude/settings.json`.** O motivo, segundo a documentação oficial (code.claude.com/docs/en/plugins/marketplace-reference, consultada em 2026-10-19):

- Uma fonte de marketplace `github` em `extraKnownMarketplaces` aceita só `repo`, `ref`, `path` e `sparsePaths`, e o `ref` é definido como "branch or tag". Não existe campo `sha` nesse nível.
- `claude-plugins-official` não tem nenhuma tag. Fixar `ref: main` equivale ao comportamento atual.
- A tag `v5.3.2` da Ponytail aponta para `16352ac2…`, que **não** é o commit validado `09c434ab…`. Fixá-la instalaria uma versão não validada.
- O mecanismo oficial que aceita `sha` é a fonte de *plugin* (`github`/`url`/`git-subdir` com `sha`), por exemplo num marketplace declarado nas configurações (`source: "settings"`). Ele muda o identificador dos plugins (`superpowers@<novo-marketplace>`) e exige reinstalar e validar de novo. Fica como proposta para uma etapa autorizada, não aplicada.

**Comportamento resultante numa máquina nova:**

- A primeira instalação pega o estado do marketplace naquele dia, que pode diferir das versões acima.
- Atualização automática: ligada por padrão para `claude-plugins-official` (Superpowers e Context7) e desligada para marketplaces de terceiros (Ponytail).
- Para controlar isso, use `/plugin` → aba **Marketplaces** → **Disable auto-update** em `claude-plugins-official`.
- Depois de instalar, compare `claude plugin list` com a tabela acima. Se a versão for diferente, revise o changelog do plugin, principalmente os hooks, antes de usar.
