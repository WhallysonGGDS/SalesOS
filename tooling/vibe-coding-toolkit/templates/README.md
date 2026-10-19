# Templates

Copy only the component you need. These files are sources for adaptation, not a ready-made application or standalone installer. The [bootstrap](../docs/04-project-bootstrap.md) defines the order; the [defaults](../docs/06-project-defaults.md) define the decisions.

For an existing project, [prompt 12](../docs/prompts/12-existing-project-setup.md) reconciles these templates with the structure, tools, and documents already adopted.

| Directory or file | Use | Destination |
|---|---|---|
| [project-docs/manifest.json](project-docs/manifest.json) | Single map of initial documentation | Four root files and five in `docs/` |
| [product.md.template](product.md.template) | Product, MVP, assumptions, and acceptance | `PRODUCT.md`; source path retained for compatibility |
| [AGENTS.md.template](AGENTS.md.template) and [CLAUDE.md.template](CLAUDE.md.template) | Shared instructions and Claude bridge | Root, merging existing instructions |
| [next/](next/) | Environment, logger, Drizzle connection, UI helper, and tests | Same application tree; remove only the `.example` suffix, preserving `.env.example` |
| [eslint/next-app.config.mjs.example](eslint/next-app.config.mjs.example) | Full profile for the core with Drizzle | `eslint.config.mjs` and the `eslint-rules/` directory |
| [eslint/next.config.mjs.example](eslint/next.config.mjs.example) | Lightweight Next.js profile without mandatory logging/database | `eslint.config.mjs` and the `eslint-rules/` directory |
| [eslint/next.typed.config.mjs.example](eslint/next.typed.config.mjs.example) | Focused async correctness gate for new Next.js projects | `eslint.typed.config.mjs`, after the base config |
| [eslint/eslint.config.mjs.example](eslint/eslint.config.mjs.example) and [typed profile](eslint/eslint.typed.config.mjs.example) | Advanced adoption in an existing codebase | Merge into existing lint configuration |
| [eslint/verify.mjs](eslint/verify.mjs) | Local rule self-check | `scripts/verify-quality-rules.mjs` |
| [project/](project/) | Context7 per client and Graphify exclusions | `.codex/config.toml`, `.mcp.json`, or `.graphifyignore`, when needed |
| [Sentry Codex](project/sentry.codex.config.toml.example) and [Sentry Claude](project/sentry.mcp.json.example) | Optional project-scoped OAuth connection for a chosen service | Merge into `.codex/config.toml` or `.mcp.json`, replace scope identifiers, and follow the [Sentry guide](../docs/tools/22-sentry-mcp.md) |
| [environment-manifest.json.example](environment-manifest.json.example) | Machine setup inventory | Follow the [global guide](../docs/03-environment-setup.md) |
| [settings.json.example](settings.json.example) and [hooks/](hooks/) | Optional client hook examples | Only in the chosen integration; these are not Git hooks |
| [rules/](rules/) | Delegation protocol, when used | Relevant project instructions |
| [task-handoff.md.template](task-handoff.md.template) | Verified state and next action for unfinished work | Existing task/plan location; only when work spans sessions |
| [security-review.md.template](security-review.md.template) | Findings, evidence, scope, and limitations | Private location outside the reviewed repository by default |
| [harness-evaluation/](harness-evaluation/) | Deliberately broken local authorization fixture | Disposable copy only; follow the [evaluation guide](../docs/07-harness-evaluation.md) |

Fill documents with project facts; remove instructions and placeholders. Document template links are relative to the **destination**, defined in the manifest. Next.js modules require the guide's dependencies and scripts; do not copy them into this toolkit's root.
