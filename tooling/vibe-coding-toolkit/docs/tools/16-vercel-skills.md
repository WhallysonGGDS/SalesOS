# Vercel skills per project

[agent-skills](https://github.com/vercel-labs/agent-skills) contains the skills. [skills](https://github.com/vercel-labs/skills) provides the `npx skills` CLI and `find-skills` skill. These serve different purposes; installing the CLI does not automatically install the collection.

Names below are the `name` fields, which may differ from folder names or README titles. Discover the current upstream catalog before installation or updates; the [validation report](../05-toolkit-validation.md) records dated evidence.

## Web and mobile catalog

| Installable skill | Purpose and workflow stage | Next web bootstrap |
|---|---|---|
| [`vercel-react-best-practices`](https://github.com/vercel-labs/agent-skills/blob/main/skills/react-best-practices/SKILL.md) | When writing/reviewing React and Next: data, parallel execution, bundles, server, and rendering | Install; apply from implementation onward |
| [`vercel-composition-patterns`](https://github.com/vercel-labs/agent-skills/blob/main/skills/composition-patterns/SKILL.md) | When structuring components and their APIs; reuse composition when there is a concrete need | Install; do not create a component library in advance |
| [`web-design-guidelines`](https://github.com/vercel-labs/agent-skills/blob/main/skills/web-design-guidelines/SKILL.md) | Interface review: accessibility, keyboard, focus, forms, states, and performance | Install; review screens before completing UI changes |
| [`writing-guidelines`](https://github.com/vercel-labs/agent-skills/blob/main/skills/writing-guidelines/SKILL.md) | Review documentation and prose against the handbook; adapt to project language and audience | Install; review delivered documentation |
| [`vercel-react-view-transitions`](https://github.com/vercel-labs/agent-skills/blob/main/skills/react-view-transitions/SKILL.md) | When transitions are requested; check React/Next versions and reduced motion | Install; do not automatically enable experimental APIs or animations |
| [`vercel-optimize`](https://github.com/vercel-labs/agent-skills/blob/main/skills/vercel-optimize/SKILL.md) | Once a Vercel project and metrics exist: cost, caching, functions, and performance | Install; audit when access and a relevant task exist |
| [`deploy-to-vercel`](https://github.com/vercel-labs/agent-skills/blob/main/skills/deploy-to-vercel/SKILL.md) | Publishing or previews requested by the user; check the method and target account | Install; do not run during bootstrap |
| [`vercel-cli-with-tokens`](https://github.com/vercel-labs/agent-skills/blob/main/skills/vercel-cli-with-tokens/SKILL.md) | Vercel operations already using token authentication | Install; use only when this method is selected, without storing tokens in the repository/chat |
| [`vercel-react-native-skills`](https://github.com/vercel-labs/agent-skills/blob/main/skills/react-native-skills/SKILL.md) | React Native and Expo: lists, gestures, animation, and native APIs | Optional; install only for mobile platforms |
| [`find-skills`](https://github.com/vercel-labs/skills/blob/main/skills/find-skills/SKILL.md) | Discover an additional capability when the installed foundation cannot meet a need | Install; discovery does not authorize indiscriminate extra installations |

Check upstream during every bootstrap: incorporate relevant official web skills, reconcile removed/renamed names, and record the selection. The mobile skill applies to its platform. Deployment skills remain available for requested tasks; setup does not publish. The broader [tool catalog](README.md#select-by-scope) adds Next.js runtime/bundle workflows, PostgreSQL, CI repair, security review, shadcn, and Sentry according to project needs.

## Local installation

At the project root, check the current catalog:

```bash
npx --yes skills@latest add vercel-labs/agent-skills --list
npx --yes skills@latest add vercel-labs/skills --list
```

For a project used with Claude Code and Codex:

```bash
npx --yes skills@latest add vercel-labs/agent-skills --skill vercel-react-best-practices vercel-composition-patterns web-design-guidelines writing-guidelines vercel-react-view-transitions vercel-optimize deploy-to-vercel vercel-cli-with-tokens --agent codex claude-code --yes
npx --yes skills@latest add vercel-labs/skills --skill find-skills --agent codex claude-code --yes
```

Without `--global`/`-g`, installation belongs to the project. `--agent` selects clients, not models. If you use one client, select only that one; for another supported agent, use its CLI-documented identifier. Avoid `--all`, which also selects unnecessary platforms and clients.

Additional installation for React Native/Expo projects:

```bash
npx --yes skills@latest add vercel-labs/agent-skills --skill vercel-react-native-skills --agent codex claude-code --yes
```

The default layout uses `.agents/skills/` for canonical content and links in client paths where needed. Check the actual paths for the installed version. Version content, **relative** links, and `skills-lock.json`; preserve attribution and licenses. Do not use absolute links to machine caches. On Windows, add `--copy` to avoid junctions with absolute targets; use the same mode for clients without link support. Record this choice and update copies through the CLI.

Before installing, inventory local/global skills and plugins. A skill with the same `name` can appear twice; Codex does not merge identically named files. Resolve overlap within the project scope without deleting global preferences used by other projects. Source: [official Codex discovery](https://learn.chatgpt.com/docs/build-skills).

## Usage workflow

1. **Understand:** `PRODUCT.md`, Context7 for current APIs, and Superpowers when the request requires design/planning.
2. **Build:** Ponytail maintains scope; `vercel-react-best-practices` guides Next/React; `vercel-composition-patterns` informs component decisions.
3. **Review:** lint, types, relevant tests, and build; `web-design-guidelines` for UI and `writing-guidelines` for documentation.
4. **Refine when requested:** `vercel-react-view-transitions` for compatible animations; `find-skills` when a concrete capability is missing.
5. **Publish when requested:** `deploy-to-vercel` or `vercel-cli-with-tokens`, according to the chosen method. Afterward, `vercel-optimize` uses available metrics.

Explicit user instructions override skill defaults. No skill authorizes choosing another model, requiring a particular agent, adding preventive dependencies, or publishing without a request.

## Verify and update

```bash
npx --yes skills@latest list --agent codex claude-code
```

Compare the list with the catalog, check frontmatter and links, and record the result in `docs/setup.md`. Open a new session for each client used and check discovery when the host allows it. Files on disk prove installation, not skill execution by the client.

For an intentional project update:

```bash
npx --yes skills@latest update --project --yes
```

Check `--help` before using options in another version. Do not assume older commands, such as `skills check`, exist in the current CLI. Review the diff and `skills-lock.json`, validate affected workflows, and include the observed version/revision in the report. Do not update global skills as a side effect of a local update.
