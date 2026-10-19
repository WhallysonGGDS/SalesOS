# 0003 — Proteções de uma aplicação local

**Status:** aceita (Fase 01)

**Contexto:** mesmo sem login, um app em `127.0.0.1` pode ser atacado por páginas abertas no navegador do usuário (CSRF) e por DNS rebinding.

**Decisão:**
- `Settings.host` só aceita loopback.
- `TrustedHostMiddleware` com `127.0.0.1`, `localhost` e `[::1]`, em lista fixa no código (não configurável por `.env`).
- Cabeçalhos: CSP, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: no-referrer`, COOP.
- CSRF por double-submit **assinado**: o cookie aleatório é HttpOnly e SameSite=Strict; o formulário envia `HMAC-SHA256(segredo, cookie)`; a comparação é em tempo constante (`hmac.compare_digest`). Vale para POST, PUT, PATCH e DELETE, via dependência global. Usa só a biblioteca padrão, sem dependência nova.
- O segredo do HMAC tem no mínimo 32 caracteres. Um valor vazio no `.env` é ignorado e o padrão aleatório é usado; um valor curto é recusado.

**Consequências:**
- Sem `SALESOS_SECRET_KEY` fixo, reiniciar o servidor invalida formulários abertos.
- A dependência global só cobre rotas FastAPI. `app.mount`, rotas Starlette puras e websockets ficam fora: não usar sem uma proteção própria.
- Expor na rede exige HTTPS, cookies `Secure`, autenticação e uma revisão própria (Fase 07 ou posterior).
