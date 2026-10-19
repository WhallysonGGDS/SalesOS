# Context7

## What it is

Context7 is an MCP server (*Model Context Protocol*: the protocol connecting an AI agent to external tools and data sources, exposing each as an operation with a name, parameters, and validation) maintained by [Upstash](https://upstash.com). Its source is [`upstash/context7`](https://github.com/upstash/context7). Use the documentation for your client and running version to configure the integration.

It solves a concrete problem: a language model has a knowledge cutoff (the latest information its training included), but code libraries keep changing afterward. Function signatures change, new hooks appear, and configuration options change names or locations. Without external help, the agent fills the gap by “hallucinating”: confidently inventing a plausible API that no longer exists, or never existed in that form. Context7 closes this gap by injecting real, current documentation for the right version directly into the agent's context through two tools:

- **`resolve-library-id`** takes `libraryName` and `query`, the lookup objective, and returns candidate library identifiers.
- **`query-docs`** takes `libraryId` and `query`, containing a specific question, and returns relevant excerpts. Check the project's installed version when choosing the identifier.

(Older documentation and tutorials sometimes call the second tool `get-library-docs`; see “Tips and pitfalls” below.)

The project appears in the official `marketplace.json` of [`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official), the same marketplace this toolkit uses to install [Superpowers](01-superpowers.md), as the `context7` plugin, maintained by Upstash and marked “community-managed” (maintained by the community rather than Anthropic itself, but distributed through its official marketplace). This combination of official distribution and considerable independent adoption is rare, and helps explain why Context7 comes up in almost every discussion of MCP development tools.

Important: **Context7 is not exclusive to Claude Code.** It works with any MCP-capable client, including Cursor, Windsurf, VS Code, Claude Desktop, and others, each with its own connection guide.

## Why use it

Ask any AI agent “how do I configure X in the latest version of library Y” and there is a real chance its answer comes from a time when the API was different. The problem is not that the agent knows nothing: it knows an older version and answers with the same confidence, without flagging uncertainty. Common results include code that will not compile, a configuration option rejected by the linter or build, or an API call returning a method-not-found error.

Without Context7, fixing this becomes trial and error: the agent writes something plausible, you run it, it breaks, you paste the error back, and the agent tries again. Each round consumes your time and its tokens until luck or manual research finds the right syntax. With Context7, the agent fetches the installed version's actual documentation *before* answering. Trial and error does not disappear entirely (documentation can also be incomplete or ambiguous around an edge case), but it shrinks considerably because the answer starts from facts rather than outdated training memories.

## How to install

> 💬 **Ask your agent to install it:**
>
> ```
> Install Context7 for me: run `npx ctx7 setup --claude` in the terminal.
> ```
>
> Claude Code has terminal (Bash) access and runs the command for you. Unlike most tools in this toolkit, this command opens an OAuth login flow: a browser tab opens automatically and asks you to confirm authentication. Installation is not entirely “ask and forget”: the agent starts the command, but you must confirm in the browser. Prefer doing it yourself? Run the same command directly in your terminal.

`npx ctx7 setup --claude` (source: [official Context7 client documentation](https://context7.com/docs/clients/claude-code)) authenticates through OAuth, generates an API key automatically, and lets you choose CLI or MCP mode for Claude Code. For additional features, including skills triggered by mentioning a library, dedicated agents, and the manual `/context7:docs` command, install the full plugin instead (source: [official project README](https://github.com/upstash/context7)):

```bash
/plugin marketplace add upstash/context7
/plugin install context7@context7-marketplace
```

Authentication and limits depend on the current method and plan. Prefer the official OAuth flow when provided by the plugin/setup. If you choose a key, configure the client through the documented mechanism and keep the secret out of the project and chat. Exporting a variable named `CONTEXT7_API_KEY` alone does not guarantee the MCP connection uses it.

Confirm the connection worked by asking the agent to list available MCP tools, or simply asking a question that requires library documentation (next section) and observing whether it consults Context7 before answering.

### Codex: plugin or direct connection

The [official client guide](https://context7.com/docs/resources/all-clients) includes a Codex plugin. In the terminal:

```bash
codex plugin marketplace add upstash/context7
codex plugin add context7@context7-marketplace
```

Alternatively, register the remote server directly:

```bash
codex mcp add context7 --url https://mcp.context7.com/mcp
```

Choose one method when both provide the same server. In Claude Code, the remote alternative uses `claude mcp add --scope user --transport http context7 https://mcp.context7.com/mcp`. Complete the authentication required by the service and open a new session. A listed connection must still respond to a real query to be validated.

See also the [Codex guide](15-codex-workflow.md). For clients that do not support the chosen method, use the documented alternative instead of copying another agent's configuration.

## Step-by-step tutorial

### 1. Install

> 💬 **Ask your agent to install it:**
>
> ```
> Install Context7 for me: run `npx ctx7 setup --claude` in the terminal.
> ```
>
> Claude Code has terminal (Bash) access and runs the command for you, but you must confirm the OAuth login in the browser tab. Prefer doing it yourself? Run the same command directly in your terminal.

### 2. Ask a question requiring current documentation

Ask something only the right version's documentation can answer properly: an API detail that changes between versions, rather than a general concept:

```
How do I use React's `use()` hook to read a Promise inside
 a component in the latest version?
```

### 3. The agent resolves the right library first

Before answering, the agent calls `resolve-library-id` to find the exact identifier:

```
resolve-library-id({
  libraryName: "React",
  query: "How do I read a Promise with use in a React component?"
})
```

Illustrative candidates; use the identifiers actually returned:

```
/reactjs/react.dev  — React — official documentation
/facebook/react      — React — source code on GitHub
...
```

### 4. The agent fetches that version's actual documentation

With the identifier, it calls `query-docs`, usually with a topic to focus the lookup:

```
query-docs({
  libraryId: "/reactjs/react.dev",
  query: "How do I read a Promise with use and handle component suspension?"
})
```

Typical output (excerpt):

```
## use

`use(promise)` or `use(context)` reads the value of a resource, such as a
Promise or Context, directly during rendering.

Unlike other hooks, `use` can be called inside
conditionals and loops...

Example:
  function Comments({ commentsPromise }) {
    const comments = use(commentsPromise);
    ...
  }
```

### 5. The final answer is backed by actual documentation

The agent answers with the exact signature and behavior it just fetched: a live lookup against real documentation, rather than a training memory.

Make one query per concept. If the question covers independent subjects, such as routing and authentication, query each separately. Never include secrets, personal data, or private code in the search; describe the library's public behavior.

## Concrete examples

### Example 1 — a library that changed recently

**Question:** “How do I configure custom colors in the latest Tailwind CSS version?”

Tailwind CSS changed substantially between versions 3 and 4: configuration moved from a JavaScript file (`tailwind.config.js`, with a `theme.extend.colors` object) to a CSS-first approach, directly in the stylesheet through the `@theme` directive. An agent without Context7, or with Context7 available but unused, tends to answer with the older pattern because it appeared much more frequently in training data before the cutoff:

```js
// plausible answer, but outdated for Tailwind v4
module.exports = {
  theme: {
    extend: {
      colors: { brand: "#F7A072" },
    },
  },
};
```

After consulting Context7, the answer matches the project's installed version:

```css
/* Tailwind CSS v4 — configuration directly in CSS */
@import "tailwindcss";

@theme {
  --color-brand: #F7A072;
}
```

### Example 2 — a case the agent would get wrong without Context7

**Question:** “How do I read a cookie in a Next.js Server Action?”

Starting in Next.js 15, `cookies()` and `headers()` became asynchronous, requiring `await`, after being synchronous for several previous versions. An agent answering from memory without checking the installed version has a real chance of returning the old synchronous pattern:

```ts
// wrong in v15+: cookies() now returns a Promise
import { cookies } from "next/headers";

export async function myAction() {
  const cookieStore = cookies(); // missing await
  return cookieStore.get("session");
}
```

This is not a typo: it causes a runtime error (or build error, depending on usage), because `cookieStore` becomes an unresolved `Promise` rather than the expected object. After checking the installed version's actual documentation through Context7, the answer includes `await` in the right place:

```ts
import { cookies } from "next/headers";

export async function myAction() {
  const cookieStore = await cookies();
  return cookieStore.get("session");
}
```

## Tips and pitfalls

**The second tool used to have another name.** Older documentation and tutorials call it `get-library-docs`; the current Upstash-hosted version exposes `query-docs`. If a guide mentions one name while your agent's tool list shows another, that is a difference in the documentation's version or date, rather than an installation error.

**Without an API key, the request limit is shared with everyone using anonymous mode.** During a busy session, or for a whole team behind one IP, this can mean slower responses or rate-limit rejections. The key is free: generate one before hitting that limit rather than afterward.

**Context7 only knows what it has indexed.** If a library does not resolve, try a more precise name or query. If it is still missing, consult the project's official documentation and identify that alternative source; do not treat a memory-based answer as verified documentation.

**The search engine behind it is closed.** The MCP client (what you install and connect) is MIT-licensed open source. Upstash's hosted backend performs the actual crawling, parsing, and searching and is not open source. This does not change everyday usage, but explains why you cannot simply run your own instance of the entire Context7 service.

**Context7 does not replace understanding the library.** It is excellent for exact API syntax: the right signature, parameter, and current usage example. For design decisions (“why did this library choose this pattern,” “when should I use X instead of Y”), the complete prose documentation, read by a person, remains more valuable.

## Frequently asked questions

**Do I need to pay?**
Not for normal use. The MCP client is free and open source (MIT); Upstash's hosted backend has a free tier, either anonymous with a shared rate limit or with a free API key and a higher individual limit. Teams with heavy usage should check current plans directly on Upstash's website.

**Does it work with any language or framework?**
In practice, with any library Context7 has indexed, covering a large portion of JavaScript/TypeScript, Python, and other ecosystems. A library that is too new, internal to a company, or has never been crawled will not resolve.

**Does this replace reading official documentation?**
No. It is a quick lookup layer designed to inject the right excerpt into the agent's context when needed, rather than replace your own understanding of a library when the question concerns design instead of syntax.

**Do I need to restart the agent session after installation?**
Usually yes: as with any new MCP server, the agent only sees its tools in a new session after the connection has been configured.
