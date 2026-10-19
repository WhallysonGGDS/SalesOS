# Installation

Quick reference for installing agents and toolkit components. To **prepare or update the entire computer**, use the [setup guide](03-environment-setup.md) and [prompt 10](prompts/10-development-environment-setup.md): they include system prerequisites, Node.js, Docker, all required integrations, backups, and validation.

To **configure or update an existing project**, use [prompt 12](prompts/12-existing-project-setup.md): diagnosis, brainstorming, a harness, and integration of all applicable toolkit components, preserving the stack and customizations.

Commands checked on **October 14, 2026**. Confirm the documentation for your version and operating system. Choose one method per tool and preserve existing installations where supported.

## 1. Codex and Claude Code

Both agents offer native installers that do not require Node.js beforehand. On macOS, Linux, or WSL, choose the command for the agent you want to install:

```bash
# Codex
curl -fsSL https://chatgpt.com/codex/install.sh | sh

# Claude Code
curl -fsSL https://claude.ai/install.sh | bash
```

On native Windows, follow the PowerShell instructions on the official pages. For Homebrew or an existing npm installation, check supported methods before migrating. Sources: [Codex CLI](https://learn.chatgpt.com/docs/codex/cli) and [Claude Code](https://code.claude.com/docs/en/setup).

Then, in a new terminal:

```bash
codex --version
claude --version
```

Open `codex` or `claude` and complete authentication through the official flow. The setup prompt prefers ChatGPT login for Codex. Credentials never belong in chat or project files.

`claude doctor` helps check Claude Code installation and updates. Update each CLI through its installation method; for example, a Homebrew installation requires Homebrew updates, while Claude's native installer manages its own updates.

## 2. Plugins and standalone CLIs

### Claude Code: commands inside the session

`/plugin` is a Claude Code command, **not a shell command**. Open `claude` before using it:

```text
/plugin marketplace add anthropics/claude-plugins-official
/plugin install superpowers@claude-plugins-official

/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail

/plugin marketplace add JuliusBrussee/caveman
/plugin install caveman@caveman
```

Sources: [Superpowers](https://github.com/obra/superpowers#claude-code), [Ponytail](https://github.com/DietrichGebert/ponytail#install), and [Caveman](https://github.com/JuliusBrussee/caveman). Verify loading in a new conversation; an installed directory does not prove activation.

### Codex: its own plugins

For Superpowers, open `/plugins` in the session and install the official distribution. For Ponytail, the documented terminal commands are:

```bash
codex plugin marketplace add DietrichGebert/ponytail
codex plugin add ponytail@ponytail
```

Check hooks through the client's workflow and open a new conversation. For Caveman, use the documented skills distribution and Codex discovery, retaining concise communication without enabling a proxy or model routing. See the [Codex guide](tools/15-codex-workflow.md) for paths, commands, and instruction precedence.

### RTK, Context7, and Graphify

| Tool | Installation or connection | Integration |
|---|---|---|
| [RTK](tools/03-rtk-token-proxy.md) | With Homebrew: `brew install rtk-ai/tap/rtk`; other systems follow official releases | Claude: `rtk init --global`; Codex: `rtk init --global --codex` |
| [Context7](tools/12-context7.md) | Client plugin or remote MCP at `https://mcp.context7.com/mcp` | Configure each client and run a real query; avoid duplicate servers |
| [Graphify](tools/07-graphify.md) | `uv tool install graphifyy` **or** `pipx install graphifyy` | `graphify install`, then verify skill discovery in the agent |

Graphify requires Python and a compatible installation mechanism; configure these prerequisites if missing. The package is `graphifyy`, with two “y” characters; the CLI is `graphify`. Choose one isolated method, rather than installing both. RTK and Graphify are CLIs; they are not npm packages with the same names.

Remote Context7 is a service, not a local package to update. The plugin may already include the MCP server and query skill. Installing a second connection for the same purpose creates overlap.

### Project workflow extras

With the modular toolkit, you can choose components. In **prompt 10**, RTK, Ponytail, Caveman, Superpowers, Context7, and Graphify are required. The following remain new extras subject to your choice:

| Tool | Reference | Use |
|---|---|---|
| agent-browser | [Guide](tools/11-agent-browser.md) | Automate browser flows |
| Chrome DevTools MCP | [Guide](tools/14-chrome-devtools-mcp.md) | Investigate networking, console, and performance |
| Anthropic Skills | [Guide](tools/13-anthropics-skills.md) | Work with artifacts and create skills |
| aia-harness | [Marketplace](https://github.com/leandrosilvaferreira/claude-plugins-registry) | Project onboarding; confirm options and support in the marketplace itself |
| Official Claude plugins | [Marketplace](https://github.com/anthropics/claude-plugins-official) | Choose review, commit, or hook tools as needed |

## 3. Local Vercel skills

For Next.js/React, follow the [Vercel catalog](tools/16-vercel-skills.md) and discover current official sources. Use local installation, actual frontmatter names, and only the clients you need. React Native/Expo is an optional extension.

Evaluate the [capability matrix](tools/README.md#select-by-scope) for both machine preparation and individual projects: [Next.js runtime/bundle skills](tools/17-nextjs-runtime-and-performance.md), [PostgreSQL](tools/18-postgresql-skills.md), [GitHub CI repair](tools/19-github-ci-repair.md), [security review](tools/20-security-review.md), [shadcn](tools/21-shadcn-ui.md), and [Sentry MCP](tools/22-sentry-mcp.md). Each guide covers prerequisites, installation, use, verification, and updates. Install applicable instructions locally; account-dependent workflows stay pending until authorized access exists.

To generate the product definition, official foundation, and configurations together, use the [Next.js bootstrap](04-project-bootstrap.md) and [prompt 11](prompts/11-next-project-bootstrap.md). Do not reinstall global plugins for every project.

<a id="3-project-instructions"></a>

## 4. Project instructions

Use [AGENTS.md.template](../templates/AGENTS.md.template) for shared instructions and [CLAUDE.md.template](../templates/CLAUDE.md.template) as the Claude client's bridge to `AGENTS.md`. Fill in commands and conventions in the shared file; merge with existing files without overwriting them.

[settings.json.example](../templates/settings.json.example) shows the custom hook format. Referenced scripts are examples: register only hooks whose files exist and whose behavior has been verified. RTK and plugins should use their official installation without duplicate interceptors.

## Need the complete walkthrough?

- [Machine setup](03-environment-setup.md): execution, resumption, reporting, and reproduction.
- [Existing-project setup](prompts/12-existing-project-setup.md): complete adoption, updates, and validation.
- [Claude Code playbook](02-playbook-onboarding.md): a narrated project workflow.
- [Codex workflow](tools/15-codex-workflow.md): instructions, skills, MCP, and permissions.
