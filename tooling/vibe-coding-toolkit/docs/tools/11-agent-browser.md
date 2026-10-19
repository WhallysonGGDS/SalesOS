# agent-browser

## What it is

agent-browser is a standalone CLI (command-line interface), installed through npm (the default Node.js/JavaScript package manager). It is a separate tool, rather than a Claude Code plugin, and works with any AI agent capable of running terminal commands. It is a browser automation agent in the style of Vercel projects, controlling a real Chrome/Chromium browser through the DevTools Protocol (the remote debugging protocol exposed by Chrome itself, also used behind the scenes by the browser's developer tools).

Important: it is **not a wrapper** (a thin layer on top) around libraries such as Playwright or Puppeteer. It was written from scratch as a native CLI specifically designed for control by an AI agent, rather than adapted from a tool originally built for humans writing automated tests.

The practical difference: instead of CSS selectors (the “addresses” identifying an element on a page, such as `#login-button`) or screenshot-only interaction (the AI looking at pixels and guessing where to click), agent-browser takes *snapshots* of the *accessibility tree*: the structure screen readers use to navigate a page without seeing it, including headings, buttons, fields, links, and their relationships. It returns compact element references such as `@e1`, `@e2`, and `@e3`.

## Why use it

A CSS selector breaks when a page layout changes. A screenshot-only approach forces the agent to reason about pixels, which is expensive and imprecise. A short, stable accessibility reference (`@e1`, `@e2`, ...) gives the agent something it can act on directly and request again cheaply after the page changes. This is closer to how a screen reader “sees” a page than how a traditional scraper works.

## How to install

> 💬 **Ask your agent to install it:**
>
> ```
> Install agent-browser for me: run `npm i -g agent-browser`, then `agent-browser install`.
> ```
>
> Claude Code has terminal (Bash) access: it runs the commands and confirms they worked. You do not need to open a separate terminal or know the difference between `pip`/`uv`/`npm`. Prefer doing it yourself? Run the exact same commands directly in your terminal.

The first command installs the CLI globally; the second downloads and prepares the Chrome/Chromium browser it will control (similar to `playwright install`, for anyone familiar with Playwright).

Confirm:

```bash
agent-browser --version
```

## Basic workflow

| Command | What it does |
|---|---|
| `agent-browser open <url>` | Opens a page. |
| `agent-browser snapshot` | Takes a snapshot of the current page's accessibility tree, with references (`@e1`, `@e2`, ...). |
| `agent-browser click @eN` | Clicks the element referenced by `@eN` in the latest snapshot. |
| `agent-browser fill @eN "text"` | Fills the field referenced by `@eN` with the given text. |
| `agent-browser screenshot file.png` | Saves a PNG screenshot. |

Golden rule: **take a fresh snapshot after any action that substantially changes the page.** References are only valid against the snapshot they came from. Reusing a reference from an old snapshot after the page changes points to the wrong element or nothing at all.

## The discovery stub pattern

The file a coding agent loads to learn this tool (the “skill”: in agent-browser's vocabulary, an instruction package loaded on demand for a specific capability) is deliberately tiny. Instead of duplicating a complete Markdown guide that would become outdated with every CLI release, it simply tells the agent to fetch the actual, current instructions directly from the CLI:

```bash
agent-browser skills get core          # workflows, patterns, troubleshooting
agent-browser skills get core --full   # complete command and template reference
agent-browser skills list              # all skills available in this installation
```

The stub never becomes outdated because there is nothing in it to go stale: the actual content always matches the version installed when it is fetched. This pattern is worth copying in your own tools: keep the always-loaded file tiny, and fetch the actual instructions live when needed.

For the same reason, this document avoids duplicating an exhaustive command reference. For anything beyond the basic workflow above, `agent-browser skills get core --full`, run in your installation, is the source of truth, rather than this text.

## Step-by-step tutorial

### 1. Install

> 💬 **Ask your agent to install it:**
>
> ```
> Install agent-browser for me: run `npm i -g agent-browser`, then `agent-browser install`.
> ```
>
> Claude Code has terminal (Bash) access: it runs the commands and confirms they worked. You do not need to open a separate terminal or know the difference between `pip`/`uv`/`npm`. Prefer doing it yourself? Run the exact same commands directly in your terminal.

### 2. First command: fetch the actual instructions

```bash
agent-browser skills get core
```

This returns a Markdown guide covering workflows, common patterns, and troubleshooting for the installed version. The exact content varies by version, so run it yourself rather than relying solely on this document.

### 3. Open a page

```bash
agent-browser open example.com
```

### 4. Take a snapshot and read its text directly

```bash
agent-browser snapshot
```

Typical output for this particular page (`example.com` is a domain reserved for documentation examples, with consistent content):

```
Page: Example Domain
URL: https://example.com/

@e1 [heading] "Example Domain"
@e2 [text] "This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission."
@e3 [link] "More information..."
```

Notice that “extracting text” does not require a separate command: visible text is already included in the snapshot alongside each reference. Reading `@e2` in the result above **is** the extraction.

## Examples

### Example 1 — fill out and submit a form

A generic registration form running locally:

```bash
agent-browser open localhost:3000/signup
agent-browser snapshot
```

Typical output:

```
Page: New registration
URL: http://localhost:3000/signup

@e1 [heading] "Create account"
@e2 [form]
  @e3 [input type="text"] placeholder="Full name"
  @e4 [input type="email"] placeholder="Email"
  @e5 [input type="password"] placeholder="Password"
  @e6 [button type="submit"] "Create account"
```

Fill out the fields and submit:

```bash
agent-browser fill @e3 "Maria Oliveira"
agent-browser fill @e4 "maria@example.com"
agent-browser fill @e5 "strong-password-123"
agent-browser click @e6
```

Clicking `@e6` submits the form and changes the page. Following the golden rule above, the next step is a fresh snapshot, rather than reusing `@e3`–`@e6`:

```bash
agent-browser snapshot
```

```
Page: Registration confirmed
URL: http://localhost:3000/welcome

@e1 [heading] "Account created successfully"
@e2 [text] "We sent a confirmation email to maria@example.com."
```

### Example 2 — take a page screenshot

```bash
agent-browser open example.com
agent-browser screenshot page.png
```

Expected output: a `page.png` file in the current directory and a confirmation similar to:

```
Screenshot saved to page.png (1280x800)
```

## Beyond ordinary web pages

Extended capabilities load just like `core` above: on demand, each as its own skill, instead of all being bundled into the main documentation from the start:

| Skill | Covers |
|---|---|
| `electron` | Desktop apps built with Electron (a framework for building desktop applications using web technologies): code editors, chat apps, and design tools. |
| `slack` | Corporate chat app (workspace) automation. |
| `dogfood` | Exploratory QA/*dogfooding* passes (using your own application internally to find problems before real users do) on a web application. |
| `derive-client` | Deriving a standalone API client from captured network traffic: a HAR file (*HTTP Archive*, the standard format recording every browser request and response). |
| `vercel-sandbox` | Running inside cloud-hosted sandbox VMs (virtual machines): isolated, disposable environments for running something without risking the rest of the system. |
| `agentcore` | Cloud-hosted browser sessions. |

Fetch any of them the same way: `agent-browser skills get <name>`.

## Tips and pitfalls

**`@eN` references are generated for each snapshot and become stale as soon as the page changes.** Always take a fresh snapshot after an action that substantially changes the page: a click, navigation, or form submission. An old reference does not always cause an error; sometimes it silently points to the wrong element.

**This document can become outdated; the CLI cannot.** Following the discovery stub pattern above, the complete, current command reference is `agent-browser skills get core --full`, run in your installation, rather than this text or another static guide.

**An annotated screenshot helps verify the agent's work.** `agent-browser screenshot --annotate file.png` numbers visible elements to match the snapshot's `@eN` references, useful when someone wants to visually check what the agent “saw” before acting. `--full` captures the entire scrollable page, rather than only the visible screen.

**Poor timing causes more failures than poor selectors.** If an action seems to do nothing, the page was most likely still loading or transitioning during the interaction, rather than the reference being wrong. Take a verification snapshot before repeating the action.

## Frequently asked questions

**Do I need to know Playwright or Puppeteer to use this?**
No. agent-browser is not a wrapper around either: it has its own commands, and those tools do not use accessibility references in the same way.

**Does it only work with Claude Code?**
No, it is standalone and works with any AI agent that can run terminal commands.

**Can it automate a desktop application, such as a code editor?**
Yes, through the `electron` skill, loaded on demand with `agent-browser skills get electron`.

**Do `@eN` references change between runs?**
Yes: they are generated from scratch for every snapshot. Never reuse a reference from an earlier snapshot.

**Do I need to maintain my own guide for every new CLI version?**
Not for the commands themselves. The source of truth is always `agent-browser skills get core`; this document is the conceptual entry point, explaining the “why” behind the tool rather than the exact “how” of each command.
