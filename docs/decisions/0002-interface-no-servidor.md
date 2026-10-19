# 0002 — Interface renderizada no servidor, sem JavaScript

**Status:** aceita (Fase 01)

**Decisão:** HTML em Jinja2 com auto-escape, CSS próprio com tokens, nenhum JavaScript nem fonte externa. A documentação interativa da API (`/docs`, `/redoc`, `/openapi.json`) fica desativada.

**Por quê:**
- Menos superfície de XSS e nenhuma etapa de build.
- Uma CSP restritiva (`default-src 'self'`) funciona sem exceções.
- O Swagger carregaria scripts de CDN, bloqueados pela CSP.

**Consequências:** interações ricas, se forem necessárias, entram com JavaScript local, justificado e compatível com a CSP.
