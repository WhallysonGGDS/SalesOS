# Design

## Direção
Escuro, minimalista, editorial. Uma marca monumental na entrada, muito espaço negativo e dados em lista de definições. Sem cards, sem decoração. A lista de clientes é um índice com linhas finas. No funil, as quatro etapas em andamento ficam lado a lado na ordem real e os resultados (ganha, perdida) numa faixa separada por uma linha mais forte; cada oportunidade é uma linha de índice (título, cliente, valor), nunca um card. O elemento marcante é a linha do tempo: uma régua vertical com as datas numa coluna à esquerda, em que o que pessoas registraram aparece inteiro e os eventos automáticos do sistema ficam em segundo plano.

## Tokens (`src/salesos/web/static/app.css`)
| Token | Valor | Uso | Contraste sobre `--noite` |
|---|---|---|---|
| `--noite` | `#0a1120` | Fundo | — |
| `--superficie` | `#101a2e` | Fundo dos campos | — |
| `--linha` | `#1c2940` | Divisores decorativos (nunca bordas de controle) | 1,29 |
| `--borda` | `#5d6d88` | Bordas de campos e botões | 3,60 (WCAG 1.4.11 exige 3) |
| `--texto` | `#e9edf4` | Texto principal, botão principal | 16,06 |
| `--cinza` | `#8b96aa` | Texto secundário e rótulos | 6,32 |
| `--gelo` | `#8ab8ff` | Único acento: foco e página atual | 9,32 |
| `--alerta` | `#ff9a9a` | Erros e a ação irreversível (anonimizar) | 9,28 |

Tipografia: fontes do sistema (Segoe UI Variable no Windows 11), sem fontes externas, porque a CSP bloqueia recursos de fora e o app é local. Números tabulares em toda a interface.

Botões: o principal é claro sobre o escuro (um por tela), o secundário tem só a borda e o de perigo usa `--alerta`. Toda área clicável tem 44 px de altura mínima (`--alvo`).

## Acessibilidade (implementado e verificado na E6, no Chromium do Linux)
- `lang="pt-BR"`, link "Ir para o conteúdo", um `h1` e um `main` por página, a navegação marca a seção atual com `aria-current="page"`.
- Todo campo tem `<label for>`. Erros aparecem no campo, com o prefixo "Erro:" (a informação não depende só da cor), `aria-invalid` e `aria-describedby`, além de um resumo com `role="alert"`.
- Botões e links repetidos levam o nome do contato no texto acessível ("Remover contato Fulano").
- Datas da linha do tempo em `<time datetime>` (UTC).
- Foco visível em azul gelo em toda parada do Tab, inclusive dentro do `datetime-local`.
- Contraste medido em todo texto visível de 7 telas × 4 larguras (320, 390, 768 e 1440 px): nenhuma falha (mínimo 4,5:1; 3:1 para texto grande).
- Sem rolagem horizontal em 320 px (reflow, WCAG 1.4.10).
- Animação única de entrada da marca, desligada com `prefers-reduced-motion`. Suporte básico a `forced-colors`.

Não verificado: leitor de tela (NVDA ou Narrador), zoom real do navegador a 200% e 400%, a fonte Segoe UI Variable e o seletor de data no Windows.
