# Como usar o Toolkit nas próximas sessões

O ponto de entrada de toda sessão é o `AGENTS.md`, carregado automaticamente via `CLAUDE.md`. Este documento detalha o que lá aparece resumido.

## 1. Início de sessão

1. Abra o Claude Code na raiz do SalesOS. Os plugins do projeto carregam sozinhos: Superpowers e Ponytail injetam contexto no SessionStart.
2. Confirme o estado antes de pedir trabalho: `git status`, a branch e o último registro em `docs/toolkit/CHANGELOG.md` (e em `docs/phases.md`, quando existir).
3. Retomando trabalho inacabado? Peça ao agente para ler o handoff e **conferir os arquivos e testes reais** antes de continuar.

Prompt de abertura sugerido:

```text
Leia AGENTS.md e docs/toolkit/USAGE.md. Estamos na Fase NN. Antes de alterar arquivos,
apresente o plano com skills escolhidas, critérios de aceite e comandos de verificação.
```

## 2. Ciclo de cada tarefa

| Etapa | O que fazer | Recurso |
|---|---|---|
| Entender | Pedido ambíguo → perguntas, uma por vez, e interpretações lado a lado | `superpowers:brainstorming`; `tooling/vibe-coding-toolkit/docs/prompts/04-brainstorm-to-plan.md` |
| Planejar | Tarefas pequenas, cada uma com uma verificação executável | `superpowers:writing-plans` |
| Implementar | Teste primeiro, depois a menor mudança completa | `superpowers:test-driven-development` + Ponytail `full` |
| Depurar | Reproduzir → causa raiz → teste de regressão | `superpowers:systematic-debugging` |
| Verificar | Rodar a verificação completa e mostrar a saída real | `superpowers:verification-before-completion` |
| Revisar | Diff exato + chamadores e testes afetados; achados com severidade e evidência | `superpowers:requesting-code-review`; prompt 03 para revisões amplas |
| Registrar | Atualizar o documento responsável, decisões (ADR) e limitações | `AGENTS.md`, seção Continuidade |
| Aprovar | Parar e pedir aprovação no fim da fase, ou antes de commit/push | Política do projeto |

## 3. Consultar a documentação do Toolkit

- O índice das ferramentas fica em `tooling/vibe-coding-toolkit/docs/tools/README.md`, e o dos prompts em `tooling/vibe-coding-toolkit/docs/prompts/README.md`.
- Para usar um prompt do Toolkit, peça: *"Leia `tooling/vibe-coding-toolkit/docs/prompts/13-security-review.md` e execute o bloco Prompt sobre o diff atual, adaptado ao SalesOS (Python)."* Use a cópia local, não a URL do `main`, para manter a mesma revisão.
- Sempre filtre pelas adaptações de `docs/toolkit/COMPATIBILITY.md`: exemplos com Next.js, Drizzle ou ESLint não se aplicam.

## 4. Continuidade entre sessões

- Decisões: `docs/decisions/NNNN-titulo.md` (a partir da Fase 01).
- Trabalho inacabado: um handoff curto no plano da fase, usando `tooling/vibe-coding-toolkit/templates/task-handoff.md.template`. Ele registra objetivo, estado verificado, verificações, pendências, bloqueios e a próxima ação.
- Não transforme progresso temporário em memória permanente. Documentos versionados são a fonte de verdade.

## 5. Subagentes sem colisão

- Use `superpowers:dispatching-parallel-agents` ou `subagent-driven-development` só para tarefas independentes.
- Cada subagente recebe a lista de arquivos que pode alterar, sem sobreposição. `pyproject.toml`, `uv.lock`, `migrations/` e operações Git ficam com o coordenador.
- Banco de teste e porta: cada tarefa paralela usa seu próprio SQLite temporário. Se isso não for possível, serialize.
- Revisores só leem. As correções voltam para quem escreveu o código.
- Regras completas: `tooling/vibe-coding-toolkit/docs/tools/02-subagent-orchestration.md` e `templates/rules/parallel-subagent-driven-development.md`.

## 6. Segurança, dependências e qualidade

- **Segurança:** prompt 13 do Toolkit (`docs/prompts/13-security-review.md`) em modo somente leitura. O relatório fica **fora do repositório** (base: `templates/security-review.md.template`). Para um diff, combine com `/security-review`.
- **Dependências (a partir da Fase 01):** toda dependência nova é justificada, tem a licença registrada e passa por auditoria de vulnerabilidades. A ferramenta (ex.: `pip-audit`) será proposta na Fase 01.
- **Qualidade:** a verificação canônica do `AGENTS.md` (Ruff, mypy, pytest), quando existir.
- **Harness:** depois de mudar `AGENTS.md`, plugins ou permissões, rode um caso de `tooling/vibe-coding-toolkit/docs/07-harness-evaluation.md` numa **cópia descartável** da fixture, fora do SalesOS:

  ```bash
  node tooling/vibe-coding-toolkit/scripts/validate-harness.mjs <copia-descartavel>
  ```

  O baseline deve falhar em 2 verificações. Depois da correção feita pelo agente, as 7 devem passar.

## 7. Context7

- Use para APIs de FastAPI, SQLAlchemy, Alembic, Pydantic etc.: resolva a biblioteca e consulte um conceito por vez.
- Nunca envie código do SalesOS, dados de clientes ou segredos: a consulta vai para um serviço externo (Upstash).
- Se o servidor estiver indisponível, use a documentação oficial e registre a limitação.

## 8. Ponytail

- O modo padrão é `full`. Comandos: `/ponytail lite|full|ultra|off`, `/ponytail-review`, `/ponytail-audit`.
- "Menor mudança" nunca remove validação, segurança, acessibilidade nem testes exigidos.

## 9. Comprovar conclusão

Toda entrega lista:

- arquivos alterados;
- comandos executados, com a saída real;
- critérios de aceite atendidos e não atendidos;
- o que não foi verificado e por quê;
- riscos restantes.

Não há conclusão sem evidência.
