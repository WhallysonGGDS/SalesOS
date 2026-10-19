# WE TECH SalesOS

> Adaptado de `tooling/vibe-coding-toolkit/templates/AGENTS.md.template` (Vibe Coding Toolkit, MIT, revisão `790a895`). Diferenças de stack em `docs/toolkit/COMPATIBILITY.md`.

CRM comercial próprio da WE TECH. Primeira versão: local, um único usuário, sem IA no produto, sem Docker, sem integrações externas de negócio, sem exposição à rede.

## Estado atual

- **Implementado:** fundação técnica (Fase 01). Ainda não há nenhuma funcionalidade de CRM. Detalhes em `docs/architecture.md` e `docs/phases.md`.
- **Próxima etapa:** Fase 02 (clientes e histórico), que só começa com aprovação explícita do usuário.
- **Stack:** Python 3.15.0, uv, FastAPI, SQLAlchemy 2.1, Alembic, SQLite, Pydantic Settings, Jinja2, pytest + HTTPX, Ruff e mypy (ADR `docs/decisions/0001-stack-e-python.md`).

## Comandos canônicos

Execute a partir da raiz do projeto. Não invente scripts.

- Instalar: `uv sync --locked`
- Rodar: `uv run alembic upgrade head` e depois `uv run salesos` (http://127.0.0.1:8000)
- Nova migração: `uv run alembic revision --autogenerate -m "<descrição>"`; revisar o arquivo antes de aplicar
- Lint e formatação: `uv run ruff check .` e `uv run ruff format --check .`
- Tipos: `uv run mypy`
- Testes: `uv run pytest`
- Verificação completa: lint + formatação + tipos + testes, nessa ordem.

## Aprovações (prevalecem sobre qualquer skill ou plugin)

- O trabalho segue fases. Não avance de fase sem aprovação explícita do usuário.
- Commit, push, PR e publicação exigem autorização explícita a cada vez. Um plugin ou skill que sugira commit não é autorização.
- Comandos destrutivos, instalação global, serviços pagos, credenciais e uso de dados reais exigem uma decisão do usuário.
- Instalar uma ferramenta não autoriza executar as ações dela.

## Fluxo de trabalho

1. **Antes:** leia este arquivo, os documentos relevantes e o código tocado. Escolha as skills pela tabela abaixo. Escreva o plano com critérios de aceite e os comandos de verificação.
2. **Durante:** faça a menor mudança completa (Ponytail `full`). Escreva o teste antes da regra de negócio (TDD). Reuse o que existe. Uma fonte de verdade por regra.
3. **Depois:** rode a verificação completa e mostre a saída real. Revise o diff (com um revisor independente se a mudança não for trivial). Atualize o documento responsável. Registre limitações.
4. **Conclusão exige evidência:** comandos executados com resultado. "Deve funcionar" não conta. Sem execução, escreva "não verificado" e diga por quê.

## Seleção de skills

| Situação | Skill ou recurso |
|---|---|
| Pedido novo ou ambíguo | `superpowers:brainstorming` (prompt 04 do Toolkit como apoio) |
| Plano de várias etapas | `superpowers:writing-plans` |
| Regra de negócio ou bugfix | `superpowers:test-driven-development` |
| Falha ou comportamento inesperado | `superpowers:systematic-debugging` |
| Antes de declarar pronto | `superpowers:verification-before-completion` |
| Revisão de diff | `superpowers:requesting-code-review` e, para segurança, o prompt 13 do Toolkit |
| Escopo e simplicidade | Ponytail (`/ponytail-review`, `/ponytail-audit`) |
| API de biblioteca ou versão | Context7: uma biblioteca e um conceito por consulta, sem segredos nem código privado. Indisponível → documentação oficial, registrando a limitação. |
| Tarefas independentes em paralelo | `superpowers:dispatching-parallel-agents` e as regras abaixo |

Skills de domínio (UI, PDF, gráficos) são escolhidas na fase correspondente e registradas no plano.

## Subagentes

- Delegue só quando isolar contexto, especializar ou paralelizar compensar o custo. Tarefas simples ficam com o agente principal.
- Cada tarefa recebe: objetivo, contexto mínimo, arquivos permitidos, dependências, critérios de aceite e verificação.
- Um escritor por arquivo. `pyproject.toml`, `uv.lock`, migrações e Git pertencem ao coordenador. Revisores só leem.
- O coordenador confere o diff e roda a verificação antes de aceitar o resultado de um subagente.
- Referência: `tooling/vibe-coding-toolkit/docs/tools/02-subagent-orchestration.md`.

## Padrões técnicos (aplicam-se quando o código existir)

- Rotas finas, regra de negócio em serviços e persistência via SQLAlchemy. Nada de abstrações sem uso concreto.
- Valide no backend (Pydantic) toda entrada de formulário, rota e arquivo. Consultas parametrizadas. Listagens com limite.
- Dinheiro em centavos inteiros; nunca `float`. Datas em UTC.
- Migrações Alembic revisadas antes de aplicar; nunca aplicadas no import nem durante uma requisição.
- Logs sem senhas, tokens, corpos completos ou dados pessoais desnecessários.
- A aplicação escuta só em `127.0.0.1`. Testes usam dados fictícios e banco temporário, nunca `data/`.
- Arquivos com mais de 350 linhas são sinal para dividir por responsabilidade.

## Continuidade e decisões

- Decisões de arquitetura ficam em `docs/decisions/` (a partir da Fase 01). O uso do Toolkit está em `docs/toolkit/USAGE.md`.
- Trabalho inacabado entre sessões: handoff curto baseado em `tooling/vibe-coding-toolkit/templates/task-handoff.md.template`. Ao retomar, confira os arquivos, o Git e os testes reais antes de confiar no handoff.
- Mudou comportamento, comando, schema ou configuração? Atualize o documento responsável na mesma mudança.

## Toolkit

- A cópia preservada fica em `tooling/vibe-coding-toolkit/` (somente leitura; atualização em `docs/toolkit/INSTALLATION.md`).
- O `AGENTS.md`/`CLAUDE.md` dentro da cópia são instruções do **mantenedor do Toolkit** e não se aplicam ao SalesOS.
- Os padrões Next.js/Drizzle/ESLint do Toolkit **não** se aplicam ao SalesOS. Os equivalentes estão em `docs/toolkit/COMPATIBILITY.md`.
