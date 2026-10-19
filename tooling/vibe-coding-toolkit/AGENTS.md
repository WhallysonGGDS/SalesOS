# Vibe Coding Toolkit

This repository distributes documentation, prompts, and templates. It is not a Next.js application; projects are generated in separate directories.

## Scope and sources

- Preserve the entry points: machine setup, project bootstrap, and tool-specific adoption.
- Recipe: `docs/04-project-bootstrap.md`; defaults: `docs/06-project-defaults.md`; entry point: `docs/prompts/11-next-project-bootstrap.md`.
- Catalog: `docs/tools/16-vercel-skills.md`. Use the `name` from `SKILL.md`, rather than inferring it from the directory name.
- Generated documents: `templates/project-docs/manifest.json`, with four root files and five files in `docs/`. Product destination: `PRODUCT.md`; preserve the historical URL `templates/product.md.template`.
- Portable instructions: `templates/AGENTS.md.template`; the Claude template imports that file.
- Use current official sources and Context7 where relevant. Never send secrets in queries.
- English is the canonical language for documentation, prompts, templates, examples, and assets. Only `README.pt-BR.md` and `README.es.md` are localized; keep them aligned with `README.md`. Agent conversations follow the user's language.

## Changes and validation

- Reuse templates and rules. Do not add an application, custom generator, or product dependencies at the root.
- Keep public paths in English; update links, anchors, indexes, recipes, and examples together when their contracts change.
- Validate executable templates in a temporary project; check local links, configuration syntax, and `git diff --check`.
- Validator regression tests: `node --test scripts/validate-docs.test.mjs`. Links, anchors, manifest, and JSON: `node scripts/validate-docs.mjs`.
- Reproducible baseline validation: `node scripts/validate-next.mjs` with Node.js 24, npm, and network access. It creates and removes the temporary project; dependencies stay outside the root.
- Rule self-check: `node templates/eslint/verify.mjs templates/eslint/eslint-rules/index.cjs`, in an environment with ESLint available.
- Do not copy credentials, private domains, dumps, personal caches, or tightly coupled harnesses into public examples.
- Do not add Git blockers, branch/worktree requirements, or commit/push hooks.
- Publishing and pushing require an explicit request. The bootstrap does not publish the application.

## Agents

- Ponytail `full`: the smallest complete change, preserving security, accessibility, and relevant checks.
- Caveman: concise conversation in the user's language; normal wording for code, documentation, and commits.
- Respect existing authorization and directly requested execution; do not repeat design/plan approvals.
- Public content works with different LLMs. Configure Claude and Codex separately; do not hardcode a personal model, provider, or authentication method in templates.
- Preserve the session's client, model, and authentication; do not enable proxies or API billing as a side effect of Graphify/Caveman.
- Relevant, supported delegation specifies the authorized model, files, and completion criteria.
