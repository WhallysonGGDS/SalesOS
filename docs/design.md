# Design

## Direção
Escuro, minimalista, editorial. Uma marca monumental, muito espaço negativo e dados reais em lista de definições, sem cards, sem menu falso e sem decoração.

## Tokens (`src/salesos/web/static/app.css`)
| Token | Valor | Uso |
|---|---|---|
| `--noite` | `#0a1120` | Fundo |
| `--superficie` | `#101a2e` | Superfícies elevadas |
| `--linha` | `#1c2940` | Divisores (quando houver) |
| `--texto` | `#e9edf4` | Texto principal |
| `--cinza` | `#8b96aa` | Texto secundário e rótulos |
| `--gelo` | `#8ab8ff` | Único acento: estado ativo e foco |

Tipografia: fontes do sistema (Segoe UI Variable no Windows 11), sem fontes externas. A CSP bloqueia recursos de fora, e o app é local.

## Acessibilidade (implementado)
- `lang="pt-BR"`, link "Ir para o conteúdo", foco visível em azul gelo.
- Animação única de entrada da marca, desligada com `prefers-reduced-motion`.
- Layout fluido sem rolagem horizontal a 390 px e 1440 px (verificado no Chromium).

Não verificado: leitor de tela e medição formal de contraste. Ficam para a Fase 02, com `design:accessibility-review`.
