# Obsidian as Memory

## What it is

An Obsidian vault — plain Markdown files stored on disk and organized by a folder convention — used as a project's long-term memory. The access convention in this optional pattern is to route agent reads and writes through a validating MCP server (*Model Context Protocol*, a protocol that exposes operations as structured tools — with names, parameters, and validation — for an AI agent to call, instead of letting the agent manipulate raw filesystem files).

A server configured with these checks can reduce drift for writes made through it:

- **required frontmatter** — metadata at the top of a Markdown file, between two `---` lines, such as title and description;
- **one template per folder**, defining which sections a note must have and in what order;
- **link checking** — a `[[wikilink]]` (the double-bracket link style Obsidian uses to connect notes) to a nonexistent note is rejected, rather than silently accepted as a broken link;
- **a consistent slug style** (the "flattened" version of a filename — lowercase, without accents, with hyphens instead of spaces) **and tag style.**

A manual edit directly in the file bypasses all of this — and only visibly breaks the convention much later, during an unrelated write.

This is optional infrastructure. Prefer native client memory or existing
repository documentation when those meet the need; no vault or new dependency
is required. Follow the [portable storage and freshness rules](09-claude-memory-system.md#portable-storage-and-freshness): record source, evidence,
last verified date, and invalidation condition. Daily task handoffs are
working state, not automatically durable knowledge.

## Why use it

An always-loaded index (see [Claude memory system](09-claude-memory-system.md)) needs to stay small to remain useful — if it grows too large, it becomes something to skim rather than actually read. Most things worth remembering about a project do not fit there: they are too specific, rarely needed, or would simply push the index beyond the size worth loading in every session.

The vault is where this long tail goes — the large but individually infrequently accessed portion of what a project "knows": searchable on demand, without a size limit, and structured enough for searches to find what they need instead of becoming a heap of loose files.

## How to install

Several open-source MCP servers expose an Obsidian vault (or any Markdown folder) as a set of tools. No single "official" package is recommended here deliberately — search for "obsidian" in an MCP registry (a catalog of MCP servers available to install) and choose one supporting mandatory templates and frontmatter if you want this exact validation pattern. Such a server usually exposes tools resembling these (exact names vary by server):

- search (by text, tag, frontmatter property, date)
- note reading (full content or just metadata/size)
- creation and editing (whole note or just a section by heading)
- links (what points to this note, where this note points, broken links)
- structure (rename, move, create folder)

General installation steps:

1. Create the vault folder in your project (e.g., `vault/`) and the PARA subfolders (next section).
2. Write one template per folder — the frontmatter and required sections that notes in that folder must have.
3. Install the chosen MCP server and configure it in your agent, pointing to the vault folder. Configuration is usually a file such as `.mcp.json`:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "npx",
      "args": ["-y", "<chosen-server-package>"],
      "env": {
        "VAULT_PATH": "${CLAUDE_PROJECT_DIR}/vault"
      }
    }
  }
}
```

   Exact command and environment variable names vary by server — check the README of your chosen server before copying this literally.

4. Restart the agent session and confirm that vault tools appear in the list of available tools.
5. Optionally add the illustrative hook below to remind agents using the named tools about the access convention. It is not a security boundary.

## Folder structure

A generic PARA-style structure (the organizational method created by Tiago Forte, standing for **P**rojects, **A**reas, **R**esources, **A**rchives) works well, with two practical additions:

| Folder | Stores |
|---|---|
| **active projects** | Work with a defined end state — ends when the project ends. |
| **ongoing areas** | Responsibilities with no end date — e.g., "payment module maintenance." |
| **consolidated knowledge** | Timeless, reusable lessons — equivalent to the original PARA "Archives," but treated as an active destination rather than dead storage. |
| **reference** | Reference material — external documentation, third-party decisions, useful links. |
| **daily/session log** | A rotating scratchpad, one file per day — never the final home of anything. |
| **templates** | Defines the required format for each folder above. |

## Step-by-step tutorial

Building this structure in a new project from scratch:

### 1. Create the folders

```bash
mkdir -p vault/{01-projects,02-areas,03-knowledge,04-reference,daily,templates}
```

### 2. Write one template per folder

For example, `vault/templates/03-knowledge.md`:

```markdown
---
name:
description:
metadata:
  type:
source:
evidence:
last_verified:
invalidate_when:
---

## Context

## Rule or fact

## Why it matters

## Related
```

The MCP server uses this template to validate every new or edited note inside `03-knowledge/` — same sections, same order (extra sections are allowed, but none of the required sections may be missing).

### 3. Install and configure the MCP server

Point it to the `vault/` folder (see "How to install" above).

### 4. Write the protection hook

This optional step adds a convention guardrail, not protection against all access. See "Enforcing 'MCP only' with a hook" below for its limits; if used, adjust the literal path and register the named tools.

### 5. Test both paths

Ask the agent to create a well-formed note in one of the folders through MCP — it should work. Then request a direct file read (`Read` on the vault path) — the hook should block it and explain why. Both complete examples appear in the next section.

## Examples

### Example 1 — well-formed note, accepted

File: `vault/03-knowledge/large-order-approval-rule.md`

```markdown
---
name: large-order-approval-rule
description: Orders with 10 or more items require manual supervisor approval before proceeding to processing.
metadata:
  type: business-rule
source: approved order-processing decision
evidence: supervisor-approval acceptance check
last_verified: YYYY-MM-DD
invalidate_when: approval threshold or processing policy changes
---

## Context

Discovered while investigating why some orders were stuck in
"pending" without any corresponding error in the log.

## Rule or fact

Orders with 10 or more items automatically enter a manual
approval queue — this is not a bug, but intentional business validation.

## Why it matters

An agent investigating "why didn't this order process automatically" without
knowing this rule will look for a bug where none exists.

## Related

- [[order-processing-flow]]
```

This illustrative note requires an actual source, check result, and verified date before saving. With those filled in, it passes validation when: `name` matches the filename (without the `.md` extension) and is in kebab-case (lowercase, with hyphens); `description` is filled in; `metadata.type` is an accepted type; the sections match the folder template in the same order, with `Related` last; and the wikilink `[[order-processing-flow]]` points to a note that actually exists in the vault.

### Example 2 — malformed note, rejected

Attempt to create `vault/03-knowledge/ApprovalRulé.md`:

```markdown
---
name: ApprovalRulé
metadata:
  type: note
---

# Large order approval

Large orders need approval. See [[Flow That Does Not Exist]].
```

The server rejects the write with a message resembling this (exact wording varies by server):

```
ToolError: write rejected —
  • frontmatter: required field "description" missing
  • frontmatter: "name" (ApprovalRulé) is not kebab-case; use approval-rule
  • metadata.type: "note" is not an accepted type (use feedback | architecture | business-rule | reference)
  • structure: required sections from this folder's template are missing ("Why it matters", "Related")
  • wikilink: [[Flow That Does Not Exist]] does not exist — no note matches this title
```

Five problems at once, all things a manual edit directly in the file would let slip through:

1. Missing `description`.
2. `name` violates kebab-case and includes an accent.
3. `metadata.type` falls outside the accepted vocabulary — this vault uses the same vocabulary as the always-loaded index (`feedback | architecture | business-rule | reference`, see [Claude memory system](09-claude-memory-system.md)), precisely so migration between them is mechanical, without reclassifying anything.
4. Sections required by the folder template are missing.
5. A wikilink to a nonexistent note — rejected immediately instead of silently becoming a broken link.

## Enforcing "MCP only" with a hook

The heading describes an access convention, not complete enforcement. This
illustrative `PreToolUse` guardrail checks only the registered `Read`, `Grep`,
`Glob`, `Write`, and `Edit` tools and literal path strings containing `vault/`.
It fails open on invalid events. Shell commands, other tools, omitted paths,
path aliases, and direct human edits can bypass it. The daily read exception
also bypasses MCP for those reads. It is **not a security boundary** and does
not guarantee MCP-only access; use actual filesystem permissions or sandbox
controls if access isolation is required. No new hook logic is needed to use
the memory convention.

The same JSON stdin (standard input) reader as the token proxy hook: [`hook-io.mjs.example`](../../templates/hooks/hook-io.mjs.example), which exposes `readStdinRaw()` (reads stdin without ever throwing) and `parseHookEvent()` (attempts to parse, returning `null` for both invalid JSON and the literal value `null` — the two cases that often crash a hastily written hook):

```js
#!/usr/bin/env node
// PreToolUse hook — matcher: Read|Grep|Glob|Write|Edit
(async () => {
  const { readStdinRaw, parseHookEvent } = await import("./hook-io.mjs");
  const event = parseHookEvent(readStdinRaw());
  if (event === null) process.exit(0); // nothing to analyze — fail open

  const path =
    event?.tool_input?.file_path ??
    event?.tool_input?.path ??
    event?.tool_input?.pattern ??
    "";

  if (!path.includes("vault/")) process.exit(0); // not the vault — allow

  const isDailyRead =
    path.includes("vault/daily/") && ["Read", "Grep", "Glob"].includes(event.tool_name);
  if (isDailyRead) process.exit(0); // narrow exception: read-only daily folder access

  console.error("vault/ is MCP-only — use the vault's MCP tools, not direct file access.");
  process.exit(2); // blocks; the message above is shown to the agent
})();
```

See [Hook best practices](10-hooks-best-practices.md) for the general reasoning behind "failing open" and the specific care around `JSON.parse("null")` that the snippet above already handles.

## Automating capture and consolidation

If recurring capture warrants automation, two optional hooks can support it:

- An **end-of-session** hook (runs when the session ends) records a short summary in the day's note — work done, decisions made, problems encountered.
- A **start-of-session** hook can propose durable lessons from daily entries. Verify each against its source, record evidence and freshness metadata, and confirm the saved note by reading it back before any authorized cleanup of the raw log.

Retain unprocessed daily notes and unfinished handoffs. Cleanup follows the project's retention policy only after confirmed consolidation; automation must not treat every session summary as durable truth.

## Migrating from the always-loaded index to the vault

The always-loaded index (see [Claude memory system](09-claude-memory-system.md)) and vault are not competing stores — there is an explicit migration path between them for when an index entry no longer deserves its place in something read every session:

1. **Dedup** — search the vault first; extend an existing note instead of creating a near-duplicate.
2. **Match the template** — fetch the destination folder's required template and follow it exactly.
3. **Create** the note.
4. **Confirm by reading it back** — without a successful read after writing, the migration has not actually happened.
5. **Only then** delete the short copy from the always-loaded index.

Never jump straight to step 5. An unconfirmed migration is data loss, not relocation — the entry existed nowhere during the time it took someone to notice the mistake.

## Tips and pitfalls

**Reading the vault directly "just this once" is exactly the habit the hook exists to break.** If you find yourself wanting to bypass the block, that signals a missing MCP tool (such as batch listing), not a reason to ignore the rule.

**The daily-folder exception in the hook above is read-only.** A hook that also permits direct writing to `daily/` bypasses frontmatter and template validation for those files too — always keep writes through MCP, even in the daily folder.

**Search before creating.** A wikilink to a note that does not yet exist fails immediately under a strict link policy — create the target note first, or use plain text until it exists.

**Keep "Related" as the last section**, even if the template technically permits another position — that is where compilation and deduplication tools expect it.

**A write that "succeeded" but was not confirmed by reading is not truly confirmed.** Treat it as possibly lost until migration step 4 (reading it back) actually happens.

## Frequently asked questions

**Why not let the agent edit `.md` files directly?**
Because without centralized validation, the vault degrades over time: inconsistent frontmatter, broken links, inconsistent filenames — every manual edit is a chance to stray from convention, and nobody notices until much later.

**Does this replace the always-loaded index (`MEMORY.md`)?**
No, it complements it. The index is small and read every session; the vault is large and searched on demand. See [Claude memory system](09-claude-memory-system.md) for the other side of the same coin.

**Do I actually need the Obsidian application installed?**
Not necessarily. The "vault" is just a Markdown folder with a convention — the Obsidian application is a pleasant way to browse it visually, but the access mechanism that matters here is the MCP server, not the app.

**Which MCP server should I use?**
We deliberately do not recommend a specific one — search for "obsidian" in an MCP registry and confirm that your chosen server supports mandatory frontmatter and templates if you want this exact pattern.

**What happens to the daily log after compilation?**
Follow the project's retention policy. Only clean up after verified lessons are saved and read back; an unfinished handoff remains available.
