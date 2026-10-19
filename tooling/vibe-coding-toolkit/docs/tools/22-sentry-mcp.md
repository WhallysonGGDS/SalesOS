# Sentry MCP

Connect an agent to an existing Sentry project to investigate errors and performance with production evidence. This is an optional remote MCP integration, separate from installing an application's Sentry SDK. Use it only when the service is chosen and access is authorized.

## Requirements and configuration

Use an OAuth-capable client and an authorized Sentry account. Prefer the project-scoped endpoint documented by [Sentry](https://mcp.sentry.dev/). Replace the example slugs with the intended organization/project; they are identifiers, not credentials.

For Codex, merge the [optional TOML example](../../templates/project/sentry.codex.config.toml.example) into the project's `.codex/config.toml`. Follow the client's project trust rules. Then authenticate through the supported UI or:

```bash
codex mcp login sentry
```

See [official Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli). Check `codex mcp --help` against the installed client. CLI server-add commands may change user scope; merging the project configuration keeps the destination explicit.

For Claude Code, merge the [optional JSON example](../../templates/project/sentry.mcp.json.example) into `.mcp.json`, or use the supported project-scoped command:

```bash
claude mcp add --scope project --transport http sentry https://mcp.sentry.dev/mcp/example-org/example-project
```

Check current help and approve the project's MCP configuration when the client requests it. Complete OAuth in the browser/client. Store no bearer tokens, cookies, account sessions, or OAuth secrets in versioned files. Reuse an existing equivalent connection instead of adding another logical server.

## Use and validation

```text
Use the project's Sentry connection to investigate the selected issue.
Confirm organization, project, release, and time range, inspect relevant events,
and connect the evidence to this checkout. Propose a fix and a regression check.
```

Validate in stages: parse configuration, confirm discovery, authenticate, enumerate tools, then perform a read-only query against the intended project. Redact event data in reports. Record **configured without execution** or **pending authentication** until live checks succeed; an endpoint or file alone is insufficient.

Issue mutations, external messages, new accounts, SDK installation, paid features, and deployment need their own task authorization. Project scoping narrows the tool context; inspect account permissions and returned project data rather than treating a URL as an authorization boundary.

## Maintenance

The hosted service updates independently of the repository. Review current Sentry/client documentation, OAuth permissions, endpoint scope, and available tools when adopting or troubleshooting it. Revalidate a read-only query after meaningful changes and record client version, sanitized endpoint scope, evidence, and pending access in the machine inventory or `docs/setup.md`.
