# Caveman

## What it is

Caveman is a plugin — a package that extends the agent's behavior
inside Claude Code — for communication compression: it cuts filler
words, rhetorical hedging (phrases such as "maybe," "it could be,"
"possibly," which soften an answer without adding new information),
and excessive formality from the agent's own prose. It does not change the code
the agent writes, only how it talks about that code.

It is independent of and combinable with [Ponytail](04-ponytail.md): Ponytail governs
what gets built; Caveman governs how the agent talks about it. You can use
either alone or both together. Source: [`JuliusBrussee/caveman`](https://github.com/JuliusBrussee/caveman).

## Why use it

By default, agent prose tends to be padded with phrases like "I'll
go ahead and...", "It seems this could potentially...", "Great
question!" — none changes what was actually done. This costs reading
time and tokens (the units measuring how much text enters and leaves the model,
usually with an associated cost) without delivering anything extra. The
plugin's own repository claims a reduction of up to 65% in a conversation's
token usage through this style compression alone.

Caveman removes padding without removing information: numbers, units,
code, and exact error-message text pass through unchanged. The
compression is in style, never content.

## How to install/activate

Inside a Claude Code session:

```bash
/plugin marketplace add JuliusBrussee/caveman
/plugin install caveman@caveman
```

The first command registers the GitHub repository as a plugin source; the
second installs the `caveman` plugin from it.

Once installed, intensity can be adjusted with `/caveman` in Claude Code or the corresponding skill in the client. In Codex, use `$caveman` or the name discovered in the skill list. To persist the preference, incorporate the rule into `AGENTS.md` or `CLAUDE.md` without replacing existing instructions.

The [official project](https://github.com/JuliusBrussee/caveman) also distributes a CLI, proxy, and Cloud features. Communication skills can be used separately. In this toolkit's setup, preserve the session's native client, model, and authentication for Caveman LLM work. In Codex, keep ChatGPT login when used; in Claude, preserve its authentication mode. Do not enable routing, another provider, or API billing as a side effect of installation.

For skill and plugin discovery in Codex, see the [client guide](15-codex-workflow.md). Configure each agent separately and avoid copying skills already provided by another distribution.

## Step-by-step tutorial

### 1. What gets cut

Filler words, rhetorical hedging, and formality — the part of an
answer that exists to sound polite or cautious but carries no
information that would be missing without it. Examples: "I'll check that for
you," "it seems that maybe," "no problem!", "excellent observation."

### 2. What is never touched

Four categories always stay outside compression:

- **Negation and restriction words** — not, never, none, only, except. Cutting one
  would reverse the sentence's actual meaning, so compression does not even try.
- **Numbers and units.**
- **Code and exact error text.**
- **The language the user is using.** Caveman compresses style, never
  language — if the conversation is in Portuguese, the compressed answer stays in
  Portuguese.

Text persisted outside the conversation must also use normal wording: documentation, code comments, commits, and PR descriptions. When the user requests a full explanation, clarity and completeness take precedence over compression.

### 3. The automatic clarity override

Compression turns itself off in three situations, because clarity matters
more than brevity there:

- safety warnings;
- confirmations before irreversible actions;
- anywhere compressing a sentence would create technical ambiguity.

This is not a manual exception to remember — it is automatic, built into
the plugin itself.

### 4. Adjusting intensity and persisting the rule in the repository

`/caveman` changes the compression level for the current session,
independently of Ponytail's equivalent command (`/ponytail
lite|full|ultra`) — each plugin has its own intensity control.
To keep activation beyond the current session, incorporate this into the instruction file loaded by the client:

```markdown
- Caveman active by default: concise conversation in the user's requested language, preserving clarity.
- Full explanations when requested; normal wording for code, documentation, and commits.
- “stop caveman” disables the style in this conversation.
```

Use the [`AGENTS.md` template](../../templates/AGENTS.md.template) as a starting point. Do not depend on an initialization command absent from the installed version.

### 5. Complementary commands

- **`/caveman-commit`** — generates a direct commit message without
  filler.
- **`/caveman-review`** — code review comments in one line
  each.
- **`/caveman-stats`** — observed session counters, when available. This does not prove how much Caveman saved; runtime measurements must be identified separately.

The names above are client commands/skills, not shell executables. In Codex, use the discovered skill with `$name`, which may include a namespace.

### 6. Measure usage without inventing savings

In native Codex, use current-session counters when the client exposes them. If they are unavailable, report that limitation; do not choose another session's log because it is the newest.

Distinguish observed usage, per-tool text reduction, and savings measured against a comparable run. Cumulative counters must not be added again at each update. Promotional percentages do not measure your session, and tokens on a ChatGPT subscription do not automatically equate to dollar charges.

## Concrete examples

### Example 1 — everyday prose

**User request:** "Why is this test failing?"

**Without Caveman:**

> Great question! Let me take a look at that for you. It seems it could
> be because, possibly, the mock is not returning the expected value
> in this particular scenario. I'll look more closely and let you know what
> I find.

**With Caveman active:**

> Mock returns `undefined`; test expects `42`.

Same cause, zero filler words — and the exact value (`42`) and the
technical term (`undefined`) pass through intact, because numbers and code
are never compressed.

### Example 2 — why negation is never cut

**User request:** "Explain why this function must not be called
twice in a row, except in tests."

**Without Caveman:**

> Good question! This function, generally speaking, should not be called twice
> in a row — this can, in certain situations, cause unexpected
> behavior. That said, in tests, it is usually fine.

**With Caveman active:**

> Do not call twice in a row — only safe in tests.

"Not" and "only" survive untouched because they carry the sentence's entire
meaning; cutting either would reverse the rule instead of merely
shortening it. Everything around them — "good question," "generally speaking," "that said,
usually" — is filler and disappears.

### Example 3 — when compression turns itself off

**User request:** "Delete the `orders` table from the database."

Deleting a table is irreversible — the automatic clarity override
kicks in, and the confirmation stays complete even with Caveman at
high intensity:

**With Caveman active:**

> This will permanently delete the `orders` table and all its data —
> it cannot be undone. Do you confirm you want to continue?

It does not become "Delete orders, no undo, confirm?" The message stays explicit
because this is precisely the category — confirmation before an
irreversible action — where Caveman decides clarity matters more than saving
words.

## Tips and pitfalls

- **An answer that is "too short" in an irreversible-action confirmation or safety
  warning is not expected behavior.** If it happens, it indicates a
  bug — the clarity override should have kept the sentence complete.
- **Numbers, code, and error text that change between the "raw" and
  compressed versions are also bugs, not style.** These elements are guaranteed
  to stay intact, always.
- **It combines with [Ponytail](04-ponytail.md), but solves a different
  problem.** Ponytail decides how much code is written; Caveman decides
  how many words describe it. Using both compresses along
  both axes without creating ambiguity in either.
- **Persistence depends on loaded instructions.** A preference in `AGENTS.md` or `CLAUDE.md` must be checked in a new session. Plugin installation and persistent configuration are separate checks.
- **Language never changes with intensity level.** Increasing compression
  does not change the answer's language — it only cuts excess around the
  information.

## Frequently asked questions

**Does Caveman make the agent answer in English even if I write in
Portuguese?**
No — it compresses style, never changes language. The answer stays in the
language you are using.

**Will I lose numbers, code, or error text because of compression?**
No. These elements pass through unchanged at every intensity
level.

**What if I request confirmation before an action that cannot be
undone?**
The automatic clarity override turns off compression in that specific
case — the message stays complete and unambiguous.

**Do Caveman and Ponytail do the same thing?**
No. [Ponytail](04-ponytail.md) decides what gets built; Caveman decides
how the agent talks about what was built. They are independent plugins that
combine.

**Do I need to choose a level every session?**
No. `/caveman` adjusts it whenever you want, and the level applies to the current session;
to keep it active by default in the repository, record the preference in the instruction file loaded by the client and check it in a new session.
