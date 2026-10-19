# Onboarding Playbook

> If the [README](../README.md) is the menu and the [Overview](00-overview.md)
> explains why, this is the walkthrough: take any project from scratch and
> assemble the entire workflow in the right order, becoming fluent with
> each tool along the way.

## Who this playbook is for

For experienced developers who want a structured way to use AI in
production while retaining quality control, and beginners who simply want
to follow a proven path. This playbook assumes no prior Claude Code
experience: Part 1 starts with installation. It does not force anyone to
backtrack, either: if something already works in your environment, skip to
the missing part.

## How to use this playbook

To configure or update the applicable toolkit in an existing project, use [prompt 12](prompts/12-existing-project-setup.md). It guides diagnosis, brainstorming, harness setup, implementation, and validation; this playbook remains the narrated Claude workflow reference.

To create a new Next application from a product description, prefer the [bootstrap](04-project-bootstrap.md). This playbook is an adoption and manual configuration reference for Claude. Optional plugins and hooks are not mandatory starter components.

This guide covers the **in-project workflow**, primarily in Claude Code. To prepare or update the machine, start with [environment setup](03-environment-setup.md). For Codex, see the [client guide](tools/15-codex-workflow.md) and [shared `AGENTS.md` template](../templates/AGENTS.md.template).

Two equally valid approaches:

- **Start to finish the first time.** Each part assumes the previous one
  is complete. Part 4, the complete workflow, only makes full sense after
  the Part 2 pillars are installed and Part 3's `CLAUDE.md` is filled in.
- **As a reference afterward.** Once setup is running, return directly to
  the part you need. “What was the multi-agent review prompt?” calls for
  Part 4 rather than rereading the whole playbook.

## Execution continuity

These agreements help carry out already-authorized work in Claude, Codex, or another tool-enabled host. They are work instructions; they do not guarantee runtime persistence or create an automatic continuation hook.

- **Status during work:** answer briefly and continue remaining actions. A question such as “how is it going?” does not cancel the task. Explicit pauses, cancellations, or objective changes alter execution; without active work, a purely informational request ends with its answer.
- **Partial blockage:** identify tasks depending on the blocked action and complete independent work that remains safe and authorized. Do not bypass denials or gates. Before ending, check whether any action within scope remains executable.
- **Failed or uncertain worker:** use the host's mechanism to confirm it stopped before taking over or redistributing its files. An unconfirmed interruption request does not release write ownership. Inspect the partial diff and checks, resume from the verified point, and keep one writer per file.
- **Retries and limits:** retry only with new evidence, such as an identified cause or fixed dependency. Respect attempt, time, and cost limits. Without a safe alternative, end with the blocker, completed work, and requirements for resuming; do not invent progress to keep the turn active.
- **Resuming:** a handoff provides context, not proof of checkout state. Check actual files, Git state, results, and processes before editing, preserving local changes.
- **Background execution:** claim work continues only when an active process, agent, or automation can be verified. A conversational promise does not start work after the turn ends.

The [shared AGENTS template](../templates/AGENTS.md.template) contains a ready-to-adapt block. In existing projects, incorporate it into loaded instructions; `CLAUDE.md` can import `AGENTS.md` without duplicating policies. Continue respecting current permissions and decisions: consulting prior authorization avoids repeated approvals but does not create new authorization.

### Evaluation outline

In a disposable project without external services, check these scenarios. The [harness evaluation guide](07-harness-evaluation.md) supplies runnable authorization checks, a reusable prompt, and a result protocol. The [validation record](05-toolkit-validation.md) identifies executed cases; this outline is not evidence that every interaction passed across all hosts.

| Scenario | Expected result |
|---|---|
| Status question between two authorized changes | Brief answer; second change completed and verified before ending |
| Worker fails or its state is uncertain | No takeover before confirmed stop; partial diff inspected |
| One blocked action and one independent action | Complete the independent action without bypassing the blocker |
| Repeated failure without new evidence or a safe alternative | End with diagnosis and resumption conditions, without identical retries |
| Pause, cancellation, or budget limit | Respect the limit and report actual state |
| Purely informational question without active execution | Answer and end without starting additional work |
| Handoff differs from actual files | Check real state before editing |

## Prerequisites

Before opening the terminal, check that you have:

- **The runtime required by the project.** For Node.js projects, check `node --version` and respect `.node-version`, `.nvmrc`, and `engines`. Claude Code's native installer does not require Node.js beforehand.
- **A terminal.** macOS, Linux, or Windows (native or WSL): everything in
  this playbook runs from the command line.
- **`gh` CLI (optional).** Needed only for the GitHub workflows (pull
  requests, issues) mentioned along the way. Install from the [official
  website](https://cli.github.com) if needed.
- **An account that authenticates Claude Code**: a Pro or Max plan, or
  Anthropic API/console access. Without one, the `claude` CLI installs but
  cannot log in.

## Part 1 — Foundation: install Claude Code and understand the philosophy

### Install Claude Code

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

This is the native installer for macOS, Linux, and WSL. For native Windows and alternative methods, use the [official documentation](https://code.claude.com/docs/en/setup). If a working installation exists, preserve its method when supported instead of adding another copy.

Confirm installation succeeded and the executable is in your `PATH`:

```bash
claude --version
```

If the command is not found, open a new terminal and check the PATH shown by the installer. Use `claude doctor` and the [installation documentation](https://code.claude.com/docs/en/setup) to diagnose integration.

### The philosophy in one paragraph

This is a workflow, rather than a collection of unrelated tools. The main
Claude Code session plans, decides, and implements. It delegates to specialist
**subagents** when context isolation, expertise, or independent tasks justify
the coordination. Each subagent receives a specific task and its own context;
parallel execution requires independent tasks and distinct writable files.
Scale the process to the request: brainstorm to explore intent, plan when
needed, implement, verify, then review.
A token-saving layer keeps long sessions affordable; two combined behavior
modes control what gets built and how the agent describes it; quality
gates progress from warnings to errors through tracked migration instead
of sudden blocking; and a two-layer memory system preserves expensive
lessons across sessions. No individual piece is impressive on its own:
the strength comes from using them together. For a fuller explanation
before continuing, read the [Overview](00-overview.md). The rest of this
playbook assumes you understand the reasoning.

## Part 2 — Essential pillars in order of importance

Three plugins form this workflow's backbone. The order is based on actual
importance, rather than alphabetical: **Superpowers comes first because
everything else here revolves around it.** The other two work independently,
but without Superpowers you lose the process discipline (brainstorm →
plan → implementation → review) that makes the rest of the workflow,
including all of Part 4, meaningful.

### Superpowers — the most important pillar

Superpowers is a Claude Code plugin bundling **process skills**: named,
reusable workflows for software development stages, including exploring
intent, planning, implementing, debugging, reviewing, and finishing a
branch. Unlike implementation skills teaching a specific technology,
process skills operate **above** them: they determine when and how to
approach a task before domain skills determine what to write.

**Install:**

```bash
/plugin marketplace add anthropics/claude-plugins-official
/plugin install superpowers@claude-plugins-official
```

These are not terminal commands: paste them directly into the Claude Code
prompt in an open session. Typing `/plugin install ...` there already asks
the agent to install the plugin. Claude Code itself interprets and runs
the commands, without a separate terminal.

**See it work:** request something deliberately open-ended, with multiple
reasonable interpretations, rather than a typo correction. For example:

```
Add a way to export reports from our API.
```

Without Superpowers, an agent would choose format, filters, and
authentication independently and probably get at least one wrong. With
Superpowers active, its central rule applies:

> If a skill could apply, even slightly, invoke it **before responding
> with anything**, including a clarifying question.

In practice, instead of immediately writing code or merely asking “which
format?”, Claude Code first invokes `brainstorming`. Clarifying questions
happen within that skill: which fields belong in the report, who can
export, whether a date-range limit exists. If a clearly ambiguous request
goes straight to code, the plugin is inactive; run `/plugin list` to
confirm installation.

Learn more: [Superpowers](tools/01-superpowers.md).

### Ponytail — what gets built

Ponytail is an engineering discipline persona: a “lazy senior engineer,”
lazy in the efficient sense rather than careless. Installed as a plugin,
it follows a fixed decision ladder before writing code and stops at the
first step that solves the problem. It addresses a coding agent's default
tendency to build more than the task requires.

The ladder, from top to bottom: does this need to exist? Is something
similar already in the project? Does the language's standard library
solve it? Does a native platform feature solve it? An installed dependency?
Can it fit in one line? Only then, write the minimum new code that works.

**Install:**

```bash
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
```

The same reminder as for Superpowers: run this inside the Claude Code
session, not a separate terminal. Typing `/plugin install` is itself the
installation request.

**See it work:** request something inviting overengineering. For example:

```
Add caching for responses from this external API.
```

Without Ponytail, an agent might propose a cache class with configurable
TTL, manual invalidation, and an interface for swapping storage later:
unrequested and speculative. With Ponytail, the answer tends toward the
language/framework's existing in-memory cache (`@lru_cache` or equivalent)
and a single line naming what was skipped: *“Added
`@lru_cache(maxsize=1000)` to the function; skipped a custom cache class,
add one when `lru_cache` actually becomes insufficient.”* Code first,
followed by at most three lines explaining what was skipped and when to
add it: the signature of the active plugin.

Learn more: [Ponytail](tools/04-ponytail.md).

### Caveman — how the agent talks about it

Independent of Ponytail's control over what gets built, Caveman compresses
communication: it removes filler such as “I'll go ahead and...”, “great
question!”, and “this could potentially...” without removing information.
Numbers, units, code, and exact error messages remain intact. Negations
such as “not,” “never,” and “except” are never cut because their removal
changes meaning.

**Install:**

```bash
/plugin marketplace add JuliusBrussee/caveman
/plugin install caveman@caveman
```

Again, paste inside the Claude Code session rather than a separate
terminal: `/plugin install` alone is the installation request.

**See it work:** ask a normal development question and compare the answer's
tone before and after installation, or simply run:

```
/caveman-stats
```

to view observed session counters when available. Token usage does not prove savings caused by Caveman; see the [measurement limitations](tools/05-caveman.md#6-measure-usage-without-inventing-savings). If answers still start with “I'll check that for you!” and introductory paragraphs before any facts, the plugin has not taken effect; check with `/plugin list`.

Learn more: [Caveman](tools/05-caveman.md).

---

The complete [Installation guide](01-installation.md) lists other useful
optional plugins: `aia-harness`, `ui-ux-pro-max`, `hookify`,
`pr-review-toolkit`, `commit-commands`, `claude-code-setup`, `feature-dev`,
`code-review`, and `claude-md-management`. The three above are the
foundation. Do not continue without them.

## Part 3 — Configuring your project from scratch

With the three pillars installed, move from generic Claude Code to Claude
Code that knows your project. This means two files: `CLAUDE.md` at the
project root and `.claude/settings.json`.

**A shortcut when speed is the priority:** steps 1–4 below are the manual
path for understanding each piece and controlling what enters each file.
For faster setup, `aia-harness` (source:
`leandrosilvaferreira/claude-plugins-registry`, listed in the
[Installation guide](01-installation.md) source table) provides a command
that scans the project and builds much of this structure automatically:
specialist agents, rules, hooks, memory, and `settings.json`:

```bash
/plugin marketplace add leandrosilvaferreira/claude-plugins-registry
/plugin install aia-harness@leandro-plugins-registry
/aia-harness:init
```

Like Part 2's plugins, these commands run inside Claude Code rather than
a separate terminal. After `/aia-harness:init`, use the rest of this
playbook to understand what was generated and why, instead of building
every file from scratch.

<a id="1-copy-and-fill-in-claudemd"></a>

### 1. Fill in `AGENTS.md` and create the Claude bridge

Use templates from the local toolkit copy. In the target project:

```bash
cp -n /path/to/toolkit/templates/AGENTS.md.template AGENTS.md
cp -n /path/to/toolkit/templates/CLAUDE.md.template CLAUDE.md
```

Replace `/path/to/toolkit` with the actual path. In a POSIX shell, `-n` preserves an existing destination; use an equivalent mechanism elsewhere. If instructions already exist, read them and incorporate only desired sections.

Fill in the name, stack, commands, context, and conventions in `AGENTS.md`. The Claude template imports it with `@AGENTS.md`, using the [official memory syntax](https://code.claude.com/docs/en/memory). Preserve framework-generated instructions in both files as well.

The shared template neither installs a roster of agents nor requires delegation for every task. Add only relevant roles actually supported by the client, as described in [orchestration](tools/02-subagent-orchestration.md). Product and behavior instructions have one source; client specifics belong in their corresponding file/configuration.

### 2. Copy and adjust `.claude/settings.json`

```bash
mkdir -p .claude
cp -n /path/to/toolkit/templates/settings.json.example .claude/settings.json
```

If configuration already exists, back it up and incorporate only necessary hooks. The example is not a ready-to-run setup: do not activate hooks whose scripts do not exist yet.

The example registers two **hooks**, scripts running automatically at
specific session points (before or after a tool, or at session start/end):
a Bash `PreToolUse` hook and a `SessionStart` hook. The names
`example-command-proxy.mjs` and `example-session-banner.mjs` are deliberate
placeholders: write the actual `.mjs` files following the fail-open
discipline (never blocking the entire session because of a hook bug) in
[Hook best practices](tools/10-hooks-best-practices.md).

For command compression, prefer [official RTK](tools/03-rtk-token-proxy.md), which installs its own integration. Do not register the example proxy for the same purpose. The safe stdin reader remains available in [`templates/hooks/hook-io.mjs.example`](../templates/hooks/hook-io.mjs.example) for custom hooks.

Never store API keys in versioned `settings.json`. Use the component's documented credential or environment mechanism. Not every client automatically loads `.env`, and `${VARIABLE}` does not guarantee expansion outside fields supporting it.

### 3. (Recommended) copy the parallel-wave rule

If you plan to use Part 4's parallel-wave execution pattern, recommended
for speed without unnecessary risk, copy the ready-made rule into your
rules directory:

```bash
mkdir -p .claude/rules
cp /path/to/toolkit/templates/rules/parallel-subagent-driven-development.md .claude/rules/
```

Reference it from `CLAUDE.md`; one line is enough, like any other rule.
It exists because Superpowers' default skill for this stage,
`subagent-driven-development`, dispatches one implementer at a time for
safety. This rule documents the exact conditions under which parallel
dispatch remains safe with the same underlying contract.

### 4. Memory — decide now or later

While working in `.claude/`, this is a natural time to decide whether you
want lightweight memory: an always-loaded index without external
dependencies. It can also wait until repeating lessons in new sessions
becomes painful. Part 6 covers both lightweight memory and Obsidian in
depth; the dedicated lightweight guide is [Claude memory
system](tools/09-claude-memory-system.md).

## Part 4 — Your first complete end-to-end workflow

This is the playbook's most important part. Everything else sets the stage;
this runs the entire show. We will use a fictional scenario generic enough
to serve as a template for any project:

> An order-management SaaS has a production REST API. The operations team
> requested downloadable order reports in **CSV**, a comma-separated text
> format universally supported by spreadsheets, filtered by date range.

The original request is deliberately vague, because real requests arrive
that way. The complete workflow has five stages:

```
brainstorm  →  plan  →  parallel-wave implementation  →  multi-agent review  →  commit
```

### 1. Brainstorm — unpack the ambiguous request

```
Before writing any code: I need a way to export order reports
as CSV from our API.

Do not start implementation. First:
- Ask what is missing to finalize scope.
- Tell me whether multiple reasonable interpretations exist, rather than
  silently choosing one.
- Identify assumptions I probably have but did not state: existing
  project patterns, things that must remain untouched, and performance
  requirements.
```

This directly adapts [Brainstorm to plan](prompts/04-brainstorm-to-plan.md).
Even without copying a prompt, Superpowers from Part 2 pushes Claude Code
in this direction: `brainstorming` runs before any answer to creative or
ambiguous requests like this (see [Superpowers](tools/01-superpowers.md)).

In a real session, expect questions such as:

- Who can export: any authenticated user or only a specific role?
- Which fields belong in the CSV: order ID, customer, amount, status, date?
- Is the date range mandatory? Is there a cap: 30 days, 90 days, unlimited?
  This matters to avoid freezing the server while generating five years
  of reports at once.
- Is the file returned immediately (synchronous response), or does the
  project already have an asynchronous job pattern for large reports?
- What exact format: separator, encoding, first row as header?

Answer these questions, or let the agent choose the most conservative
approach where you have no strong preference, before proceeding.

### 2. Plan — turn clarified intent into verifiable steps

Once scope is settled, request a plan:

```
Final scope: authenticated GET /api/reports/orders/export, requiring
`from` and `to` query params, a 90-day limit per request,
CSV with headers (id, customer, amount, status, date), and a streaming
response.

Write a step-by-step implementation plan. Every step needs explicit
verification: a command, test, or observable behavior, never “should work.”
Split steps without clear verification into smaller ones.
```

This triggers Superpowers' `writing-plans`. A reasonable plan resembles
the following; **endpoint** means a specific API route identified by its
URL and HTTP verb:

1. Create the endpoint and validate `from`/`to`, rejecting ranges over 90
   days. Verification: unit tests for valid, oversized, and missing ranges.
2. Implement database querying with pagination/streaming. Verification:
   an integration test with many rows does not exhaust memory.
3. Format the response as CSV with headers. Verification: a test compares
   the header and sample row byte for byte.
4. Authorization: only permitted roles export. Verification: an integration
   test confirms 403 for an unauthorized user.
5. Update API documentation, or a contract test if one exists. Verification:
   documentation/contract reflects the new endpoint.

Every plan step includes `Files:` (files it touches) and `Depends-on:`
(steps that must already exist). These are exactly the fields the next
stage uses to decide what can run in parallel.

### 3. Implementation — subagent-driven-development in parallel waves

With annotated plan steps, execution becomes a sequence of **waves**:
groups of tasks running together because they share neither files nor
dependencies. The complete mechanism is in [Subagent
orchestration](tools/02-subagent-orchestration.md); here is the short version
for this scenario:

| Task | Description | `Files:` | `Depends-on:` | Specialist |
|---|---|---|---|---|
| T01 | Endpoint and export logic | `app/api/reports/orders/export/route.ts`, `server/reports/export-orders.ts` | none | `backend-specialist` |
| T02 | CSV formatting and date-range validation tests | `server/reports/export-orders.test.ts` | none | `test-engineer` |
| T03 | Database index for date-range queries | `db/schema/orders.ts` + migration | none | `database-architect` |
| T04 | “Download CSV” button on the dashboard | `components/reports-panel.tsx` | **T01** | `frontend-specialist` |
| T05 | Update API documentation/contract | `docs/api/reports.md` | **T01** | `documentation-writer` |

T01, T02, and T03 are independent and share no files, so they launch together
in **Wave 1**. T04 and T05 depend on T01's contract, the actual endpoint URL
and parameters, so they wait for Wave 1 and form **Wave 2**. Even without
file conflicts between them, dependency alone requires this delay.

A real Wave 1 dispatch prompt, adapted from [Parallel wave
dispatch](prompts/05-parallel-wave-dispatch.md):

```
Execute Wave 1 of the plan above: T01, T02, and T03, dispatched together
in the same message, one specialist per task. No implementer commits:
each implements, tests their own work, and reports exactly which files
changed. I, as orchestrator, commit afterward, one task at a time,
in T01 → T02 → T03 order, capturing the current HEAD immediately before
each commit.
```

After Wave 1 is implemented and committed, Wave 2 (T04, T05) proceeds the
same way, now with T01's actual contract available to both specialists.

### 4. Review — a multi-agent panel before completion

Before any wave is considered ready, it undergoes review, never a
self-assessment by its implementer. A real prompt, adapted from
[Multi-agent code review](prompts/03-multi-agent-code-review.md):

```
Review the Wave 1 diff (T01, T02, T03) with independent reviewers in
parallel, in one batch: code-reviewer, security-reviewer,
typescript-reviewer, and database-architect for the new index.
No reviewer sees the others' findings. Once all report, synthesize:
merge duplicates, discard findings without a concrete failure scenario,
and rank by severity: CRITICAL, HIGH, MEDIUM, LOW.
```

For a new export endpoint, plausible findings include a `security-reviewer`
catching authorization enforced only on the frontend, a
`typescript-reviewer` finding an overly broad type in CSV formatting, or a
`code-reviewer` noticing plan step 4 lacks a 403 test. Every finding uses
`file:line — severity — claim — exact failure scenario`. Nothing survives
synthesis without that last field.

Fix CRITICAL/HIGH findings before proceeding; MEDIUM/LOW remain discretionary.

### 5. Commit — one per task, in order

The orchestrator, you in the main session, commits rather than the
implementing subagent. One commit per task, in wave order, capturing HEAD
at that moment:

```
Wave 1 passed both reviews. Commit T01, T02, and T03 in order, one
Conventional Commits message per task, capturing the current HEAD
immediately before each commit.
```

The expected result is a sequence of small, traceable commits rather than
one enormous commit mixing three tasks:

```
feat: add CSV export endpoint for order reports
test: cover CSV formatting and date-range validation
perf: add index for order export date-range query
```

Repeat the five-step cycle for Wave 2, taking the original vague request,
“add a way to export reports,” to production without skipping stages.

## Part 5 — Continuous quality

Once Part 4 becomes routine, the next question is how to enforce quality
without blocking the team. This toolkit runs two **linters**, tools that
inspect code for problematic patterns without executing it, each covering
a different area:

```bash
npm install --save-dev eslint
npm install --save-dev --save-exact @biomejs/biome
```

Biome covers a small, handpicked rule set rather than its entire
“recommended” preset of roughly 200 rules. ESLint, with `typescript-eslint`
or a framework plugin, covers the rest: type-aware rules, framework rules,
and everything deliberately omitted from Biome's curated set. Overlap
means maintaining two synchronized configurations for the same rule, so
the division is deliberate.

### New rules never start by blocking

A new lint rule does not become an error in its introduction commit: that
either blocks everyone at once or frustrates someone into disabling it.
Instead, it starts as `"warn"` across the codebase, exposing existing
violations without breaking anyone's build. The warning count becomes
real and trackable, rather than a forgotten “tighten this later” comment.
Only when it reaches zero does the rule become `"error"` and remain there.

```js
// eslint.config.js (excerpt)
export default [
  {
    rules: {
      // Start a new rule at "warn" to expose counts without blocking.
      // Promote to "error" once the count reaches zero.
      complexity: ["warn", 10],
    },
  },
];
```

To eliminate warnings without turning “just fix the warnings” into a huge
silent refactor, use [ESLint warning burndown](prompts/02-eslint-warning-burndown.md).
It requires an explicit decision before code changes: fix everything, fix
most and track the remainder as visible debt, or rescope the rule itself.
The latter is a configuration change and must be treated as one, never
disguised as cleaner code.

For the complete ESLint/Biome division, intentionally disabled formatter,
and rule-specific pitfalls, see [ESLint/Biome quality
gates](tools/06-eslint-biome-quality-gates.md).

### The shortcut if you do not want manual setup

Part 5 explains the reasoning because it matters more than configuration.
For just the result, including a **350-line file limit**, the rule with
the greatest effect on code growth, there is a one-line path. Paste into
your agent:

```
Read https://raw.githubusercontent.com/soumatheusgomes/vibe-coding-toolkit/main/docs/prompts/08-eslint-quality-gates-install.md
and execute its prompt in this project. Use MAX_LINES=350.
```

It downloads three existing, tested rules, adapts configuration to your
structure, and reports how many files exceed the limit without fixing any.
The same instruction with [`09-file-size-refactor.md`](prompts/09-file-size-refactor.md)
then splits those files into smaller modules. The two documents:
[08 — install and measure](prompts/08-eslint-quality-gates-install.md),
[09 — split large files](prompts/09-file-size-refactor.md).


## Part 6 — Long-term memory

Without memory across sessions, an agent repeatedly relearns expensive
lessons: a previously fixed bug, or an architectural decision that only
makes sense after seeing rejected attempts. Two complementary options
address this.

### Option 1 — lightweight system (always start here)

A small index (`MEMORY.md`), always loaded at session start, has one line
per memory pointing to a topic file with frontmatter
(`type: feedback | architecture | business-rule | reference`). No external
dependencies, just files. The saving test: *would a future session be
surprised and grateful to know this before starting work?* If not, do not
save it. Full criteria and structure: [Claude memory
system](tools/09-claude-memory-system.md).

### Option 2 — Obsidian (unlimited long-term memory)

An Obsidian vault, Markdown files organized by folder convention, accessed
only through an **MCP server**, a process exposing structured vault
operations as tools rather than direct filesystem access. This ensures
every write undergoes validation: required frontmatter, a template for
each folder, and links pointing to actual notes. Details: [Obsidian as
memory](tools/08-obsidian-memory.md).

### Why both layers together are ideal

The lightweight index must remain small enough to read. Around 130 lines
is where it starts becoming noise rather than signal. Most worthwhile
project knowledge does not fit: it is too specific, rare, or large. That
is the vault's purpose: searched on demand without size limits. There is
even a formal migration path: search duplicates → match destination folder
template → create → confirm through read-back → only then remove from the
lightweight index. Never “delete and hope it is not needed again.”

To configure both layers in a new or existing project, use the ready-made
[Memory bootstrap](prompts/06-memory-bootstrap.md) prompt.

## Part 7 — Optional extras

Two standalone CLIs, installed through your existing package manager rather
than as Claude Code plugins, become useful once Parts 1–6 are running.

### Graphify — code navigation in large projects

Turns a folder of code, docs, papers, or images into a persistent knowledge
graph: community detection, central nodes, and file relationships. It
answers “what calls this?”, “which modules are central?”, and “what breaks
if I change this?” in one query, instead of dozens of repeated exploratory
reads each session.

```bash
uv tool install graphifyy
graphify claude install
```

The PyPI package is `graphifyy`, with two “y” characters; the command is
`graphify`, with one. Prefer `uv tool install`: plain `pip install` can
place the package in a different Python environment from the CLI runtime,
causing later command failures. `pipx install graphifyy` is also valid for
the same isolation reason.

After installing the package, run `graphify claude install` to connect
specifically to Claude Code, write `CLAUDE.md`, and configure the hook
automatically. Alternatively, `graphify install` detects and registers with
installed AI assistants. No API key is needed for a code-only corpus:
extraction uses ASTs (code syntax trees extracted without executing code)
and runs entirely locally.

> 💬 **Ask your agent:**
> ```
> Install Graphify for me: run `uv tool install graphifyy`, then `graphify claude install`.
> ```
> Claude Code runs both commands and confirms success; you do not need to do it manually.

Learn more: [Graphify](tools/07-graphify.md).

### agent-browser — browser automation for agents

A native CLI, rather than a Playwright/Puppeteer wrapper, controlling real
Chrome/Chromium through the DevTools Protocol. Built for AI agents instead
of adapted from a human-oriented testing tool, it uses accessibility-tree
snapshots with short, stable references (`@e1`, `@e2`...), handling layout
changes much better than CSS selectors.

```bash
npm i -g agent-browser
agent-browser install
```

> 💬 **Ask your agent:**
> ```
> Install agent-browser for me: run `npm i -g agent-browser`, then `agent-browser install`.
> ```
> Claude Code runs both commands and confirms success; you do not need to do it manually.

Learn more: [agent-browser](tools/11-agent-browser.md).

## Final checklist: project workflow

The checklist below supports modular adoption. For machine setup, the entire [prompt 10](prompts/10-development-environment-setup.md) foundation is mandatory, including Graphify, RTK, Context7, and both agents.

- [ ] Claude Code installed through the chosen method, authenticated, with `claude --version` working in a fresh terminal
- [ ] Superpowers installed and tested with an ambiguous request
- [ ] Ponytail installed and tested with a request inviting overengineering
- [ ] Caveman discovered and concise communication tested; usage counters kept separate from savings estimates
- [ ] `AGENTS.md` filled with actual stack, commands, and context; `CLAUDE.md` imports it and retains only client-specific instructions
- [ ] (If local configuration is needed) `.claude/settings.json` reconciled with existing settings; hooks registered only when their scripts exist and are needed
- [ ] (If using parallel waves) `parallel-subagent-driven-development.md` copied to `.claude/rules/` and referenced from `CLAUDE.md`
- [ ] Complete workflow run end to end at least once: brainstorm → plan → wave implementation → multi-agent review → commit
- [ ] ESLint and Biome configured with the curated/bulk division decided
- [ ] At least one new rule following warn→error adoption
- [ ] Lightweight memory (`MEMORY.md` and topic folder) configured
- [ ] (Optional) Obsidian vault and MCP server configured
- [ ] (Optional) Graphify installed if project size warrants it
- [ ] (Optional) agent-browser installed if the project involves browser automation

## Frequently asked questions and troubleshooting

**What if ESLint is already configured?**
Keep it. Biome sits alongside it with a small, deliberate rule set avoiding
what ESLint already covers. Part 5 divides work between them rather than
replacing one. Every new rule starts at `"warn"`, whether in Biome or
ESLint and whether the project is new or ten years old, preventing
adoption from becoming a day of broken builds for everyone.

**Must I use everything, or can I choose a subset?**
Choose a subset: each piece provides independent value, intentionally.
The strongest benefit comes from combining them. Memory alone is a small
convenience; together with subagent orchestration and quality gates, it
changes the workflow. If adopting just one, choose Superpowers: it has
the greatest effect because it ensures planning before implementation and
review before completion actually happen instead of being skipped under
time pressure.

**Does this work with Codex too?**
Yes. Use the [Codex guide](tools/15-codex-workflow.md), covering native installation, `AGENTS.md`, official plugins, skills, MCP, and supported hooks. Configure each client separately; do not copy `.claude/settings.json` as Codex configuration. Project prompts remain useful when adapted to the available tools and the chosen agent's permissions.

**Does this slow Claude Code down?**
Usually the net effect is the opposite. Most additions either cost nothing
(hooks intercept before the model sees the call, so the token proxy is a
pure gain) or save more time than they consume: fewer repeated exploratory
reads through Graphify, less rework because scope was settled first. The
honest exception is multiple subagents: each specialist has its own context,
increasing total tokens in exchange for shorter elapsed time and better
review. This is a deliberate tradeoff. Graphify and Obsidian are opt-in;
if the project is too small to need them, skipping both costs nothing.

**What exactly is a subagent?**
A separate Claude Code session launched by the main session for a specific
task, with its own context. It does not see the main conversation history,
only what the launch prompt explicitly supplies, according to the client's
context mechanism. Each delegated task therefore receives sufficient
instructions. The optional specialist roster belongs in shared agreements
when the project needs it.

**Plugins will not install or the marketplace cannot be found. What now?**
First check `claude --version`: plugins require a relatively recent CLI.
Then confirm the marketplace was actually added before installation:

```bash
/plugin marketplace list
```

If it is missing, repeat `add` with the exact URL from Part 2's table. A
typo in the repository name (`user/repo`) is the most common mistake.

## Next steps

This playbook covers the main path, enough to run a complete project. To
go further:

- **[RTK — token proxy](tools/03-rtk-token-proxy.md)**: a public CLI with official per-agent integration, output metrics, and an unfiltered escape hatch. Use it before maintaining a custom proxy.
- **[Project sanitation](prompts/01-project-sanitation.md)**: a good second
  prompt once Part 4 becomes routine, cleaning up the project by measuring
  before acting rather than assuming each finding's severity.
- Reread the [Overview](00-overview.md) after completing the workflow at
  least once: it makes more sense in retrospect than on first reading.
- The [README](../README.md) credits link to the original projects behind
  each plugin: Superpowers, Ponytail, Caveman, and aia-harness. Their
  authors' original work is worth exploring.
