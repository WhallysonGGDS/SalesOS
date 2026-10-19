# Machine setup: how to use the complete prompt

Use [prompt 10 — development environment](prompts/10-development-environment-setup.md) to prepare a new machine or update and fix an existing environment. It requests execution, backups, agent integration, and tests in new sessions. Installing binaries is only part of the work.

Setup targets the global environment. To **start a Next.js project**, use the [bootstrap](04-project-bootstrap.md) afterward. To adopt the workflow in an existing project, use the [playbook](02-playbook-onboarding.md) or [Codex guide](tools/15-codex-workflow.md). Vercel skills are installed in the project, following the [catalog](tools/16-vercel-skills.md).

## 1. Choose where to run

Use Codex or Claude Code with terminal and file access on the computer receiving setup. If the session runs in a container, VM, WSL, or remote server, that is the environment it can prepare. State the destination explicitly when there is more than one.

A machine without an agent needs an initial installation to receive the prompt. Choose **one** agent to start; the prompt installs the other during setup. The examples below come from the [official Codex CLI instructions](https://learn.chatgpt.com/docs/codex/cli) and [Claude Code](https://code.claude.com/docs/en/overview). Consult those pages if your operating system or installation method differs.

macOS, Linux, or WSL — choose one command:

```bash
# Codex: native installer
curl -fsSL https://chatgpt.com/codex/install.sh | sh

# Claude Code: native installer
curl -fsSL https://claude.ai/install.sh | bash
```

Native Windows — choose one command in PowerShell:

```powershell
# Codex: native installer
irm https://chatgpt.com/codex/install.ps1 | iex

# Claude Code: native installer
irm https://claude.ai/install.ps1 | iex
```

These installers do not require Node.js beforehand. Open a new terminal, run `codex` or `claude`, and complete authentication through the official flow. For Codex, choose ChatGPT login as preferred by the prompt. Credentials, codes, and passwords stay in the login flow, never in the conversation.

If an agent already works, start there. The prompt preserves the existing method where supported and avoids a second competing installation.

## 2. Run the prompt

Open [prompt 10](prompts/10-development-environment-setup.md) and paste **the entire “Prompt” section block** into the agent conversation. The text already authorizes the required foundation, global development updates, and necessary fixes.

With this repository open in the agent, use this shortcut:

```text
Read docs/prompts/10-development-environment-setup.md and execute the entire “Prompt” section block on this computer.
Use templates/environment-manifest.json.example as the initial manifest format and add global components found during inventory.
Save the report, manifest, and backups in a user setup directory outside projects. State the paths and how to restore configurations.
```

If you are working in another directory, provide the actual file path. The URL shortcut is on the prompt page and requires this version to be published on `main`. The local file lets you use changes before publication.

Before sending, add context the agent cannot discover itself, where applicable:

```text
Destination: [this computer / native Windows / WSL / identified remote server].
Projects whose versions must be preserved: [local paths, without credentials].
Previous manifest: [path, if any].
Organization or system constraints: [describe, if any].
```

## 3. Understand what is required

The toolkit supports partial adoption. **In this specific prompt**, every baseline item is required: the agent must install missing tools and configure supported integrations. An incompatibility requires a recorded reason and alternative.

| Group | Required foundation |
|---|---|
| System | Certificates, downloads, extraction, compilation, and an appropriate package manager |
| Development | Git, GitHub CLI, a Node.js version manager, Node.js LTS, npm, pnpm, ripgrep, fd, and jq |
| Containers | Docker client, accessible engine, Compose v2 through `docker compose`, and system prerequisites |
| Agents | Codex CLI and Claude Code CLI, with verified initialization and authentication |
| Integrations | RTK, Ponytail `full`, Caveman, Superpowers, Context7, and Graphify in each compatible client |

The preferred Node.js manager is [fnm](https://github.com/Schniz/fnm). The default version should be the [compatible LTS at execution time](https://nodejs.org/en/about/previous-releases), preserving project-specific versions. Check the [pnpm installation method](https://pnpm.io/installation) during execution as well; do not assume every Node.js version includes Corepack.

For [Docker](https://docs.docker.com/get-started/get-docker/), an installed client without an accessible engine remains pending. The choice of Desktop or Engine depends on the system, requirements, and applicable license.

### Extension sources

These references help avoid similarly named packages and unsupported integrations:

| Tool | Source | Integration to verify |
|---|---|---|
| RTK | [rtk-ai/rtk](https://github.com/rtk-ai/rtk) | CLI and native hooks per agent; no double rewriting |
| Ponytail | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | Plugin with hooks or skill, according to client support |
| Caveman | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | Communication skills; proxy and routing features have their own scope |
| Superpowers | [obra/superpowers](https://github.com/obra/superpowers) | Official client plugin or documented skill mechanism |
| Context7 | [upstash/context7](https://github.com/upstash/context7) | Plugin or MCP; one logical server per client |
| Graphify | [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) | `graphifyy` package, `graphify` CLI, and a skill discovered by the agent |

For Caveman, concise communication does not require enabling a proxy, Cloud, or automatic model switching. For LLM work in Caveman and Graphify, preserve the native client, authentication, and model authorized in the session. In Codex, retain ChatGPT login when used; in Claude, retain the current authentication method. Do not infer authorization for another provider from an available tool option.

## 4. Track interventions and resumption

You may need to complete browser login, enter a system password, grant an operating system permission, start Docker Desktop, or restart a session. The agent should identify the exact intervention and continue independent steps.

New extras, costs, and incompatible migrations depend on your choice. Required installations and already authorized global updates remain part of the work.

If the session ends before validation, use:

```text
Resume prompt 10 setup from [report path] and [manifest path].
Check the current state, continue pending work, and revalidate in new sessions.
Preserve existing backups and avoid duplicate installations, configurations, and hooks.
```

A configuration file change does not necessarily change the open session's permissions. CLI, desktop application, operating system, and organization policies need separate checks. See details in the [Codex guide](tools/15-codex-workflow.md).

## 5. Check the delivery

The report should cover every item in section 12 of the prompt, including previous and final versions, paths, sources, integrations per client, cleanup, backups, and restoration. Each test should record the command, result, and session used, with sensitive data removed.

For Docker, look for evidence of section 11's seven steps: client and server in `docker version`, `docker info`, Compose version, `hello-world`, a working temporary project, and cleanup of only test resources. For agents, look for actual skill loading and a Context7 query; presence on disk or in configuration does not prove operation.

The [manifest template](../templates/environment-manifest.json.example) is JSON without an embedded installer. It starts with `template: true`, `null` versions and paths, and `pending` statuses because it does not yet represent a validated environment. When filling it in:

- Use `ready` only after installation, configuration, and validation; use `blocked` or `unsupported` with a reason in `notes` when needed.
- Record the version or revision, observed path, scope, installation method, and update method of each component. Add required dependencies and every global tool discovered.
- Detail integrations in `integrations`: client, scope, file, behavior, and status. If a plugin does not work in one client, record that client separately.
- Record required shell, PATH, runtime, and permission settings in `configuration`. Keep concise evidence without secrets in `validation`.
- Fill `generated_at`, identify the environment, and change `template` to `false`. This identifies a completed inventory without hiding items that remain blocked.
- Keep backup paths and restoration instructions in the local report. In the shareable copy, normalize personal directories as `${USER_HOME}` and remove private names, private repositories, and authentication data.

## 6. Reproduce on another machine

Bring the sanitized manifest with the complete prompt and specify:

```text
Execute prompt 10 on this computer using [manifest path] as the source inventory.
Reproduce the required foundation and other recorded components, adapting the operating system, architecture, shell, paths, and installation methods.
Respect project-required versions and record compatibility differences.
Generate a new report and a new destination manifest. Do not reuse source credentials.
```

Recorded versions are evidence of the source environment. The prompt still requests compatible stable versions at execution time; explicitly state any requirement to retain an exact revision. A manifest does not transport sessions, secrets, Docker data, or tools absent from the inventory.

## Prepare project capabilities

The toolkit has two scopes: this guide configures the **machine**; project recipes configure **individual codebases**. Evaluate the [capability matrix](tools/README.md#select-by-scope) against the intended work:

- For compatible Next.js development, prepare [agent-browser](tools/11-agent-browser.md) and its browser runtime for [next-dev-loop](tools/17-nextjs-runtime-and-performance.md). Check the current skill's version/bundler requirements. The application and its local skills remain project-scoped.
- For GitHub Actions work, prepare the [GitHub CLI and account access](tools/19-github-ci-repair.md). For security review, ensure Git/history and supported agent tools are available.
- PostgreSQL guidance, bundle analysis, and shadcn instructions belong in the project; machine setup does not choose a database host or UI library.
- For a chosen Sentry service, verify client MCP/OAuth support and authorized access. Configure a [scoped connection](tools/22-sentry-mcp.md) at the intended client/project scope; without an account/project, record the capability as not selected or pending.
- The default [Harness2-inspired workflow](tools/23-harness2.md) for new and existing projects reuses the current agent, with no additional machine installation. Only a selected official CLI lab needs Git, uv, and compatible Python in a dedicated environment. Record benchmark-specific dependencies separately; do not enable API billing, a bridge, or weaker client permissions as part of machine setup.

Record every selected prerequisite and per-client integration in the manifest, with source, observed version/revision, scope, update method, and evidence. Optional entries start with `required: false`; do not mark them ready until the relevant checks pass. Do not globally install all project skills as a consequence of this inventory.

## After the foundation

To configure or update an existing project with the applicable components, use [prompt 12](prompts/12-existing-project-setup.md). It reuses the prepared environment and keeps project scope separate from machine setup.

Choose extras by the problem they solve. For browser flow automation, see [agent-browser](tools/11-agent-browser.md); to investigate console, networking, and performance, see [Chrome DevTools MCP](tools/14-chrome-devtools-mcp.md). For project quality, use the [quality gates](tools/06-eslint-biome-quality-gates.md). None of these new extras should be installed automatically merely because they appear as recommendations.
