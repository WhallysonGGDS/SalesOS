@AGENTS.md

## Específico do Claude Code

- Plugins do projeto, declarados em `.claude/settings.json`: `superpowers`, `ponytail` e `context7`. Ao abrir o projeto pela primeira vez, aceite a confiança da pasta e a instalação dos plugins. As versões não estão fixadas (ver `docs/toolkit/INSTALLATION.md` §7).
- `claudeMdExcludes` impede que o `CLAUDE.md` de mantenedor dentro de `tooling/vibe-coding-toolkit/` seja carregado como instrução do SalesOS.

### Regras de permissão: controle de risco, não garantia

O `.claude/settings.json` declara:

- `ask` para comandos Bash que começam com `git commit` ou `git push`;
- `deny` para comandos Bash que começam com `git reset --hard`, `git clean`, `git push --force` ou `git push -f`;
- `deny` para a ferramenta de leitura de arquivos em `.env`, `.env.local` e `data/**`.

Essas regras reduzem o risco de erro, mas **não são uma barreira completa**:

- Elas comparam o início do comando. Formas equivalentes escritas de outro jeito (por exemplo, com opções globais do Git antes do subcomando) podem não ser interceptadas.
- Elas valem para as ferramentas do Claude Code a que se referem. Não há evidência de que cubram a ferramenta PowerShell no Windows, scripts, processos externos ou leituras feitas por outros comandos.
- O comportamento delas no Windows não foi testado.

Por isso, a obrigação continua sendo a política, independentemente de qualquer bloqueio técnico:

- **Commit, push e PR exigem autorização explícita do usuário, a cada vez.** Nunca contorne uma regra de permissão nem procure outra forma de fazer uma operação que ela restringe.
- Não execute comandos destrutivos (`reset --hard`, `clean`, push forçado, exclusões em massa) sem uma decisão do usuário.
- Não leia nem exiba segredos (`.env*`, exceto `.env.example`) nem dados reais em `data/`, por nenhum meio.
