# shadcn/ui skill

The official `shadcn` skill helps agents work with a project's component registry, CLI, and configuration. Adopt it when the project already uses shadcn/ui or explicitly chooses it. Existing UI systems remain valid; installing a skill does not select a design system.

## Requirements and installation

Read the [official skills guide](https://ui.shadcn.com/docs/skills) and [source](https://github.com/shadcn-ui/ui/tree/main/skills/shadcn). At the project root, select clients in use:

```bash
npx --yes skills@latest add shadcn/ui --skill shadcn --agent codex claude-code --yes
```

Use the [local skill procedure](16-vercel-skills.md#local-installation) for source files, lockfile, client links/copies, and updates. No global shadcn installation is needed. Use the project's existing package-manager runner for CLI commands.

## Inspect before changing components

Read `components.json`, existing components, tokens, aliases, and design conventions. Check current CLI help and inspect configuration:

```bash
npx --yes shadcn@latest info --json
```

This reveals framework, Tailwind, aliases, base library, icon library, and installed components. The skill can use host-specific dynamic command syntax; if the client does not execute it, run the documented inspection explicitly and verify the resulting context. Do not claim automatic execution from file presence.

```text
Use the shadcn skill to implement the requested component with this project's
existing base library, tokens, aliases, and accessibility conventions. Inspect
registry items and supported preview/diff options before applying changes.
```

Review registry sources and the proposed diff before adding code or dependencies. Choose only required components. Preserve existing customizations and test keyboard interaction, focus, labels, responsive layout, and the affected product flow. An uninitialized project should remain unchanged until choosing and initializing shadcn is within scope.

## Verification and maintenance

Verify source name and client discovery separately from CLI inspection. Record an actual component build/browser check only when performed in a compatible UI project. Update the skill through the shared project-only procedure, inspect the diff, and repeat affected checks. A skill update does not authorize replacing components, migrating the base library, or regenerating the design system.
