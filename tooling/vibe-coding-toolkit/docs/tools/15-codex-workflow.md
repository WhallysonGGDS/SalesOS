# Codex: installation, instructions, and integrations

Codex has its own CLI, application, and integrations. This guide explains how to use the toolkit with `AGENTS.md`, plugins, skills, and MCPs. To prepare the whole computer, use [environment setup](../03-environment-setup.md); for the narrated Claude Code workflow, use the [playbook](../02-playbook-onboarding.md).

To configure or update the applicable toolkit in an existing project, use [prompt 12](../prompts/12-existing-project-setup.md), covering diagnosis, brainstorming, harness, and validation.

References checked on **October 14, 2026**. Consult the sources again before installing or migrating: commands and formats can change.

## Install and authenticate

The [official CLI documentation](https://learn.chatgpt.com/docs/codex/cli) offers a native installer, npm, and Homebrew. Choose one method and preserve the existing method when supported.

```bash
# Alternative for existing Node.js/npm users
npm install -g @openai/codex

# Check the available executable
codex --version

# Open the agent in the project
codex
```

On first run, choose **Sign in with ChatGPT**. The [official authentication guide](https://learn.chatgpt.com/docs/auth) describes other methods too; this setup prefers preserving ChatGPT authentication without enabling API billing. Do not store credentials in templates, project instructions, or the manifest.

## Use `AGENTS.md` for project instructions

Codex [discovers instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md) at different scopes: the global configuration directory and the path from the project root to the working directory. In each directory, `AGENTS.override.md` takes precedence over `AGENTS.md`. Instructions closer to the working directory refine earlier ones.

Use the [shared template](../../templates/AGENTS.md.template) to create `AGENTS.md` in the target project. Fill in the stack, canonical commands, and conventions. If the file already exists, incorporate only useful parts without overwriting preferences.

In Claude Code, you can import this file from `CLAUDE.md`, as described in the [memory documentation](https://code.claude.com/docs/en/memory):

```markdown
@AGENTS.md

## Claude Code

[Client-specific instructions, if needed.]
```

Codex discovers `AGENTS.md` directly. Do not assume every Claude import syntax is interpreted the same way by other clients. Absolute personal paths belong in user configuration, outside the shared template.

## Install plugins and check skills

Plugins can distribute skills, MCPs, and hooks. For [Superpowers in Codex](https://github.com/obra/superpowers#codex-cli), open `/plugins` in the session, search for Superpowers, and install the official distribution. In the application, use the Plugins area. Installing the Claude Code plugin does not install it in Codex.

For plugins documenting their own marketplace, current examples are:

```bash
# Ponytail: terminal
codex plugin marketplace add DietrichGebert/ponytail
codex plugin add ponytail@ponytail

# Context7: choose the plugin OR the direct MCP in the next section
codex plugin marketplace add upstash/context7
codex plugin add context7@context7-marketplace
```

Sources: [Ponytail](https://github.com/DietrichGebert/ponytail#install) and [Context7 clients](https://context7.com/docs/resources/all-clients). For Ponytail, open `/hooks`, inspect and trust the hooks through the client's workflow, then start a new conversation. Keep intensity at `full` for coding.

If a tool is distributed as a standalone skill, use the [skill discovery](https://learn.chatgpt.com/docs/build-skills) paths: `.agents/skills/<name>/SKILL.md` in the project or `~/.agents/skills/<name>/SKILL.md` for the user. Symbolic links are supported. Plugins manage their own files; copying the same skills into these directories can create duplicates.

In Codex, select a skill by the name shown in the client or invoke it with `$name`. Plugins may add a namespace, such as `$ponytail:ponytail-review`. Do not assume Claude Code's `/plugin` commands or subagent names exist in Codex.

Ask the agent to list discovered skills and check their origin before validation. An existing directory without a discovered skill remains an incomplete setup.

## Work continuity

Adopt the [execution continuity agreements](../02-playbook-onboarding.md#execution-continuity) and the block in the [shared AGENTS template](../../templates/AGENTS.md.template). Status questions do not end authorized work; blockers affect only dependent work. Confirm a worker has stopped before taking over files, check the checkout when resuming, and preserve permissions and limits. These instructions do not guarantee execution after the turn or replace verifiable active processes.

## Project configuration and skills

To start Next with product documentation, lint, and skills, follow the [bootstrap](../04-project-bootstrap.md). Install the Vercel collection locally as described in the [catalog](16-vercel-skills.md), selecting `--agent codex`; if you also use Claude, select both clients. Do not copy a global cache or duplicate already-discovered plugins.

Local configuration belongs in `.codex/config.toml` and loads only in trusted projects. The [Context7 template](../../templates/project/codex.config.toml.example) is an alternative when no active connection exists; reconcile it with existing configuration and keep authentication outside the repository. Do not add personal model, provider, or permission options to the template. Source: [official configuration](https://learn.chatgpt.com/docs/config-file/config-advanced).

Global plugins remain global. `AGENTS.md`, local skills, product documentation, lint, and Graphify exclusions belong to the project. Bootstrap does not install Git blockers or commit/push hooks.

## Connect Context7 through MCP

Use this alternative when no plugin already provides the same server. The [Context7 documentation](https://context7.com/docs/resources/all-clients) describes local and remote clients; the remote endpoint avoids installing a local MCP package.

```bash
codex mcp add context7 --url https://mcp.context7.com/mcp
codex mcp list
```

If the service requires authentication or limits anonymous access, follow its official flow and keep secrets outside the repository. Start a new session and test a documentation query. `codex mcp list` proves registration, but not a server response.

The lookup workflow is `resolve-library-id` with the library and objective, followed by `query-docs` with `libraryId` and `query`. Use one query per concept and check the project's version. Do not send private code, credentials, or personal data. See [Context7](12-context7.md) for complete examples.

## Integrate RTK and Graphify

[RTK documents native Codex hooks](https://github.com/rtk-ai/rtk/blob/develop/docs/guide/getting-started/supported-agents.md). After installing the binary and backing up existing configuration:

```bash
rtk init --global --codex
```

Open a new session and confirm a supported command is rewritten. The hook changes the command before execution; it must not execute a separate copy itself. If an equivalent integration exists, reconcile configurations and avoid another hook for the same purpose.

Without an active hook on that surface, use `rtk git status`, for example. For complete output or unsupported commands, use `rtk proxy <command>`. More details: [RTK](03-rtk-token-proxy.md).

[Graphify](https://github.com/Graphify-Labs/graphify) provides installation through `graphify install`, which detects compatible agents. Check Codex skill installation in a new session. For semantic extraction or delegation, preserve native Codex, the main model, and ChatGPT login. Without an authorized selection policy, pass the session model; with one, follow [task-based routing](02-subagent-orchestration.md#part-b--model-selection-discipline), respecting explicit restrictions. Do not silently substitute an API backend or another LLM. See [Graphify](07-graphify.md).

## Permissions and persistence

The setup prompt requests full access without routine approvals. In the CLI using the documented sandbox keys, the corresponding block in `~/.codex/config.toml` is:

```toml
approval_policy = "never"
sandbox_mode = "danger-full-access"
```

These options grant broad filesystem and network access, as described in the [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference). Back up the existing file and incorporate the block without replacing model, provider, or MCP settings. Use this mode only in its authorized context, such as the requested setup.

Versions and surfaces may also expose their own permission profiles. Check the mechanism supported by the current installation and verify the effective state in a new session. Organization policies and operating-system permissions can limit the result. A configured CLI does not prove the desktop application or an already-open session received the same permissions.

## Validate without relying on the old session

- Open a new terminal and conversation; check the executable, authentication, and model.
- Confirm which instruction files were loaded and override precedence.
- Discover and use a suitable skill for a small task, without publishing or paid test calls.
- Run a real Context7 query and check the result.
- Check one RTK command execution without duplication, and complete output through `rtk proxy`.
- Verify Graphify integration without starting paid semantic extraction.
- Record outstanding hooks, login, permissions, or policy issues; do not treat files on disk as validation.
