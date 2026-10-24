# Dependências e licenças

Fonte: metadados instalados pelo `uv sync` em 2026-10-19, com versões fixadas em `uv.lock`. Python 3.15.0.

## Diretas
| Pacote | Versão | Licença | Por quê |
|---|---|---|---|
| fastapi | 0.147.0 | MIT | Framework web |
| uvicorn | 0.54.0 | BSD-3-Clause | Servidor ASGI local (sem extras) |
| sqlalchemy | 2.1.5 | MIT | ORM e conexão |
| alembic | 1.20.0 | MIT | Migrações |
| pydantic-settings | 2.16.0 | MIT | Configuração por ambiente/.env |
| jinja2 | 3.1.6 | BSD-3-Clause | Templates HTML |
| python-multipart | 0.0.32 | Apache-2.0 | Leitura de formulários (CSRF e próximas fases) |
| pytest *(dev)* | 9.1.1 | MIT | Testes |
| httpx *(dev)* | 0.28.1 | BSD-3-Clause | Cliente do `TestClient` |
| ruff *(dev)* | 0.17.1 | MIT | Lint e formatação |
| mypy *(dev)* | 2.4.0 | MIT | Tipos |

## Transitivas de execução
| Pacote | Versão | Licença |
|---|---|---|
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| click | 8.5.0 | BSD-3-Clause |
| h11 | 0.16.0 | MIT |
| idna | 3.20 | BSD-3-Clause |
| Mako | 1.4.3 | MIT |
| MarkupSafe | 3.0.4 | BSD-3-Clause |
| opentelemetry-api | 1.45.1 | Apache-2.0 |
| pydantic | 2.14.1 | MIT |
| pydantic_core | 2.50.1 | MIT |
| python-dotenv | 1.2.4 | BSD-3-Clause |
| starlette | 1.9.0 | BSD-3-Clause |
| typing-inspection | 0.4.4 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |

## Transitivas de desenvolvimento
ast_serialize 0.13.1 (MIT), certifi 2026.10.18 (**MPL-2.0**), httpcore 1.0.9 (BSD-3-Clause), iniconfig 2.3.1 (MIT), librt 0.16.0 (MIT), mypy_extensions 1.1.0 (MIT), packaging 26.3 (Apache-2.0 OR BSD-2-Clause), pathspec 1.1.1 (**MPL-2.0**), pluggy 1.7.0 (MIT), Pygments 2.21.0 (BSD-2-Clause).

## Observações
- **Custo:** todas são gratuitas e de código aberto.
- **MPL-2.0** (certifi, pathspec): copyleft fraco por arquivo, só em ferramentas de desenvolvimento usadas sem modificação. Sem obrigação para o código do SalesOS.
- **opentelemetry-api:** exigida pelo FastAPI 0.147. Só a API, sem SDK nem exportador: não envia telemetria.
- **httpx × httpx2 (decisão D13, Fase 02):** o Starlette 1.9 avisa que usar `httpx` no `TestClient` está obsoleto e recomenda `httpx2` (BSD-3-Clause, mantido pela Pydantic). **Decisão:** manter `httpx` 0.28.1, que funciona com a versão atual, e documentar o aviso (`docs/quality.md`). Não migrar para `httpx2` nesta fase. Uma troca futura exige avaliação própria (versões, lock, testes, Windows) e autorização explícita.
- **Auditoria:** `uvx pip-audit --strict --disable-pip --no-deps -r <export do uv.lock>` em 2026-10-19 resultou em "No known vulnerabilities found".
