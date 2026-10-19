# Chrome DevTools MCP

## What it is

Chrome DevTools MCP is an MCP server (*Model Context Protocol*, the protocol connecting an AI agent to external tools, exposing each as an operation with a defined name and parameters) officially maintained by Google's Chrome DevTools team. Its official repository is [`ChromeDevTools/chrome-devtools-mcp`](https://github.com/ChromeDevTools/chrome-devtools-mcp), licensed under Apache 2.0. Consult the [Chrome for Developers guide](https://developer.chrome.com/blog/chrome-devtools-mcp) and current source for supported capabilities and requirements.

It gives the agent direct access to a real, live Chrome session: an actual running browser it controls and inspects, rather than a simulation or a headless browser (without a graphical interface) pretending to be something else. Tools cover the console, network inspection, performance traces (detailed recordings of browser activity during loading or interaction, showing where time went and what blocked what), screenshots, and general debugging. They answer “why is this page slow?” or “why did this request fail?” with real data rather than assumptions.

The official Chrome for Developers post captures the problem: coding agents cannot see what their generated code actually does in the browser. In the post's words, they code “with a blindfold on.” Chrome DevTools MCP removes that blindfold: the agent sees the actual result, beyond the source code it wrote.

## Why use it

**An important difference from [agent-browser](11-agent-browser.md), already documented in this toolkit: the tools solve different problems and complement each other.**

- **agent-browser provides automation**: the agent clicks, fills forms, and navigates a complete user flow. It answers “what happens if a user does X, Y, Z on this page?”
- **Chrome DevTools MCP provides diagnosis**: it inspects a running page to understand a specific problem, such as slow loading, a failed network request, or console output. It answers “what is actually happening on this page right now?”

A straightforward distinction often found in community comparisons: automation tools **drive** the browser (action); Chrome DevTools MCP **debugs** an already-running browser (observation). They are complementary, and can work together in one session: agent-browser navigates to the precise state you want to investigate (logged in, form completed, action triggered), and Chrome DevTools MCP then inspects what is happening in that same Chrome instance.

Without this tool, an agent debugging frontend problems is like a developer without browser developer tools: limited to source code and guesses. With it, the agent performs the same investigations a person would manually, without switching windows, copying values, or describing observations to you.

## How to install

> 💬 **Ask your agent to install it:**
>
> ```
> Install Chrome DevTools MCP for me: run `claude mcp add chrome-devtools --scope user npx chrome-devtools-mcp@latest`.
> ```
>
> Claude Code has terminal (Bash) access: it runs the command and confirms success. Prefer doing it yourself? Run the same command directly in your terminal.

Requirements from the official documentation: Node.js LTS (*Long Term Support*, the more stable long-term support release), npm, and the current stable Chrome version or newer. Without Chrome installed, the server has nothing to control.

A plugin installation path also combines the same MCP tools with ready-made skills (instruction files loaded on demand to teach the agent effective tool usage):

```bash
/plugin marketplace add ChromeDevTools/chrome-devtools-mcp
/plugin install chrome-devtools-mcp@chrome-devtools-plugins
```

(Source for both commands: [official project README](https://github.com/ChromeDevTools/chrome-devtools-mcp).) If an older installation of this MCP is configured differently, the README recommends removing that old configuration before reinstalling to avoid conflicting entries.

By default, the server starts a new Chrome instance. To connect to an already-open Chrome window, preserving login and session state, use `--browser-url` (also accepted as `--browserUrl`) pointing to Chrome's remote debugging port. Manual configuration in the MCP servers file (source: official README):

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "chrome-devtools-mcp@latest",
        "--browser-url=http://127.0.0.1:9222"
      ]
    }
  }
}
```

## Step-by-step tutorial

### 1. Install

> 💬 **Ask your agent to install it:**
>
> ```
> Install Chrome DevTools MCP for me: run `claude mcp add chrome-devtools --scope user npx chrome-devtools-mcp@latest`.
> ```
>
> Claude Code has terminal (Bash) access: it runs the command and confirms success. Prefer doing it yourself? Run the same command directly in your terminal.

### 2. Describe the symptom, not the cause

Request a diagnosis as you would from a colleague: describe the symptom you see, rather than the cause you do not yet know:

```
This local page (localhost:3000/dashboard) takes a long time
to become interactive. Find what is holding up loading.
```

### 3. The agent opens the page and records a performance trace

```
navigate_page({ url: "http://localhost:3000/dashboard" })
performance_start_trace({ reload: true })
```

Typical output (summary):

```
Trace completed — 4.2s until interactive.
Largest contributor: LCP (Largest Contentful Paint, measuring
  when the largest visible element finishes loading) at 3.8s,
  caused by a 2.4MB image loaded without optimization
  (banner-hero.png, 3840x2160).
Blocking script identified: analytics.js (612ms, render-blocking).
```

### 4. The agent reads the result and identifies the root cause

The final answer cites actual recorded data: file size, precise timing, and the specific resource delaying loading, rather than generic performance best practices that might not apply to this page.

## Concrete examples

### Example 1 — performance trace

**Request:** “Why is this page slow to load?”

The agent navigates to the page, starts a performance recording, and reads the result:

```
performance_start_trace({ url: "https://example.com/products", reload: true })
```

Typical output:

```
LCP: 4.1s (poor — ideally below 2.5s)
  Element: <img class="featured-product">
  Cause: image served at original size (1920x1080),
         displayed at 400x225, without resizing or lazy loading.

Recommendation: serve the image at its display size, or use
  `loading="lazy"` for images below the first screen.
```

The answer identifies the exact element, metric, and cause, because it comes from an actual recording of the page rather than a generic assumption that large images make pages slow.

### Example 2 — console and network errors

**Request:** “A button on this page does nothing when clicked. Find out why.”

```
navigate_page({ url: "http://localhost:3000/checkout" })
click(button_selector)
list_console_messages()
list_network_requests()
```

Typical output:

```
Console:
  [error] Uncaught TypeError: Cannot read properties of undefined
    (reading 'total') at checkout.js:142

Network:
  POST /api/cart/checkout → 404 Not Found
    (the requested endpoint does not exist in this API version)
```

Two concrete clues at once: the JavaScript error blocking the click and the network call returning 404, likely the root cause behind the console error. Without both, the diagnosis would remain “the button does not work,” without a clue why.

## Tips and pitfalls

**It needs a real running Chrome browser.** This is not a lightweight simulation: the server starts or connects to a real browser instance, with the associated memory and CPU usage. Environments without a graphical interface, such as some containers, may require explicit headless configuration.

**`--browser-url` reuses your authenticated session.** Instead of making the agent log in again on an authenticated page, open Chrome manually, log in, and point the server at that window through its remote debugging port. This is especially useful for pages requiring a session.

**An old installation can conflict with a new one.** The README warns that an existing Chrome DevTools MCP configuration should be removed first. Two differently configured entries pointing at the same server tend to confuse rather than help.

**The tool surface is large.** Dozens of tools cover input automation, navigation, emulation, performance, networking, debugging, memory, extensions, and PWA (progressive web apps). An overly broad request (“review the whole page”) tends to trigger more tool calls and consume more context than a specific symptom.

**It focuses on one page at a time, rather than a complete flow.** To diagnose a state reached after multiple screens, such as login, cart, and checkout, combine it with [agent-browser](11-agent-browser.md): that tool reaches the right state, and Chrome DevTools MCP investigates it.

## Frequently asked questions

**Must Chrome be installed?**
Yes: the official documentation requires the current stable Chrome version or newer. The server controls actual Chrome, either starting a new instance or connecting to an existing window through `--browser-url`.

**Does it work in production or only on localhost?**
It works with any URL the browser can open: local, staging, or production. It is a real controlled browser and does not distinguish local from public pages. Official documentation examples use a real production URL. The typically local part is the remote debugging address (`--browser-url`, usually `127.0.0.1`) when connecting to an already-open Chrome window on your computer, but the page loaded *inside* that window can be any URL.

**Is this the same as Playwright MCP?**
No. Their purposes differ, a distinction clearly drawn by the community: Playwright MCP **drives** browsers through repeatable, cross-browser automation (Chrome, Firefox, WebKit) for testing workflows. Chrome DevTools MCP **debugs** a particular running Chrome instance through performance traces, console, and network inspection. For “does this user flow work end to end?”, choose Playwright MCP or this toolkit's [agent-browser](11-agent-browser.md). For “why is this particular page slow or broken?”, Chrome DevTools MCP provides a more direct answer.

**Can it work with this toolkit's agent-browser?**
Yes, this is a useful combination: agent-browser navigates to the state to investigate, and Chrome DevTools MCP inspects what is happening there, as detailed under “Why use it” above.
