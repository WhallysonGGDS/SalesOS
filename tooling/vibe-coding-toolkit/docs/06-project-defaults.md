# New project defaults

This is the decision reference for the [bootstrap](04-project-bootstrap.md). Defaults provide a coherent foundation; explicit requirements and current evidence may justify adaptations. Record the choice in the project without installing tools merely because they appear here.

For adoption or updates in an existing application, follow [prompt 12](prompts/12-existing-project-setup.md). Preserve the stack and working equivalents; these new-project defaults do not authorize a migration.

## Default core

| Area | Initial choice | Limit |
|---|---|---|
| Application | Stable Next.js, App Router, strict TypeScript, Tailwind, ESLint, `src/`, `@/*` | Preserve the existing application and package manager |
| Persistence | Drizzle ORM + PostgreSQL, `pg` driver, Node.js runtime | A product explicitly without persistence may omit the database; record the reason in `PRODUCT.md` |
| Validation | Zod for environment, inputs, and external responses | Do not confuse TypeScript types with runtime validation |
| Server code | `server-only` for environment, logger, and database client | Secrets never belong in `NEXT_PUBLIC_*` or client components |
| Logging | Pino, structured fields, and known-secret redaction | Field redaction does not remove secrets written in free-form messages |
| Tests | Vitest in Node.js for server logic and boundaries | DOM, Testing Library, and E2E are added with flows that need them |
| UI | Accessible HTML, mobile first, Tailwind, and the `cn` helper | UI kits, tables, and form libraries depend on the actual interface |
| Quality | Next.js/TypeScript presets, focused typed async checks, 350-line limit, logging, and data boundary | Measure typed lint cost; Drizzle guards do not replace review |
| Agents | Shared `AGENTS.md`, Claude bridge, official local skills | Preserve client, model, and authentication; configure each host in its supported format |

Align Node.js types with the runtime and tool peers; retain supported combinations without forcing installation. The full lint profile and commands are in the [execution guide](04-project-bootstrap.md#6-apply-eslint-and-commands).

The [executable templates](../templates/next/) implement the server core. Use compatible stable versions checked at execution time; do not select `@beta`, `@rc`, `@canary`, or major versions merely because they are newer. Official documentation may show a prerelease example: check the registry channel before copying a command.

### Database and architecture

- Drizzle is the default ORM for a new application with data. Another ORM or database needs a concrete product reason recorded in `PRODUCT.md` and `docs/architecture.md`.
- Do not migrate an existing project to Drizzle as a side effect of bootstrap. Record the current stack and treat migration as separate work.
- Keep the schema in `src/db/schema/`, versioned SQL in `drizzle/`, and one connection entry point in `src/db/index.ts`.
- Initialize a bounded, reusable pool only when the database is used. `lint`, types, tests without I/O, and the initial build do not require real credentials.
- Validate `DATABASE_URL` before connecting, without including its value in errors. Use ignored `.env.local` and `.env.example` without real credentials.
- For migrations, prefer a direct connection when the provider requires one. The template accepts `DATABASE_URL_UNPOOLED` and falls back to `DATABASE_URL`.
- Generate SQL with `db:generate`, review the diff, and apply only to a known, authorized destination. Do not run migrations on import, during builds, or on every request. Do not add `db:push` to the default flow.
- Prefer additive changes and preserve applied migrations. Do not rewrite SQL to appear idempotent without understanding database history.
- Derive types with `$inferSelect`/`$inferInsert`. Choose keys and timestamps according to the model; do not impose one ID format on every product.
- Use parameterized queries, select required columns, bound listings, and avoid N+1. Return DTOs exposing only permitted fields.
- Use transactions when an operation requires atomicity and the driver supports them. An HTTP driver's limitation is not a global prohibition.
- Separate data access from presentation. Create feature modules when the first flow exists; do not generate empty DDD layers or wrappers for every call.

The `pg` driver uses Node.js. If the destination requires Edge or an HTTP driver, adapt and test the contract. In Vercel Functions, check current pooling and `attachDatabasePool` guidance; on other hosts, follow the equivalent lifecycle. Size the pool according to database limits and concurrent instances.

Sources: [Drizzle PostgreSQL](https://orm.drizzle.team/docs/get-started-postgresql), [migrations](https://orm.drizzle.team/docs/migrations), [ESLint Drizzle](https://orm.drizzle.team/docs/eslint-plugin), [node-postgres pooling](https://node-postgres.com/features/pooling), and [Vercel pooling](https://vercel.com/kb/guide/connection-pooling-with-functions).

### Validation, logging, and interface

Validate data received from forms, routes, and external services with Zod. Build inputs and responses from permitted fields; do not pass an entire body to the database. Place validation messages beside fields. Asynchronous operations provide progress states and prevent duplicate submissions.

Use the server logger with useful, bounded context. Do not indiscriminately log tokens, cookies, connection URLs, complete request bodies, or personal data. The initial redaction list is an additional defense; adapt it to actual names and structures. Public errors do not expose stacks or internal configuration.

Prefer Server Components and small client boundaries. Enable caching, React Compiler, and other options according to version documentation, required behavior, and tests. Preserve semantics, keyboard access, visible focus, contrast, error states, and reduced motion.

Sources: [Zod](https://zod.dev/), [Pino](https://github.com/pinojs/pino/blob/main/docs/redaction.md), [Vitest](https://vitest.dev/guide/), and [Vercel skills](tools/16-vercel-skills.md).

## Documentation created during bootstrap

Create four root files and five supporting documents in `docs/`. The [manifest](../templates/project-docs/manifest.json) points to their sources. Templates guide content: the LLM must fill them with the product description, generated code, executed commands, and actual decisions. Do not deliver copied placeholders.

| File | Source | Responsibility |
|---|---|---|
| `PRODUCT.md` | [Product](../templates/product.md.template) | Problem, audience, MVP, constraints, assumptions, and acceptance |
| `README.md` | [README](../templates/project-docs/README.md.template) | Project entry point, execution, and document map |
| `AGENTS.md` | [Instructions](../templates/AGENTS.md.template) | Commands, conventions, and shared agent rules |
| `CLAUDE.md` | [Bridge](../templates/CLAUDE.md.template) | Import `AGENTS.md` without duplicating policies |
| `docs/architecture.md` | [Code](../templates/project-docs/architecture.md.template) | Observed structure, boundaries, data, and technical decisions |
| `docs/design.md` | [Design](../templates/project-docs/design.md.template) | Visual direction, existing components, and accessibility |
| `docs/onboarding.md` | [Onboarding](../templates/project-docs/onboarding.md.template) | Local preparation, environment, database, and first workflow |
| `docs/quality.md` | [Quality](../templates/project-docs/quality.md.template) | What each check proves and when to run it |
| `docs/setup.md` | [Evidence](../templates/project-docs/setup.md.template) | Toolkit revision, sources, versions, scopes, and results |

`PRODUCT.md` is the canonical name, including in references. The historical path `templates/product.md.template` remains valid; the destination filename is uppercase.

In an existing project, preserve useful content. If `product.md` exists, consolidate it into `PRODUCT.md`, with an intermediate rename on case-insensitive filesystems. If two distinct versions exist, compare and merge content without blindly overwriting either. Update links in the same change.

Record only implemented structure in `docs/architecture.md`; label plans as plans. `docs/design.md` may start with visual direction and accessibility criteria without inventing a component catalog. `docs/quality.md` does not claim nonexistent tests or coverage. Add other documents when they have content and their own responsibility.

Both new and existing projects record the actual memory/index location, client loading mechanism, source/verification/invalidation rules, and observed retrieval in `docs/setup.md`. Reuse native memory and canonical documents; external memory remains optional. Temporary handoffs belong to an active task or plan, using the [handoff template](../templates/task-handoff.md.template) only when needed. `docs/quality.md` records the reusable [security review prompt](prompts/13-security-review.md), private report convention, and relevant [harness evaluations](07-harness-evaluation.md). These additions do not change the nine-document manifest.

## Features according to the product

| Confirmed need | Next choice |
|---|---|
| Login, roles, teams, or multi-tenancy | Choose authentication and test server-side authorization |
| Interactive remote state or a complex table | Evaluate TanStack Query/Table; preserve server fetching where sufficient |
| Complex form | Evaluate React Hook Form with Zod; simple forms can use native features |
| Shared UI | Evaluate accessible components and the chosen visual system without installing an entire catalog |
| Caching, rate limiting, jobs, or events | Choose a service/driver after defining consistency, operations, and cost |
| Monetary values | Define units, precision, rounding, and tests; avoid imprecise binary arithmetic |
| Internationalization, analytics, or external observability | Define audience, transmitted data, privacy, and required credentials |

Do not copy integrations, financial rules, hooks, local validation queues, metrics, or caches from the reference application. The useful default is the rule's intent, adapted to the new product.

## Capability selection

Use the [scope matrix](tools/README.md#select-by-scope) during both initial and repeat setup. Compatible Next.js projects can use runtime feedback and bundle analysis; PostgreSQL projects use the provider-independent SQL skill. CI repair requires a supported client and GitHub Actions; differential review serves security-sensitive changes. shadcn applies to the adopted UI system; Sentry requires a chosen service and authorized scope.

Keep project skills local and machine prerequisites reusable. Report an older Next.js version, unsupported bundler, missing browser runtime, unavailable account, or different UI/database as a concrete applicability decision. Optional capability requirements do not override the product's compatibility contract. Keep installation, discovery, and successful execution as separate evidence in `docs/setup.md`.

## Keep the recipe current

The recipe does not update itself. Each bootstrap run should:

1. Obtain a single toolkit revision and inspect the project before deciding.
2. Consult Context7 and official documentation for the components used. Compare examples with the registry's stable channel and installed CLI.
3. Review defaults against the product, runtime, hosting, and current recommendations. Suggest and apply compatible improvements within authorized setup, recording the reason and source.
4. Resolve and test a compatible combination; save actual versions in the lockfile. Do not replace a stable version with a prerelease merely to follow an example.
5. Check the official skills catalog rather than treating this toolkit's names and counts as permanent. Record installed skills and their sources.
6. Create documents from the actual state. Record date, sources, and reasons in `docs/setup.md`, using **validated**, **configured without execution**, or **pending**.
7. Run checks and review audits. A registry suggestion does not authorize an incompatible downgrade or a fix that loses data.

After bootstrap, a change in behavior, command, schema, or boundary updates the responsible document in the same change. Consult current evidence when changing a decision; do not turn an old recommendation into an absolute rule. Improvements requiring broad migration, paid services, publishing, or production data need relevant authorization.

In a toolkit checkout, a finding may become an update to the recipe and its checks. When starting another application from the public link, record the adaptation in that application; that access does not authorize publishing changes to the source repository.
