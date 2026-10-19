# PostgreSQL guidance

`supabase-postgres-best-practices` provides PostgreSQL query, schema, index, connection, concurrency, and security guidance. It applies to PostgreSQL across providers; installing it does not adopt Supabase hosting, authentication, or an SDK.

## Requirements and installation

Use this project skill when the application uses PostgreSQL, including the toolkit's Drizzle/PostgreSQL default. Read the [official source](https://github.com/supabase/agent-skills/tree/main/skills/supabase-postgres-best-practices), verify its frontmatter name and license, and select the clients in use:

```bash
npx --yes skills@latest add supabase/agent-skills --list
npx --yes skills@latest add supabase/agent-skills --skill supabase-postgres-best-practices --agent codex claude-code --yes
```

Use the [local skill procedure](16-vercel-skills.md#local-installation) for portable files, lockfile, discovery, and project-only updates. A machine needs a compatible agent and runner; guidance alone does not require a database account or local PostgreSQL server.

## Use and verification

```text
Use supabase-postgres-best-practices to review this schema and query change.
Inspect the actual PostgreSQL version, ORM-generated SQL, indexes, row counts,
connection budget, transaction boundaries, and authorization requirements.
Explain each recommendation and how to validate it against this workload.
```

Start with the actual workload and migrations. Check query plans and index costs before recommending changes. `EXPLAIN ANALYZE` executes the statement; use an appropriate disposable database or an explicitly authorized target, especially for writes. RLS advice applies only when the product uses that security model; ORM predicates do not replace application authorization.

Generate and inspect SQL without credentials where supported. With an authorized test database, verify migration behavior, affected reads/writes, transactions, and connection lifecycle. An embedded compatibility engine is useful evidence but does not prove hosted PostgreSQL behavior, permissions, or production performance. Document those limits.

## Maintenance

Review source and lockfile diffs during a selected project-skill update. Recheck recommendations against the installed PostgreSQL/ORM versions and hosting limits through official documentation and Context7. Keep the existing provider and ORM unless a separate migration is authorized. Record discovered skill, applied recommendations, actual database checks, and pending access in `docs/setup.md` and `docs/quality.md`.
