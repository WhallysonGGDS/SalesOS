# RTK — CLI token proxy

RTK stands for **Rust Token Killer**. It is a public tool at [rtk-ai/rtk](https://github.com/rtk-ai/rtk), distributed as a command-line binary. It runs supported commands and filters their output before the agent receives it, reducing repetitive text in the context window.

A **hook** is an integration that runs before or after an agent action. In RTK, the hook can rewrite the proposed command to use the binary. This lets you use ordinary commands without relying on the model to remember the prefix on every call.

This page replaces the old custom proxy example. Prefer the official integration: it understands each client's formats and avoids maintaining your own shell parser and hook. See [hook best practices](10-hooks-best-practices.md) when you need an additional integration.

## Install using the official method

With Homebrew available, the [installation documentation](https://github.com/rtk-ai/rtk/blob/develop/docs/guide/getting-started/installation.md) specifies:

```bash
brew install rtk-ai/tap/rtk
rtk --version
```

On other environments, use the installer or release binary the project specifies for your system and architecture. Confirm the source before installing: a package named `rtk` in another ecosystem may be a different tool.

If RTK is already installed, identify its path, version, and managing package manager before updating. For an installation from the tap above, use `brew upgrade rtk-ai/tap/rtk`. Do not install another copy just to change methods.

## Configure each agent

Back up existing settings before initializing the integration. The [official list of supported agents](https://github.com/rtk-ai/rtk/blob/develop/docs/guide/getting-started/supported-agents.md) distinguishes each client's mechanisms.

### Claude Code

```bash
rtk init --global
rtk init --show
```

This workflow installs the hook and updates the Claude Code configuration. Open a new session and check its registration. If a custom proxy hook already serves the same purpose, remove or reconcile only the redundant integration after confirming its references.

### Codex CLI

```bash
rtk init --global --codex
```

The current mechanism registers Codex's native `PreToolUse` hook. The `rtk hook codex` handler returns the rewritten command through `updatedInput`; Codex runs the command and applies its own permissions. The hook does not need to run a copy of the command beforehand.

Alternatively, `rtk init --codex` installs it in the current project. Choose the scope you need: do not register the same hook globally and in the project without checking the combined effect. For machine setup, prefer global scope to preserve projects.

Restart Codex and complete hook trust when the client prompts you. Check `rtk init --help` and your installed version's documentation if the option does not exist. CLI support does not prove that every desktop or remote surface runs the same hook.

## Use supported commands or full output

Without an active hook, prefix supported commands explicitly:

```bash
rtk git status
rtk git diff
rtk git log -5 --oneline
```

With a native hook active, propose ordinary commands and let the integration rewrite them. Do not add a second wrapper or another rewrite hook.

To preserve the entire output or use a command without a dedicated filter, use `rtk proxy`:

```bash
rtk proxy git diff
rtk proxy git log -5 --oneline
```

This is the escape hatch when a summary omits a detail needed for diagnosis. Do not use condensed output as proof that a line, warning, or file does not exist without checking the full data when the decision depends on it.

Do not blindly prefix pipelines, redirections, heredocs, or compound commands. Syntax support varies; preserve shell semantics and check `rtk --help` for available commands.

## Measure and validate

```bash
rtk gain
rtk gain --history
```

The metrics show usage history observed by RTK. They describe reduced command output, not total session tokens, guaranteed subscription savings, or the cost of all model work. Calls through `rtk proxy` preserve output and may appear without a reduction.

To test the integration:

1. Open a new terminal and agent session.
2. Confirm `rtk --version` and the executable path resolved by the shell.
3. Request `git status` in a known repository and check that the call was rewritten once.
4. Check the entry in `rtk gain --history`.
5. Run `rtk proxy git status` and check the full output.

If the history shows no usage, investigate binary discovery, hook scope, trust, and surface support. Installation on disk does not prove an active integration.

## Important pitfalls

- **Duplicate hooks:** two interceptors can apply wrappers twice or repeat work. Inventory global and project settings before consolidating.
- **Incomplete output:** filters help with routine reading; diagnosis, unusual flags, and exact checks may require `rtk proxy`.
- **Permissions:** compressing output does not authorize installing, publishing, deleting, or accessing a resource. The agent and system remain responsible for permissions.
- **Command errors:** preserve exit codes and enough evidence of failure. An apparently normal summary does not turn a failed run into success.
- **Updates:** update the binary through its managing package manager and check the release's integration instructions. Preserve custom hooks serving other purposes.

## Frequently asked questions

**Do I need to build my own proxy?**
No. Install the public RTK tool and use the mechanism documented for your agent. A custom hook is justified only by a need the official integration does not cover.

**Does it work without a hook?**
Yes. Use the explicit prefix on supported commands and `rtk proxy` when you need full output.

**Does installing it for Claude configure Codex?**
No. Configure and validate the two clients separately.

**Does this change my model or provider?**
The CLI and hook workflow described here filters command output. It does not require changing the agent's model, authentication, or provider.

**How does it fit into the full setup?**
RTK is required by the [environment prompt](../prompts/10-development-environment-setup.md). The agent must install, integrate, and validate it without duplicating wrappers or hooks.
