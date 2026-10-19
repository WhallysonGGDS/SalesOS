<a id="what-it-is"></a>
<a id="why-use-it"></a>

# Graphify

[Graphify](https://github.com/Graphify-Labs/graphify) turns code and documents into a queryable graph. The CLI is `graphify`; the Python package is **`graphifyy`**, with two “y” characters. It combines structural extraction, semantic relationships, and exports for project investigation.

<a id="how-to-install"></a>
<a id="1-install"></a>

## Global and project scope

The CLI and agent skill belong to the environment/client. The project maintains `.graphifyignore` and the `graphify-out/` output. In the [Next bootstrap](../04-project-bootstrap.md), working global installations are reused; do not copy skills from a personal cache or install Git hooks.

Isolated package installation, when requested:

```bash
uv tool install graphifyy
# Alternative: pipx install graphifyy
```

Choose one method. Check the CLI before integrating:

```bash
GRAPHIFY_NO_AUTO_REFRESH=1 graphify --version
GRAPHIFY_NO_AUTO_REFRESH=1 graphify --help
```

The upstream project documents `graphify install` for client integration. Check your installed version's flags and effects before running it: installations may modify instructions and hooks. In the starter, prefer the already discovered global integration and concise shared instructions. Do not use an automatic installation to replace local adaptations or add restrictions.

<a id="step-by-step-tutorial"></a>
<a id="2-run-the-full-pipeline"></a>
<a id="3-inspect-the-output"></a>

## Code without a model call

For an application's initial graph:

```bash
GRAPHIFY_NO_AUTO_REFRESH=1 graphify extract . --code-only --no-cluster
```

This mode restricts extraction to code and avoids the clustering stage. Check the expected files in `graphify-out/graph.json`; it does not automatically cover requirements from `PRODUCT.md` or semantic relationships in documents.

Copy and adapt [the exclusions](../../templates/project/.graphifyignore.example). Exclude credentials, `.env*`, dependencies, vendored skills, caches, and the graph's own output. Ignore `graphify-out/` in Git by default; deliberately shared exports require content review.

`GRAPHIFY_NO_AUTO_REFRESH=1` prevents the integration's automatic refresh. Use it when local adaptations need to be preserved. Check support in the installed version.

<a id="codex-model-and-authentication"></a>

## Documents and semantic extraction

Use the skill discovered by the client, such as `$graphify` in Codex or the equivalent invocation documented for another agent. Preserve the **authorized native client, main model, and authentication**. Without an authorized selection policy, pass the session model in supported delegation; with such a policy, follow [selection by task and risk](02-subagent-orchestration.md#part-b--model-selection-discipline), respecting explicit model restrictions.

In Codex, preserve ChatGPT login when used; in Claude, preserve the current authentication mode. Do not activate an API backend, proxy, or another model as a side effect of setup. The `graphify extract` CLI alone **does not automatically inherit conversation authentication**. A `--backend openai` option is not equivalent to ChatGPT login.

If no compatible native semantic integration exists, record the limitation and continue with deterministic extraction. Do not invent support for an LLM merely because it can run the CLI.

<a id="main-commands"></a>
<a id="4-ask-the-graph-a-question"></a>
<a id="5-explore-a-specific-concept"></a>
<a id="examples"></a>
<a id="example-1--graphify-explain-inspecting-a-specific-node"></a>
<a id="example-2--graphify-path-the-relationship-between-two-concepts"></a>
<a id="example-3--incremental-update-after-editing-code"></a>
<a id="automation-with-git-hooks"></a>
<a id="orientation-hook"></a>

## Query and maintain

With an existing, relevant graph:

```bash
GRAPHIFY_NO_AUTO_REFRESH=1 graphify query 'What depends on this module?'
GRAPHIFY_NO_AUTO_REFRESH=1 graphify path 'AuthModule' 'Database'
GRAPHIFY_NO_AUTO_REFRESH=1 graphify explain 'AuthModule'
```

Replace the names with real nodes. Extracted, inferred, and ambiguous relationships do not carry the same evidentiary weight. Confirm important findings in the code; record whether the graph is outdated or does not include the necessary part.

After changing code, check the installed version's deterministic extraction/update modes. For a code-only graph, repeating the command with `--code-only --no-cluster` keeps the scope explicit. An update without flags does not guarantee that new documents will avoid triggering semantic extraction.

The CLI offers exports including HTML, wiki, Obsidian, SVG, GraphML, and graph database formats. Check `graphify --help`; exporting a file and sending data to a service are separate actions. Do not send the graph to an external database or platform during bootstrap.

<a id="tips-and-pitfalls"></a>
<a id="frequently-asked-questions"></a>

## Validate

- Check the version and actual executable.
- Check skill discovery in every client used; a directory's presence does not prove loading.
- Generate a small corpus without an external LLM and check nodes/files in the output.
- Test a query against the generated graph.
- Record scope, evidence, limitations, and required updates in `docs/setup.md`.

References: [official project](https://github.com/Graphify-Labs/graphify), [Codex guide](15-codex-workflow.md), [machine setup](../03-environment-setup.md), and [bootstrap](../04-project-bootstrap.md). The CLI evolves; check flags in the running version instead of copying commands from another installation.
