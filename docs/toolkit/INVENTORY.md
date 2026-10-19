# Inventário do Vibe Coding Toolkit no SalesOS

- **Origem:** https://github.com/soumatheusgomes/vibe-coding-toolkit.git, branch `main`
- **Revisão:** `790a895304e0c08b70a5b215c9d334f1c86b816c` (commit de 2026-10-18T22:42:54-04:00, "feat: default to Harness2-inspired setup workflow")
- **Obtido em:** 2026-10-19T10:31:16Z
- **Licença:** MIT, © 2026 Matheus Gomes (`tooling/vibe-coding-toolkit/LICENSE`)
- **Cópia:** `tooling/vibe-coding-toolkit/`. São 119 arquivos, exatamente os versionados na origem. Integridade em `tooling/vibe-coding-toolkit.sha256`.

**Legenda dos estados:** *instalado* = presente e habilitado; *configurado* = declarado, sem teste funcional completo; *validado* = teste executado com sucesso; *adiado* = pertinente, mas sem necessidade agora; *não aplicável* = incompatível com a stack ou o escopo.

## 1. Componentes externos (plugins, CLIs, MCP)

| Componente | Fonte oficial | Finalidade | Tipo | Dependências | Licença / custo | Escopo | Windows / Claude Code | Python/FastAPI/SQLite | Ação | Evidência | Limitação / motivo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Superpowers 7.0.0 | `obra/superpowers` via marketplace `anthropics/claude-plugins-official` (sha `bb92a777`) | Processo: brainstorming, planos, TDD, depuração, verificação, revisão | Plugin (15 skills + hook SessionStart) | `bash` (no Windows: Git for Windows) | MIT / gratuito | Projeto | Hook `run-hook.cmd` poliglota (cmd → bash). Suportado. | Agnóstico | **Instalado** | `claude plugin list`: enabled, scope project. Hook executado gerou `additionalContext`. | Não testado no Windows. Neste container, sobrepõe a cópia `superpowers@synced` do claude.ai (a do projeto prevalece). |
| Ponytail 5.3.2 | `DietrichGebert/ponytail` (sha `09c434ab`) | Menor mudança completa (YAGNI) | Plugin (6 skills, comandos, hooks) | Node.js no PATH | MIT / gratuito. O webhook opcional fica vazio. | Projeto (opções em nível de usuário) | Hooks via `node -e`, que tratam `\`. Suportado. | Agnóstico | **Instalado** | Plugin enabled. Hook de ativação imprimiu `PONYTAIL MODE ACTIVE — level: full`. | Opção `ledger` (padrão ligada) grava CSV em `%APPDATA%`/`~/.config/ponytail`. Recomendação: `ledger=false` (ver USAGE). Não testado no Windows. |
| Context7 | `upstash/context7` via `claude-plugins-official/external_plugins/context7` | Documentação atual de bibliotecas | Plugin (MCP HTTP remoto) | Rede | Cliente MIT. Backend hospedado com plano gratuito anônimo e limite de taxa; API key gratuita opcional. | Projeto | Sem Node; suportado | FastAPI, SQLAlchemy etc. indexados | **Configurado** | Plugin enabled. | **Não validado:** `claude mcp list` → `ERR_PROXY_TUNNEL`; a rede deste container bloqueia `mcp.context7.com`. Validar no Windows. As consultas saem para a Upstash: nunca enviar segredos nem código privado. |
| Caveman 4.0.1 | `JuliusBrussee/caveman` (sha `bad48a0e`) | Respostas comprimidas | Plugin (hooks em toda sessão e subagente) | Node, `sed`, shell POSIX | Apache-2.0 + MIT | — | Hooks dependem de `sed` | Agnóstico | **Não instalado** | — | Comprime toda a prosa, o que contraria os relatórios detalhados em PT-BR exigidos pelo projeto. |
| RTK | `rtk-ai/rtk` | Reduzir a saída de comandos | CLI binário + hook global | `winget`/binário | Apache-2.0 / gratuito | Usuário (global) | Tem instalação nativa para Windows (`winget install rtk-ai.rtk`) | Agnóstico | **Não instalado** | — | Exige instalação global e `rtk init --global`, que altera a configuração global do Claude. O ganho é marginal num projeto pequeno. Reavaliar se a saída de testes ficar volumosa. |
| Graphify | `Graphify-Labs/graphify` (PyPI `graphifyy`) | Grafo do código | CLI Python + skill | Python, `uv tool` | Apache-2.0 | Usuário | Suporta Windows | Compatível | **Adiado** | — | Repositório ainda sem código. Reavaliar depois da Fase 02. A `.graphifyignore` precisa excluir `data/`, `.env`, `.venv/` e `tooling/`. |
| agent-browser | `vercel-labs/agent-browser` | Automação de navegador | CLI npm | Node | Apache-2.0 | Usuário | — | Útil para a UI Jinja2 | **Adiado** | — | Ainda não existe interface. Decidir na primeira fase com tela; alternativa: plugin `playwright`. |
| Chrome DevTools MCP | `ChromeDevTools/chrome-devtools-mcp` | Console, rede, desempenho | MCP | Node, Chrome | Apache-2.0 | Projeto | — | Útil para a UI | **Adiado** | — | Mesmo motivo do agent-browser. Instalar só um dos dois. |
| aia-harness | `leandrosilvaferreira/claude-plugins-registry` (sha `e891972d`) | Gera uma harness completa (hooks, agentes, regras, worktrees, CLAUDE.md por domínio) | Plugin gerador | — | — | Projeto | — | — | **Não instalado** | — | Duplicaria e conflitaria com a harness do Toolkit, que proíbe exigir worktrees e hooks de Git por padrão. |
| security-guidance 2.0.14 | `claude-plugins-official/plugins/security-guidance` | Alertas de segurança em edições e revisão por LLM em commit/push | Plugin (hooks) | `bash`, Python | Gratuito, mas cada revisão consome cota | Projeto | Depende de `bash` | Compatível | **Não instalado** | — | O SessionStart instala um SDK automaticamente (`ensure_agent_sdk.py`) e dispara revisões assíncronas. São efeitos automáticos não autorizados. Reavaliar na Fase 07. |
| code-review (oficial) | `claude-plugins-official/plugins/code-review` | Revisão de PR por múltiplos agentes | Plugin | `gh` | Gratuito | — | — | — | **Não instalado** | — | Redundante com `superpowers:requesting-code-review` e o `/code-review` embutido; é voltado para PRs. |
| pyright-lsp | `claude-plugins-official/plugins/pyright-lsp` | Inteligência de código Python | Plugin LSP | `pyright-langserver` | Gratuito | Projeto | — | Compatível | **Adiado (Fase 01)** | — | Depende de o projeto Python existir. Sobrepõe-se em parte ao mypy. |
| playwright (MCP) | `claude-plugins-official/external_plugins/playwright` | Testes de navegador | Plugin MCP | Node (npx) | Apache-2.0 | Projeto | — | Útil para a UI | **Adiado** | — | Sem UI ainda. |
| skill-creator, hookify, feature-dev, code-simplifier | `claude-plugins-official` | Criar skills/hooks, fluxo de feature, simplificação | Plugins | — | Gratuito | — | — | — | **Não instalado** | — | Sem necessidade concreta. Sobreposição com Superpowers e Ponytail. |
| Anthropic skills | `anthropics/skills` | Artefatos (docx, pdf…) e criação de skills | Skills | — | Por skill. `docx/pdf/pptx/xlsx` têm licença restritiva. | — | — | — | **Não incorporado** | — | As licenças proíbem vendorizar. Usar só as skills disponíveis no cliente, se necessário (PDF na Fase 05). |
| Vercel skills, next-dev-loop, next-bundle-optimizer, shadcn | `vercel-labs/agent-skills`, `vercel/next.js` | Ecossistema Next/React | Skills | Next.js | — | — | — | Incompatível | **Não aplicável** | — | A stack é Python + Jinja2. |
| supabase-postgres-best-practices | `supabase/agent-skills` | SQL e migrações PostgreSQL | Skill | PostgreSQL | — | — | — | Futuro | **Adiado** | — | Usar na migração SQLite → PostgreSQL. |
| gh-fix-ci | `openai/skills` | Corrigir CI do GitHub Actions | Skill (Codex) | `gh`, Codex | — | — | Fluxo Codex | — | **Não aplicável** | — | Sem CI e sem Codex. |
| differential-review | `trailofbits/skills` | Revisão de segurança de diff | Skill | Git | CC BY-SA 4.0 | Projeto | — | Compatível | **Adiado (Fase 07)** | — | Alternativa já disponível: prompt 13 do Toolkit + `/security-review`. A licença ShareAlike exige atenção se vendorizar. |
| Sentry MCP | `getsentry` | Observabilidade externa | MCP OAuth | Conta Sentry | Serviço externo | — | — | — | **Não aplicável** | — | App local, sem serviços externos. |
| Harness2 (laboratório CLI) | `google-research/harness2` | Benchmarks de harness | CLI Python | Python 3.12–3.13, Node 20+, Docker em alguns benchmarks | Apache-2.0; os benchmarks geram **custo de API** | — | — | — | **Não instalado** | — | Custo e Docker vetados. O método nativo (prompt 15) é adotado como procedimento documental. |
| Codex workflow (tools/15) | Toolkit | Configuração do cliente Codex | Documentação | Codex | — | — | — | — | **Não aplicável** | — | O cliente usado é o Claude Code. |
| Memória Obsidian / sistema de memória Claude (tools/08, 09; prompt 06) | Toolkit | Memória persistente | Documentação / MCP | — | — | — | — | — | **Não adotado** | — | Os documentos versionados são a memória do projeto. O Toolkit desaconselha memória completa em projeto vazio. |
| ESLint/Biome quality gates (tools/06; prompts 02, 07, 08) | Toolkit | Lint JS/TS e limites | Template + regras | Node, ESLint | — | — | — | Incompatível | **Substituído** | — | O equivalente nativo é Ruff + mypy + limite de 350 linhas (ver COMPATIBILITY). |

## 2. Componentes internos do Toolkit (documentos, prompts, templates)

| Recurso | Tipo | Ação | Onde é usado |
|---|---|---|---|
| `templates/AGENTS.md.template` | Template | **Adaptado** | `/AGENTS.md` |
| `templates/CLAUDE.md.template` | Template | **Adaptado** | `/CLAUDE.md` (import + regras específicas do Claude) |
| `templates/project-docs/*` + `manifest.json` | Templates | **Adiado (Fase 01)** | `README.md`, `PRODUCT.md`, `docs/{architecture,design,onboarding,quality,setup}.md` |
| `templates/product.md.template` | Template | **Adiado (Fase 01)** | `PRODUCT.md` |
| `templates/task-handoff.md.template` | Template | **Sob demanda** | Trabalho entre sessões (USAGE §4) |
| `templates/security-review.md.template` | Template | **Sob demanda (Fase 07)** | Relatório privado, fora do repositório |
| `templates/rules/parallel-subagent-driven-development.md` | Regra | **Incorporado (resumo)** | `AGENTS.md`, seção Subagentes |
| `templates/harness-evaluation/` | Fixture | **Validado (autoteste)** | Avaliação da harness (USAGE §6) |
| `templates/settings.json.example`, `templates/hooks/` | Exemplos de hook | **Não adotado** | Nenhum hook personalizado é necessário |
| `templates/project/mcp.json.example` | Config Context7 | **Substituído** pelo plugin oficial | — |
| `templates/project/.graphifyignore.example` | Config | **Adiado** | Junto com o Graphify |
| `templates/project/codex*.toml.example`, `sentry.*` | Config | **Não aplicável** | — |
| `templates/next/`, `templates/eslint/` | Templates | **Não aplicável** | — |
| `templates/environment-manifest.json.example` | Inventário da máquina | **Não adotado** | A preparação de máquina fica fora do escopo |
| Prompt 01 (sanitização), 09 (arquivos grandes) | Prompt | **Sob demanda** | Refatorações futuras |
| Prompt 02, 07, 08 (ESLint) | Prompt | **Não aplicável** | — |
| Prompt 03 (revisão multiagente), 05 (ondas paralelas) | Prompt | **Sob demanda** | Revisões não triviais e tarefas independentes |
| Prompt 04 (brainstorm → plano) | Prompt | **Adotado** | Início de cada fase, junto com `superpowers:brainstorming` |
| Prompt 06 (memória) | Prompt | **Não adotado** | — |
| Prompt 10 (máquina), 11 (Next.js bootstrap) | Prompt | **Não aplicável** | Alteração global / stack Next |
| Prompt 12 (projeto existente) | Prompt | **Adaptado** | Roteiro desta integração e de reaplicações |
| Prompt 13 (segurança) | Prompt | **Adotado (sob demanda)** | Diffs sensíveis e Fase 07 |
| Prompt 14 (avaliação da harness), 15 (melhoria da harness) | Prompt | **Adotado (método nativo)** | Depois de mudar instruções ou plugins |
| `docs/00`–`07`, `docs/tools/*` | Documentação | **Referência** | Consultar pelo caminho em `tooling/` |
| `scripts/validate-docs*.mjs`, `scripts/validate-harness*.mjs` | Scripts de verificação | **Validados** | INSTALLATION §5 |
| `scripts/validate-next.mjs`, `scripts/check-eslint.mjs` | Scripts | **Não executados** | Instalam pacotes npm e criam um projeto Next.js temporário |
| `.github/workflows/validate.yml` | CI do Toolkit | **Inerte** | O GitHub só executa workflows na raiz do repositório |

## 3. Lista completa dos arquivos (comparada à origem)

A lista abaixo saiu de `git ls-files` na revisão `790a895`. `diff -r` entre o clone e a cópia não acusou diferenças, e `sha256sum -c tooling/vibe-coding-toolkit.sha256` passou para os 119 arquivos.

| Arquivo (relativo a `tooling/vibe-coding-toolkit/`) | Tipo | Situação |
|---|---|---|
| `.github/workflows/validate.yml` | Configuração (CI do Toolkit) | Preservado; inerte no SalesOS (o GitHub só executa workflows na raiz) |
| `.gitignore` | Raiz | Preservado |
| `AGENTS.md` | Instrução do mantenedor | Preservado; excluído do carregamento via claudeMdExcludes |
| `CLAUDE.md` | Instrução do mantenedor | Preservado; excluído do carregamento via claudeMdExcludes |
| `LICENSE` | Licença (MIT) | Preservado |
| `README.es.md` | Raiz | Preservado |
| `README.md` | Raiz | Preservado |
| `README.pt-BR.md` | Raiz | Preservado |
| `docs/00-overview.md` | Documentação | Preservado |
| `docs/01-installation.md` | Documentação | Preservado |
| `docs/02-playbook-onboarding.md` | Documentação | Preservado |
| `docs/03-environment-setup.md` | Documentação | Preservado |
| `docs/04-project-bootstrap.md` | Documentação | Preservado |
| `docs/05-toolkit-validation.md` | Documentação | Preservado |
| `docs/06-project-defaults.md` | Documentação | Preservado |
| `docs/07-harness-evaluation.md` | Documentação | Preservado |
| `docs/assets/readme/context-still.svg` | Imagem (README) | Preservado |
| `docs/assets/readme/context.svg` | Imagem (README) | Preservado |
| `docs/assets/readme/foundation-still.svg` | Imagem (README) | Preservado |
| `docs/assets/readme/foundation.svg` | Imagem (README) | Preservado |
| `docs/assets/readme/hero-still.svg` | Imagem (README) | Preservado |
| `docs/assets/readme/hero.svg` | Imagem (README) | Preservado |
| `docs/assets/readme/orchestration-still.svg` | Imagem (README) | Preservado |
| `docs/assets/readme/orchestration.svg` | Imagem (README) | Preservado |
| `docs/assets/readme/quality-still.svg` | Imagem (README) | Preservado |
| `docs/assets/readme/quality.svg` | Imagem (README) | Preservado |
| `docs/prompts/01-project-sanitation.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/prompts/02-eslint-warning-burndown.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/prompts/03-multi-agent-code-review.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/prompts/04-brainstorm-to-plan.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/prompts/05-parallel-wave-dispatch.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/prompts/06-memory-bootstrap.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/prompts/07-eslint-complete-setup.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/prompts/08-eslint-quality-gates-install.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/prompts/09-file-size-refactor.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/prompts/10-development-environment-setup.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/prompts/11-next-project-bootstrap.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/prompts/12-existing-project-setup.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/prompts/13-security-review.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/prompts/14-harness-evaluation.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/prompts/15-harness-improvement.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/prompts/README.md` | Prompt | Preservado; uso conforme INVENTORY §2 |
| `docs/tools/01-superpowers.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/02-subagent-orchestration.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/03-rtk-token-proxy.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/04-ponytail.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/05-caveman.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/06-eslint-biome-quality-gates.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/07-graphify.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/08-obsidian-memory.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/09-claude-memory-system.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/10-hooks-best-practices.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/11-agent-browser.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/12-context7.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/13-anthropics-skills.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/14-chrome-devtools-mcp.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/15-codex-workflow.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/16-vercel-skills.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/17-nextjs-runtime-and-performance.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/18-postgresql-skills.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/19-github-ci-repair.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/20-security-review.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/21-shadcn-ui.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/22-sentry-mcp.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/23-harness2.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `docs/tools/README.md` | Documentação de ferramenta | Preservado; decisão por ferramenta em INVENTORY §2 |
| `scripts/check-eslint.mjs` | Script (Node) | Preservado; NÃO executado (instala npm/Next.js, fora do escopo) |
| `scripts/validate-docs.mjs` | Script (Node) | Preservado; executado com sucesso (ver INSTALLATION §5) |
| `scripts/validate-docs.test.mjs` | Script (Node) | Preservado; executado com sucesso (ver INSTALLATION §5) |
| `scripts/validate-harness.mjs` | Script (Node) | Preservado; só os testes seguros foram executados |
| `scripts/validate-harness.test.mjs` | Script (Node) | Preservado; executado com sucesso (ver INSTALLATION §5) |
| `scripts/validate-next.mjs` | Script (Node) | Preservado; NÃO executado (instala npm/Next.js, fora do escopo) |
| `templates/AGENTS.md.template` | Template | Adaptado → /AGENTS.md |
| `templates/CLAUDE.md.template` | Template | Adaptado → /CLAUDE.md |
| `templates/README.md` | Template | Preservado |
| `templates/environment-manifest.json.example` | Template | Preservado |
| `templates/eslint/eslint-rules/core-rules.cjs` | Template (ESLint) | Preservado; não aplicável (Python) |
| `templates/eslint/eslint-rules/index.cjs` | Template (ESLint) | Preservado; não aplicável (Python) |
| `templates/eslint/eslint-rules/next-base.mjs` | Template (ESLint) | Preservado; não aplicável (Python) |
| `templates/eslint/eslint-rules/utils.cjs` | Template (ESLint) | Preservado; não aplicável (Python) |
| `templates/eslint/eslint.config.mjs.example` | Template (ESLint) | Preservado; não aplicável (Python) |
| `templates/eslint/eslint.typed.config.mjs.example` | Template (ESLint) | Preservado; não aplicável (Python) |
| `templates/eslint/next-app.config.mjs.example` | Template (ESLint) | Preservado; não aplicável (Python) |
| `templates/eslint/next.config.mjs.example` | Template (ESLint) | Preservado; não aplicável (Python) |
| `templates/eslint/next.typed.config.mjs.example` | Template (ESLint) | Preservado; não aplicável (Python) |
| `templates/eslint/verify.mjs` | Template (ESLint) | Preservado; não aplicável (Python) |
| `templates/harness-evaluation/AGENTS.md` | Fixture de avaliação | Preservado; usar apenas em cópia descartável |
| `templates/harness-evaluation/access.mjs` | Fixture de avaliação | Preservado; usar apenas em cópia descartável |
| `templates/harness-evaluation/local-notes.txt` | Fixture de avaliação | Preservado; usar apenas em cópia descartável |
| `templates/hooks/hook-io.mjs.example` | Exemplo de hook | Preservado; não adotado |
| `templates/next/.env.example` | Template (Next.js) | Preservado; não aplicável (Python) |
| `templates/next/drizzle.config.ts.example` | Template (Next.js) | Preservado; não aplicável (Python) |
| `templates/next/src/db/index.test.ts.example` | Template (Next.js) | Preservado; não aplicável (Python) |
| `templates/next/src/db/index.ts.example` | Template (Next.js) | Preservado; não aplicável (Python) |
| `templates/next/src/db/schema/index.ts.example` | Template (Next.js) | Preservado; não aplicável (Python) |
| `templates/next/src/lib/env-schema.ts.example` | Template (Next.js) | Preservado; não aplicável (Python) |
| `templates/next/src/lib/env.test.ts.example` | Template (Next.js) | Preservado; não aplicável (Python) |
| `templates/next/src/lib/env.ts.example` | Template (Next.js) | Preservado; não aplicável (Python) |
| `templates/next/src/lib/logger.test.ts.example` | Template (Next.js) | Preservado; não aplicável (Python) |
| `templates/next/src/lib/logger.ts.example` | Template (Next.js) | Preservado; não aplicável (Python) |
| `templates/next/src/lib/utils.ts.example` | Template (Next.js) | Preservado; não aplicável (Python) |
| `templates/next/vitest.config.mts.example` | Template (Next.js) | Preservado; não aplicável (Python) |
| `templates/product.md.template` | Template | Preservado |
| `templates/project-docs/README.md.template` | Template de documento | Preservado; a adaptação vem na Fase 01 |
| `templates/project-docs/architecture.md.template` | Template de documento | Preservado; a adaptação vem na Fase 01 |
| `templates/project-docs/design.md.template` | Template de documento | Preservado; a adaptação vem na Fase 01 |
| `templates/project-docs/manifest.json` | Template de documento | Preservado; a adaptação vem na Fase 01 |
| `templates/project-docs/onboarding.md.template` | Template de documento | Preservado; a adaptação vem na Fase 01 |
| `templates/project-docs/quality.md.template` | Template de documento | Preservado; a adaptação vem na Fase 01 |
| `templates/project-docs/setup.md.template` | Template de documento | Preservado; a adaptação vem na Fase 01 |
| `templates/project/.graphifyignore.example` | Template de configuração | Preservado; Context7 via plugin, Graphify adiado |
| `templates/project/codex.config.toml.example` | Template de configuração | Preservado; Context7 via plugin, Graphify adiado |
| `templates/project/mcp.json.example` | Template de configuração | Preservado; Context7 via plugin, Graphify adiado |
| `templates/project/sentry.codex.config.toml.example` | Template de configuração | Preservado; Context7 via plugin, Graphify adiado |
| `templates/project/sentry.mcp.json.example` | Template de configuração | Preservado; Context7 via plugin, Graphify adiado |
| `templates/rules/parallel-subagent-driven-development.md` | Regra de delegação | Preservado; incorporado de forma resumida no AGENTS.md |
| `templates/security-review.md.template` | Template | Preservado |
| `templates/settings.json.example` | Template | Preservado |
| `templates/task-handoff.md.template` | Template | Preservado |
