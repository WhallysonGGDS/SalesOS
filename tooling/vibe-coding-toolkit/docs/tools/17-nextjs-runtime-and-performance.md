# Next.js runtime and performance skills

Use the official `next-dev-loop` and `next-bundle-optimizer` skills for feedback from a running Next.js application and evidence-based bundle investigation. They complement the [Vercel skills](16-vercel-skills.md), tests, and [browser automation](11-agent-browser.md).

## Requirements and scope

Install instructions in the **project**. Prepare browser tooling through [machine setup](../03-environment-setup.md); project setup checks and reuses it.

| Skill | Use | Compatibility to check |
|---|---|---|
| `next-dev-loop` | Compile, inspect runtime issues and routes, exercise the page, and repeat | The source currently requires Next.js 16.3+ with Turbopack, `agent-browser` 0.31.1+ on PATH, and a running development server |
| `next-bundle-optimizer` | Audit bundle composition, then compare a requested optimization | Check the installed Next.js analyzer commands and the skill's prerequisites before running |

The runtime skill calls the application's `/_next/mcp` endpoint directly. Its compatibility floor is stricter than the general Next.js MCP endpoint requirement; endpoint presence alone does not prove compatibility. An older application or a Webpack configuration may leave this capability unavailable. Record the reason and use existing checks; an optional skill does not authorize a framework or bundler migration.

## Install and discover

Check the [official Next.js agent guide](https://nextjs.org/docs/app/guides/ai-agents) and the source frontmatter: [next-dev-loop](https://github.com/vercel/next.js/blob/canary/skills/next-dev-loop/SKILL.md) and [next-bundle-optimizer](https://github.com/vercel/next.js/blob/canary/skills/next-bundle-optimizer/SKILL.md). The source branch `canary` does **not** require a canary application dependency.

At the project root, select only clients in use:

```bash
npx --yes skills@latest add https://github.com/vercel/next.js/tree/canary/skills/next-dev-loop --skill next-dev-loop --agent codex claude-code --yes
npx --yes skills@latest add https://github.com/vercel/next.js/tree/canary/skills/next-bundle-optimizer --skill next-bundle-optimizer --agent codex claude-code --yes
npx --yes skills@latest list --agent codex claude-code
```

Follow the [shared installation and update procedure](16-vercel-skills.md#local-installation): keep canonical sources and lockfile, use portable links or `--copy`, and verify discovery in a fresh client session. Inspect the installed `SKILL.md` before using its commands.

On Windows, the skills CLI may clone the full Next.js repository, whose test fixture paths exceed the default Git path limit. If checkout reports `Filename too long`, enable `core.longpaths=true` for the installer's child Git processes through [Git's process-scoped configuration](https://git-scm.com/docs/git-config#Documentation/git-config.txt-GIT_CONFIG_COUNT). Append a `GIT_CONFIG_KEY_<n>`/`GIT_CONFIG_VALUE_<n>` pair and increment `GIT_CONFIG_COUNT`, preserving inherited entries; restore the shell environment afterward. Do not change global Git settings as a side effect. `--copy` addresses client links, not clone path length. The toolkit validator applies this process-only override automatically on Windows; [Git for Windows documents its scope](https://github.com/git-for-windows/git/blob/main/Documentation/config/core.adoc#corelongpaths).

## Development loop

Start the existing development command on a free local port. Ask:

```text
Use next-dev-loop for this change. Verify its preflight against the installed
Next.js version and bundler, inspect compilation issues and routes, exercise the
affected page with agent-browser, and report runtime and browser evidence.
```

The preflight must enumerate endpoint tools and check `get_compilation_issues` and `get_routes`; a successful HTTP page response is insufficient. Use a named browser session and stable page assertions. Stop only resources created for the task. Preserve `.next` while the development server runs; isolate build output or stop that server before a production build. Session naming scoped to a worktree does not require creating a Git worktree.

For version-matched API guidance, prefer documentation shipped with the installed Next.js package when available, then official docs/Context7. See the [Next.js MCP guide](https://nextjs.org/docs/app/guides/mcp).

## Bundle audit and updates

```text
Use next-bundle-optimizer to audit this application. Identify expensive routes
and dependencies with analyzer evidence, and propose the smallest useful change.
Keep application source, dependencies, and lockfile unchanged during the audit.
```

Check `next analyze --help` and `next analyze export --help` through the project's runner. If unsupported, record the limitation. Keep before/after exports in distinct locations; compare the same route, build mode, and compressed-size metric. Apply fixes only within the authorized request, then run behavior checks and inspect loading timing, accessibility, and server/client boundaries. Do not enable caching or change product behavior merely to improve a bundle number.

Update selected project skills with the shared procedure, review source/lockfile changes, recheck compatibility, and repeat the affected loop or audit. Record installation, discovery, runtime preflight, browser checks, and performance measurements separately in `docs/setup.md`.
