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

**Revisões:** revisor geral e revisor de segurança independentes (só leitura) e `ponytail-review`: nenhum achado crítico ou alto. Propostas D a G (mensagens de erro do restore, validação dos caminhos do diário, paginação da linha do tempo, páginas HTML para erros 422/403) aguardavam decisão; D e E foram feitas na Fase 02.1.

## Fase 02.1 — Hardening (implementada e verificada no Linux)

Escopo autorizado: E, D, S2 e divisão de `tests/backup/test_restore.py`. Fora do escopo: F, G, `certifi` e funcionalidades novas.

| Etapa | Entrega | Commit |
|---|---|---|
| Testes | `test_restore.py` (492 linhas) dividido em troca/validação, concorrência, anonimização e recuperação; mesmos 35 IDs antes e depois | `4ab6dfe` |
| E | `recover` confere o diário (carimbo, estado, banco, caminhos) e usa só caminhos derivados; diário adulterado é recusado sem mover nada | `77a91ef` |
| D | `backup.bloqueado()` separa bloqueio de outros erros do SQLite; backup não fica mais em laço infinito com bloqueio exclusivo | `d046690` |
| S2 | Corpo das requisições limitado a 256 KiB (413), fora do `BaseHTTPMiddleware` | `8b4e790` |

| Critério de aceite | Resultado (Linux) |
|---|---|
| Ruff, formatação e mypy strict | Passou |
| pytest | 270 passed, 1 skipped (teste só do Windows), 1 aviso conhecido |
| Fluxo legítimo pelo CLI real (banco fictício): migrar, backup, restore, recover | Passou |
| Windows | **Pendente**: checklist em `docs/setup.md` |

**Mutações detectadas:** checagem do carimbo; checagem do banco; `RecursionError` fora do `except`; prazo do backup removido (a suíte trava, sem `pytest-timeout`); máscara dos códigos estendidos; mensagem de bloqueio para todo erro; middleware do limite removido; contagem dos bytes removida. A checagem antecipada do `Content-Length` sobreviveu por ser redundante e foi removida.

**Revisões:** revisor de segurança independente (só leitura) em cada etapa (E, D e S2): nenhum achado crítico, alto ou médio. Os ajustes apontados foram aplicados: dígitos só ASCII no carimbo, `RecursionError`, nome do diário arquivado e o limite do corpo fora do `BaseHTTPMiddleware`.

**Riscos residuais:**
- Sem `pytest-timeout`, uma regressão no prazo do backup trava a suíte em vez de falhar.
- No backup, a espera real com bloqueio exclusivo chega a cerca de 15 s (10 s do prazo mais os 5 s de espera da conexão).
- O limite do corpo não impede conexões lentas (slowloris) nem muitas conexões simultâneas; o risco é aceitável num app que só escuta em 127.0.0.1.
- Um diário bem formado, mas trocado por outro de uma restauração antiga, ainda desfaz aquela restauração (sem apagar nada). Isso exige escrever em `data/`, o que já está fora do modelo de ameaça.

## Fase 03 — Oportunidades e funil (implementada e verificada no Linux)

Plano: `docs/superpowers/plans/2026-10-25-fase-03-funil.md`. Decisões: ADR `0006-funil.md` (R1–R10, P1–P3).

| Etapa | Entrega | Commit |
|---|---|---|
| 0 | ADR 0006 e decisões P1–P3 (fuso pelas regras do sistema, sem `zoneinfo`) | `0bcbcdf` |
| 1 | Auxiliares de formulário em `salesos/formularios.py` (sem mudar comportamento) | `0cb3804` |
| 2 | Dinheiro em centavos (`dinheiro.py`) | `3ab302b` |
| 3 | Modelo e migração `0003` | `f8d7c0a` |
| 4 | Serviço (R1–R10), schemas, período e R10 na anonimização | `1aac7cd` |
| 5 | Rotas e telas do funil | `dbaaf76` |
| 6 | Acessibilidade (Chromium) e ajustes da revisão geral | `d362785` |
| 7 | Documentação | commit da Etapa 7 |

| Critério de aceite | Resultado (Linux) |
|---|---|
| Ruff, formatação e mypy strict | Passou |
| pytest | 426 passed, 1 skipped (teste só do Windows), 1 aviso conhecido |
| Migração `0003`: upgrade, downgrade, upgrade de novo e `alembic check` (banco temporário) | Passou |
| CHECKs no banco (motivo só na perda, fechamento, ganha com valor não nulo, valor inteiro) | Passou (SQL direto) |
| R1–R10, P2 e histórico imutável | Passou (testes do serviço e das rotas) |
| Período local → UTC, inclusive horário de verão de 2018–2019 | Passou no Linux (contra `zoneinfo`); **não verificado no Windows** |
| CSRF, XSS, 303, 404/409, 422 no campo, GET sem efeito (banco inteiro) | Passou |
| Interface: 15 telas × 4 larguras, contraste, foco, alvos de 44 px, sem rolagem horizontal nem erro de CSP | Passou no Chromium |
| Windows | **Pendente**: checklist em `docs/setup.md` |

**Mutações detectadas** (Etapas 2 a 5): 3 casas decimais, sinal, dígitos Unicode e sem teto no dinheiro; CHECK de valor ingênuo (`NULL > 0`) e sem `typeof`; motivo não exigido; ganhar sem valor; movimentação duplicada; final para final; filtro em UTC e com o offset de hoje; evento com o título; reabertura que apaga histórico; anonimização sem limpar observações ou detalhe; editar uma ganha sem valor. Um teste fraco de R10 foi encontrado por mutação e corrigido.

**Revisões:** revisão de segurança independente (só leitura) em cada etapa de código e revisão geral da fase ("Ready to proceed"). Achados corrigidos: `reais()` sem tipo e teto (médio), valor fracionário aceito pelo SQLite (médio), zero à esquerda, inteiro sem limite no schema, id enorme no caminho → 500, teste de GET sem o dump completo, motivo trocado sem efeito, contagem "20" numa coluna cheia, alvos de toque de links soltos.

**Riscos e pendências que continuam:**
- **B1:** backups da `0002` são recusados depois da `0003`; precisa existir um procedimento testado de restaurar e migrar **antes de dados reais**.
- **P1:** finalidade e prazo de retenção dos dados comerciais de clientes anonimizados (`docs/privacy.md`) bloqueiam dados reais.
- Em `/clientes/{id}`, um id maior que o inteiro de 64 bits ainda gera erro 500 (pré-existente; fora do escopo da fase).
- A checagem de estrutura do backup não compara o texto dos CHECKs (pré-existente, ADR 0005).
- Fuso histórico no Windows não verificado (P3).

## Próximas
Fase 04 — Tarefas e agenda: só começa com aprovação explícita. Antes de dados reais, a checklist do Windows (`docs/setup.md`).
