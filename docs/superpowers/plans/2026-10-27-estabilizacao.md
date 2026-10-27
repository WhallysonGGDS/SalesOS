# Estabilização pós-Fase 04: plano de implementação

> **Aprovado pelo usuário em 2026-10-27**, com as decisões abaixo. Criado com `superpowers:writing-plans`. Execução nativa (o agente principal implementa), com revisão de segurança independente por etapa de código, mutações e verificação completa antes de cada commit.

**Objetivo:** resolver os defeitos de segurança, integridade e funcionamento conhecidos e preparar a validação no Windows, sem funcionalidades novas do roadmap.

**Diagnóstico de partida (HEAD `b6534a6`, Linux):** `577 passed, 1 skipped`. Reproduzido num banco temporário: `GET /clientes/99999999999999999999`, `/clientes/…/editar` e `/contatos/…/editar` → 500; `GET /tarefas/0` → 422 em JSON. A checagem de estrutura do backup não compara CHECKs, chaves estrangeiras nem colunas dos índices. Só o comando `salesos` (servidor), `restore` e `recover` pegam a trava; `migrations/env.py` não.

## Restrições globais

- Fora do escopo: `pytest-timeout`, atualização do `certifi`, CPF/CNPJ/telefone, Fase 05.
- Nenhuma dependência nova; `pyproject.toml` e `uv.lock` intocados.
- Só dados fictícios e bancos temporários; `data/` nunca é aberto.
- Windows e leitor de tela só são declarados testados com execução real pelo usuário.
- Parar e apresentar alternativas se: E2 exigir arquitetura diferente da aprovada; a normalização dos CHECKs (E3) não for estável; a P1 (E5) exigir mudar a anonimização ou apagar dados.

## Etapas

### E0 — Plano e documentação (estimativa: 0,5 h)
- Este plano; corrigir em `docs/phases.md` o risco B1 da Fase 03 (o procedimento existe, verificado só no Linux).
- Aceite: os documentos distinguem implementado, verificação pendente e bloqueio para dados reais.

### E1 — Ids enormes em clientes e contatos (estimativa: 1 h)
- `IdDep` (`salesos/formularios.py`) nas 14 rotas de `features/clientes/router.py` com `cliente_id`/`contato_id`.
- Teste que percorre toda rota com `{id}` do app (GET e POST) com `0`, `-1`, `2^63` e `99999999999999999999`: nunca 500.
- Aceite: teste passando; mutação que tira o limite detectada.

### E2 — Trava de concorrência (estimativa: 3–4 h)
- Primeiro, levantamento dos testes que compartilham um banco entre clientes HTTP ou processos.
- Proposta aprovada: a trava passa para a inicialização da aplicação (vale para qualquer servidor, inclusive `uvicorn` direto); o comando `salesos` não a pega de novo no mesmo processo; `migrations/env.py` pega a trava do banco-alvo quando ele é um arquivo; `restore --migrar` migra uma cópia com trava própria.
- Testes: `alembic upgrade` recusado com a trava ocupada (banco com o mesmo SHA-256); segundo servidor no mesmo banco recusado; restore com o servidor ativo recusado; CLI e `restore --migrar` normais.
- Aceite: testes passando; ADR 0005 atualizado; item novo na checklist B do Windows.

### E3 — Verificação estrutural dos backups (estimativa: 3–5 h)
- Sondagem: o texto normalizado dos CHECKs é igual num banco criado do zero e num migrado pela cadeia real (desde a `0002`)? Resultado registrado.
- Comparação estruturada de `foreign_key_list` e `index_xinfo`; CHECKs só se a sondagem mostrar estabilidade (senão, parar e propor).
- Testes: backup forjado com chave estrangeira trocada ou índice com outras colunas (e CHECK removido, se aprovado) recusado; backups legítimos de toda revisão aceita pelo `--migrar` continuam aceitos.

### E4 — Fuso horário (P3) (estimativa: 1,5 h)
- Teste que roda só no Windows com o fuso do sistema de Brasília: `intervalo_utc` nos dias de horário de verão de 2018–2019 e o filtro por dia local; pulado com motivo em outro fuso.
- Aceite: lista explícita do que rodou no Linux e do que depende do Windows.

### E5 — P1, política de retenção (estimativa: 0,5–1 h de documentação)
- Direção aprovada: opção A (prazo definido, sem purga automática). Proposta inicial: finalidade "indicadores históricos comerciais e análise operacional interna"; prazo de 12 meses após a anonimização; expurgo manual documentado; backups com política compatível, inclusive cópias anteriores à anonimização.
- Antes de declarar a P1 concluída: apresentar a redação final (oportunidades, tarefas, histórico e backups) e aguardar aprovação. Nenhuma exclusão de dados implementada.

### E6 — F e G (estimativa: 3–5 h)
- F: paginação da linha do tempo do cliente; interações antigas acessíveis, nenhum registro perdido.
- G: páginas HTML para 403, 413 e 422 nas páginas web, sem dados pessoais; `/health` e respostas que não são páginas continuam como estão.

### E7 — Documentação final (estimativa: 1 h)
- ADR 0005, `privacy.md`, checklist B, `quality.md`, `phases.md`, `AGENTS.md`.

### E8 — Validação no Windows (executada pelo usuário, depois de todo o código)
- Checklist B completa, incluindo os itens novos e um leitor de tela real (NVDA ou Narrador).

## Dependências

- E1 é independente.
- E2–E6 vêm antes da E8; o item 17 (`restore --migrar`) só vale depois da E3.
- E5 depende da aprovação da redação final.
