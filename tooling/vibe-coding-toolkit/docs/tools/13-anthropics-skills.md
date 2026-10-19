# Official Anthropic skills

## What it is

An **Agent Skill** (a new capability the agent gains) is a folder containing an instruction file, `SKILL.md`, and optionally scripts and other resources (templates, examples, references) that teach an AI agent to perform a specific, repeatable task well: generating a document with a visual standard, following your team's data analysis workflow, or automating a recurring personal task. The key difference from an instruction pasted into a conversation is **on-demand loading**: a skill only enters the context window (the amount of text the model can “see” at once, which you pay for with each message) when the user's request matches it. It does not remain active unnecessarily when nobody needs that capability.

[`anthropics/skills`](https://github.com/anthropics/skills) is Anthropic's official public repository for these packages. Evaluate the source, license, host support, and usefulness for your task; popularity is not an installation or compatibility criterion.

### Skills, plugins, and MCP servers are different things

All three frequently appear together in Claude Code's vocabulary, but solve different problems:

| Concept | What it is | Where it runs |
|---|---|---|
| **Skill** | An instruction folder (+ optional scripts/resources), loaded only when the user's request matches | Inside the agent, using its existing tools (terminal, file reading/writing...), with no external process |
| **Plugin** | An installable package that can bundle **multiple** skills, slash commands (“/”), and hooks (scripts running automatically before/after an agent action) into one installation | Registered once in Claude Code; activates everything it bundles together |
| **MCP server** (*Model Context Protocol*, a standardized protocol exposing external tools and data to an AI agent) | A **separate external** program providing access to an external tool or data source: a GitHub server, library documentation, or database | Outside the agent, as a separate process; the agent connects through the protocol and never runs its code directly |

In practice, this repository combines the first two concepts: each individual skill (`docx`, `skill-creator`, and so on) is simply a folder with a `SKILL.md`, but installation in Claude Code groups them into **plugins**, each bundling several related skills (details under “How to install/activate” below).

### The repository documenting the format itself

Alongside ready-made skills, `anthropics/skills` is a reference for the **`SKILL.md`** format itself, the same file structure used by other vendored skills (copied into the project) documented in this toolkit: [Graphify](07-graphify.md) provides `.claude/skills/graphify/SKILL.md`, and [agent-browser](11-agent-browser.md) provides `.claude/skills/agent-browser/SKILL.md`. `SKILL.md` follows an **open standard** (a public specification not tied to one tool), documented at [agentskills.io](https://agentskills.io) and usable by any compatible AI agent, beyond Claude Code. The [official Claude Code documentation](https://code.claude.com/docs/en/skills) confirms it uses this standard as a foundation and adds its own features.

The minimum `SKILL.md` format has just two essential fields in a YAML metadata block (*frontmatter*, a readable data format common in configuration files), between `---`: `name` (the skill identifier) and `description` (what it does and when to use it, which the agent reads to decide whether the skill matches the current request). The Markdown body follows the frontmatter and contains the actual instructions:

```yaml
---
name: skill-name
description: What this skill does and when the agent should use it.
---

Instructions, examples, and best practices the agent follows while the skill is active.
```

## Why use it

Installing this particular repository, instead of a random standalone skill, addresses three things at once:

1. **An official source maintained by Anthropic itself.** This is not a third-party collection guessing the correct format: it comes from those defining the standard, making it a reliable reference for doing things correctly before writing your own skills.
2. **Office document skills address a real everyday gap.** `docx`, `pdf`, `pptx`, and `xlsx` generate and edit these actual formats, rather than simplified plain-text substitutes. They help anyone using an AI agent to assemble reports, presentations, or spreadsheets who currently has to convert its text manually.
3. **Two “meta” skills teach you to extend the ecosystem itself.** `skill-creator` guides the creation of your own skills; `mcp-builder` guides the construction of your own MCP server (the external component in the table above). This completes the cycle: beyond consuming ready-made skills, the repository teaches you to create your own.

One caveat before installation: **no single license covers the entire repository**. See “Tips and pitfalls” below for details.

## What the repository contains

The table illustrates the repository's plugin families. Read the current [marketplace manifest](https://github.com/anthropics/skills/blob/main/.claude-plugin/marketplace.json) and each skill's frontmatter before selecting packages; names and grouping can change:

| Plugin (in the `anthropic-agent-skills` marketplace) | What it bundles | Included skills |
|---|---|---|
| `document-skills` | Document workflows | `xlsx`, `docx`, `pptx`, `pdf` |
| `example-skills` | Creative, technical, and corporate example skills | `algorithmic-art`, `brand-guidelines`, `canvas-design`, `doc-coauthoring`, `frontend-design`, `internal-comms`, `mcp-builder`, `skill-creator`, `slack-gif-creator`, `theme-factory`, `web-artifacts-builder`, `webapp-testing` |
| `claude-api` | Claude API/SDK documentation for building LLM applications (*Large Language Model*, the type of AI behind Claude) | `claude-api` |

Within `example-skills`, the most commonly mentioned skills beyond document work include:

- **`skill-creator`** creates, edits, and optimizes your own skills (see Example 2 below).
- **`mcp-builder`** guides building an MCP server from scratch in TypeScript or Python (see Example 3 below).
- **`web-artifacts-builder`** builds more elaborate Artifacts (HTML pages rendered inside Claude/Claude.ai) with React, TypeScript, Tailwind, and shadcn/ui (a ready-made UI component collection used with Tailwind), including design guidance to avoid generic AI visuals: always-centered layouts, purple gradients, and identically rounded corners.
- **`webapp-testing`** tests local web applications with Playwright (a browser automation framework): frontend functionality, screenshots, and browser logs.
- **`frontend-design`, `canvas-design`, `algorithmic-art`, `theme-factory`** cover creativity and visual design.
- **`brand-guidelines`, `internal-comms`, `doc-coauthoring`, `slack-gif-creator`** target corporate workflows and communication.

Notice the actual name is **`web-artifacts-builder`**, with the `web-` prefix, rather than just `artifacts-builder`.

## How to install/activate

Inside a Claude Code session, register the repository as a marketplace (a source for installing plugins), then install the package you need:

```bash
/plugin marketplace add anthropics/skills
/plugin install document-skills@anthropic-agent-skills
```

The first command registers the GitHub repository as an installable marketplace; the second installs `document-skills`, all four Office document skills together. Repeat `/plugin install` for either of the other packages if desired:

```bash
/plugin install example-skills@anthropic-agent-skills
/plugin install claude-api@anthropic-agent-skills
```

You can also install through the interface without memorizing package names: after `/plugin marketplace add`, choose **Browse and install plugins** → **anthropic-agent-skills** → your package → **Install now**.

Confirm what is available in the current session:

```bash
/skills
```

After installation, there is no specific command to “activate” a skill: ask for the task normally and describe what you want. Claude Code uses each skill's `description` to decide which matches the request:

```
Use the PDF skill to extract the form fields from report.pdf.
```

You can also invoke a specific skill directly by name using `/plugin-name:skill-name`, for example `/document-skills:docx`, instead of describing the task and letting Claude Code choose. The colon format (plugin:skill) prevents name collisions between skills from different plugins.

### Install a single skill without the entire package

`example-skills` includes 12 skills. If you only want `skill-creator`, for example, without the other 11, you can vendor (copy into your project) just that skill's folder instead of installing the entire plugin. This is the pattern already used in this toolkit for [Graphify](07-graphify.md) and [agent-browser](11-agent-browser.md), except you copy a folder instead of running an installer:

> 💬 **Ask your agent to install it:**
>
> ```
> Download skill-creator from anthropics/skills and install it in
> my project: shallow-clone https://github.com/anthropics/skills.git
> (--depth 1) into a temporary folder, copy only skills/skill-creator
> to .claude/skills/skill-creator/, then remove the temporary folder.
> ```
>
> Claude Code has terminal (Bash) and file-writing access: it clones, copies the relevant folder, and confirms success. Prefer doing it yourself? Here are the exact commands:

```bash
git clone --depth 1 https://github.com/anthropics/skills.git /tmp/anthropics-skills
mkdir -p .claude/skills
cp -r /tmp/anthropics-skills/skills/skill-creator .claude/skills/skill-creator
rm -rf /tmp/anthropics-skills
```

A project skill (`.claude/skills/<name>/`) is versioned with the repository, so everyone on the team using Claude Code in that project gets it automatically. One caveat: if `.claude/skills/` did not exist before the current Claude Code session started, restart the session after creating it. Only skill folders present at session start are watched live; new folders require a restart ([source](https://code.claude.com/docs/en/skills)).

## Step-by-step tutorial

Let's install the document package and generate a real `.docx` report from scratch. The example is generic, a quarterly report, but the workflow applies to any content.

### 1. Install the document package

```bash
/plugin marketplace add anthropics/skills
/plugin install document-skills@anthropic-agent-skills
```

### 2. Request the report and describe its required content

Inside any project, with data available (a table pasted into the conversation, a spreadsheet, or a CSV):

```
Create a Word report (report.docx) with a TOC (table of contents,
 the clickable index at the beginning of a long document) at the
start, three sections with level 1 headings, a table showing sales
by quarter, and page numbers in the footer.
```

### 3. What happens behind the scenes

The `docx` skill's `description` covers this exact kind of request: creating, reading, editing, or manipulating Word documents. Claude Code therefore loads it automatically without an explicit invocation. It then:

1. Builds the `.docx` from scratch using the `docx` library (a ready-made npm/Node.js package that constructs the internal structure of a Word file);
2. If editing an existing document instead, opens the file, directly modifies its internal XML (`word/document.xml`: underneath, a `.docx` is a folder of XML files compressed as a ZIP), and repackages it;
3. Renders the result as images (through `pdftoppm`) to visually check it matches the request before returning the final file.

Source: [`skills/docx/SKILL.md`](https://github.com/anthropics/skills/blob/main/skills/docx/SKILL.md).

### 4. Check the generated file

Open `report.docx` in a real editor (Word, LibreOffice, Google Docs) and check the clickable table of contents, three sections, table with correct numbers, and footer page numbers. If something is wrong, describe it and request a correction: this edits the same file rather than regenerating it from scratch.

## Examples

### Example 1 — an `.xlsx` spreadsheet with formulas from raw data

Scenario: you have a raw list of product sales pasted from somewhere and want a real spreadsheet with formulas, rather than externally calculated numbers.

```
I installed document-skills. Here is a list of product sales
(pasted below). Build sales.xlsx with a detail sheet (one row
per product) and a summary sheet, using real formulas
(=SUM, =AVERAGE) to aggregate by category, rather than manually
precalculated values.
```

The `xlsx` skill creates the file with native Excel formulas. When opening it in Excel or Google Sheets, clicking a total cell shows `=SUM(...)`, rather than an already-resolved static number.

### Example 2 — create your own skill with `skill-creator`

Scenario: whenever you finish a task in your project, you follow the same manual steps to write a changelog entry (the file listing changes in each version), and want to turn this into your own reusable skill.

```
I installed example-skills. Use skill-creator to create a new skill:
whenever I finish a task, it should read the changes in `git diff`
and write a changelog entry using the format
"### <date> — <one-line summary>" plus bullets describing the changes,
in CHANGELOG.md.
```

Instead of writing `SKILL.md` manually, `skill-creator` conducts an interview before generating anything: what the skill should do, when it should trigger, and the expected output format. Only then does it write the folder structure (`SKILL.md` and, if supporting code is needed, `scripts/`) and suggest test requests to validate its triggering and behavior before calling it ready.

### Example 3 — build an MCP server with `mcp-builder`

Scenario: you have an internal API (for tasks, customers, or anything else) and want to expose its operations as tools any MCP-compatible AI agent can call, beyond Claude Code.

```
I installed example-skills. Use mcp-builder to help me create a
TypeScript MCP server exposing my internal task API (list, create,
mark complete) as tools.
```

`mcp-builder` guides four phases: research and plan the API design before writing code, implement the infrastructure and tools with clearly defined input/output formats, review quality and test, then create *evals* (automated tests checking whether an LLM can use the tool correctly) proving that an AI agent can actually operate the generated server.

## Tips and pitfalls

**No single license covers the entire repository.** The root of `anthropics/skills` contains `README.md` and `THIRD_PARTY_NOTICES.md`, with no general `LICENSE` file. Individual skills can have their own: the four Office document skills (`docx`, `pdf`, `pptx`, `xlsx`), for example, include their own `LICENSE.txt` tied to Anthropic's Terms of Service, explicitly prohibiting extraction of these materials outside Anthropic services, copying them (except automatically generated temporary copies during use), or creating derivative works. Before vendoring any skill from this repository, especially the four document skills, read that folder's `LICENSE.txt`. This describes the file's contents, rather than providing legal advice.

**Not every `SKILL.md` field works outside Claude Code.** The open standard (`agentskills.io`) and Claude.ai/API accept six frontmatter fields: `name`, `description`, `license`, `compatibility`, `metadata`, and `allowed-tools`. Claude Code accepts more, including `disable-model-invocation` (prevents automatic loading; only explicit invocation), `context: fork` (runs the skill in an isolated subagent), `hooks`, and `paths`, as its own extensions. A skill using only the six standard fields works everywhere; one using Claude Code's extra fields is specific to that client.

**Once loaded, the skill occupies context until the session ends.** The entire `SKILL.md` enters the conversation as one message and is not automatically discarded. It only leaves circulation through context compaction, when an oversized history is summarized. This reinforces why `SKILL.md` should be concise and large references should live in separate files loaded only when referenced: the same “minimal stub” principle used by [agent-browser](11-agent-browser.md).

**A new `.claude/skills/` folder is only watched after a restart.** If the folder existed when the Claude Code session began, added, edited, or removed skills are detected immediately without restarting. If the folder itself did not exist, for example in a project with no previous project skills, restart the session after creating it.

**Document skills check their work before returning the file.** For example, `docx` renders the result as images before considering the task finished. Do not assume “completed without errors” means “looks correct”; always open the final file yourself, as in tutorial step 4 above.

## Frequently asked questions

**Does this replace plugins I already use, such as Superpowers or Ponytail?**
No: these concepts coexist without conflict. A plugin such as [Superpowers](01-superpowers.md) can bundle skills, commands, and hooks; the skills in this repository are just the skill portion of such a package, with no fixed slash command or hook. Installing `document-skills` does not disable or replace any existing plugin.

**Must I install all 17 at once, or can I choose?**
You can choose. The three packages (`document-skills`, `example-skills`, `claude-api`) install separately. To get one skill from a larger package without the others, manually vendor that folder as shown under “How to install/activate” above.

**Does it only work in Claude Code?**
No. `SKILL.md` follows an open standard usable by any compatible agent. These particular skills are also available in paid Claude.ai plans, and you can use them or upload your own through the API using Anthropic's Skills API Quickstart.

**Can document skills (docx/pdf/pptx/xlsx) edit existing files, or only create new ones?**
Both. For example, `docx` covers both creating a new `.docx` and editing an existing one, including tracked changes and comments, beyond ordinary text.
