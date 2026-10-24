# Registro das fases

## Fase 00 — Descoberta e planejamento (concluída)
Relatório entregue na conversa de 2026-10-19; Toolkit integrado no commit `6e1c9a7`.

## Fase 01 — Fundação técnica (concluída em 2026-10-19)
Plano: `docs/superpowers/plans/2026-10-19-fase-01-fundacao.md`.

| Critério de aceite | Resultado |
|---|---|
| Instalação reproduzível (`uv sync --locked`) | Passou |
| Ruff lint e formatação | Passou |
| mypy strict | Passou |
| pytest | 46 testes passaram |
| Aplicação inicia e `/health` responde 200 | Passou (servidor real + curl) |
| Host inválido recusado | Passou (teste e curl: 400) |
| POST sem token CSRF válido recusado | Passou (testes; não há rota POST de produção ainda) |
| Cabeçalhos de segurança | Passou (teste e curl) |
| SQLite com FK e WAL | Passou (teste e banco real) |
| Migração aplica e reverte em banco temporário | Passou |
| `alembic check` sem diferenças | Passou |
| Sem segredos ou dados operacionais rastreados | Passou |
| Documentação consistente | Revisada |

Pendências no Windows: `docs/setup.md`.

## Fase 02 — Clientes e histórico (implementada e verificada no Linux; Windows pendente)

Etapas aprovadas uma a uma, com paradas para revisão (P1 após o esquema, P2 após backup e restauração, P3 no fim).

| Etapa | Conteúdo | Commit |
|---|---|---|
| E0 | Aviso `httpx`/Starlette documentado (D13) | `badd0c6` |
| E1 | Normalização de e-mail, chave de busca, escape de `LIKE` | `2864b33` |
| E2–E6 | Esquema `0002`, serviços e anonimização, backup/restauração/trava, rotas e telas, interface e acessibilidade (um commit: as etapas compartilham arquivos e os estados intermediários não foram guardados) | `245e36a` |
| E7 | Correções das revisões (cache, log de acesso, parâmetros em erros, CLI, ordenação, origem obrigatória) | `55e56c8` |
| A | Restore sem falso alerta de reintrodução | `2fad52d` |
| B | Restore recusa estrutura inesperada (tabelas, colunas, índices, views, triggers) | `c9c1dfa` |
| C | Permissões restritivas (POSIX) para banco, backups e cópias | `be75b1a` |
| E8 | Documentação | commit da E8 |

| Critério de aceite | Resultado (Linux) |
|---|---|
| Ruff, formatação e mypy strict | Passou |
| pytest | 230 passed, 1 skipped (teste só do Windows), 1 aviso conhecido |
| Migração `0002`: `upgrade`, `downgrade` e `alembic check` | Passou |
| CSRF em todas as rotas POST; GET sem efeito colateral | Passou (testes percorrem todas as rotas) |
| XSS escapado em campos e na linha do tempo | Passou |
| Eventos sem valores pessoais; interações só de acréscimo | Passou |
| Anonimização: dados fora da busca, dos eventos, dos logs e dos bytes do `.db`/`-wal` | Passou (dados fictícios) |
| Backup consistente com escritor ativo; integridade, SHA-256, revisão, estrutura | Passou |
| Restauração: recusa com qualquer conexão aberta; falha e queda em cada estado recuperadas; `recover` idempotente e sem apagar | Passou |
| Interface: contraste, foco, teclado, 320–1440 px, sem erros de CSP | Passou no Chromium (auditoria por script) |
| CPF, CNPJ e telefone | **Pendentes** (D6, D11, D12): sem fonte oficial acessível |
| Windows | **Pendente**: checklist em `docs/setup.md` |

**Mutações** (o código foi alterado de propósito, numa cópia, para confirmar que algum teste falha): sem `secure_delete`; sem checkpoint do WAL; evento com valor pessoal; resumo não apagado; `LIKE` sem escape; log com o nome; cliente anonimizado editável; restore sem trava; sem `integrity_check`; sem SHA-256; sem desfazer automático; recover sobrescrevendo o banco novo; `verified` sem preservar o restaurado; nome sem escape na lista e na linha do tempo; arquivar aceitando GET; CSRF desligado em uma rota; confirmação da anonimização ignorada; formulário aceitando campos extras; 302 no lugar de 303; checagem de reintrodução desligada; checagem de estrutura desligada; `chmod` desligado. Todas foram detectadas. Outras quatro mutações da restauração sobreviveram por haver uma segunda proteção cobrindo o mesmo caso (saída do WAL e checkpoint se cobrem; a recuperação olha os arquivos reais, então a ordem entre gravar o estado e mover é indiferente; a publicação sem sobrescrever só protege contra uma corrida não reproduzível em teste).

**Revisões:** revisor geral e revisor de segurança independentes (só leitura) e `ponytail-review`: nenhum achado crítico ou alto. Propostas D a G (mensagens de erro do restore, validação dos caminhos do diário, paginação da linha do tempo, páginas HTML para erros 422/403) aguardam decisão.

## Próximas
Fase 03 — Oportunidades e funil: só começa com aprovação explícita. Antes de dados reais, a checklist do Windows (`docs/setup.md`).
