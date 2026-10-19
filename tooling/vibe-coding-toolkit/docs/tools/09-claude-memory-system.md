# Claude memory system

## What it is

A lightweight, file-based pattern for giving an AI agent persistent memory
between sessions: no database or external service, just files the agent
reads at the start of each session and writes occasionally. It sits at the
opposite end of the complexity spectrum from the *vault* (a collection of
Markdown notes organized using a folder convention) described in
[08-obsidian-memory.md](08-obsidian-memory.md). Here there is no MCP server
(*Model Context Protocol*, a standardized way to expose external tools to
an agent), no graph of relationships between notes, and no PARA structure
(Projects / Areas / Resources / Archives, a note organization convention).
Just a small index file and a folder of topic files.

## Why use it

Most things an agent could remember are not worth remembering: they can be
rediscovered by reading the code. What matters is the small set of things
that were expensive to learn the first time: a mistake requiring several
corrections, an architectural choice that only makes sense when you know
what was tried and rejected, or a business rule the code never states
explicitly.

A memory system should capture precisely that narrow slice, cheaply enough
to be maintained, rather than fall into either of two opposite traps:
saving nothing, or saving everything until the index becomes too large to
be worth loading.

## Portable storage and freshness

Use the active client's native memory when available, or the repository's
existing documentation. The Claude-oriented paths below are examples, not
portable auto-loading guarantees: verify the client's supported loading
mechanism. Do not add a vault, MCP server, or dependency just to save memory.

Durable memory records a reusable lesson. A task handoff records the current
objective, changed files, checks, blockers, and next step; keep it in the task
record and retire it when the task ends. Promote only verified durable lessons.

Every durable entry records its source, supporting evidence (a decision,
reproduction, or check), last verified date, and an invalidation condition.
Before relying on it, compare those with current code and instructions. A
changed contract or contradicted source makes the entry stale: reverify and
update it, or mark it superseded so it no longer guides work. Never invent
verification dates or evidence, and never store credentials or private dumps.

## Structure

- **`MEMORY.md`**: an index file always loaded at session start, one line per
  entry. Keep it short: a *soft cap* (a warning threshold rather than a hard
  error) of about 130 lines prevents its mere existence from bloating every
  session's context.
- **Topic files**: one small file per memory, with *frontmatter* (the
  metadata block at the top of a Markdown file, between `---` lines):

```markdown
---
name: kebab-case-slug
description: one-line summary used to determine relevance in future sessions
metadata:
  type: feedback | architecture | business-rule | reference
source: path, decision record, or approved reference
evidence: observation or check supporting this lesson
last_verified: YYYY-MM-DD
invalidate_when: contract, dependency, or decision that would change this fact
---

The fact or rule itself, why it matters, and when it applies.
```

`name` follows *kebab-case*: a *slug* (a short, readable identifier usually
derived from the title), with lowercase words separated by hyphens. `type`
is a small, fixed set; do not invent new categories:

- **`feedback`**: a mistake requiring correction during a session.
- **`architecture`**: a pattern discovered only after failed attempts.
- **`business-rule`**: something affecting the code that is not obvious
  from reading it.
- **`reference`**: where external information lives (a dashboard, wiki,
  or ticket system).

## Saving criterion

Before writing a new entry, apply this literal test, word for word:

> Would a future session be surprised and grateful to know this before
> starting?

If not, do not save it. This test explicitly excludes:

- Anything derivable from the code or Git history alone.
- Deadlines, motivations, or other temporary context from the current
  moment.
- Debugging steps or fix recipes: these already belong in the commit
  message.
- Anything documented elsewhere in the project's own instructions.

Err on the side of not saving. An unnecessary memory is noise; relearning
a lesson the hard way is expensive, but a small, high-signal index always
beats a large, ignored one.

## Growth policy

When the index exceeds the cap, low-value entries are not simply deleted:
they **migrate** to long-term storage (a vault, wiki, documentation folder,
or whatever the project already uses for long notes), in a fixed sequence,
without skipping any step:

1. **Check for duplicates**: search long-term storage for the same topic;
   extend an existing note instead of creating a duplicate.
2. **Adapt to the destination's required format**: long-term storage often
   has its own mandatory template or frontmatter; find and follow it
   exactly.
3. **Create** the entry in long-term storage.
4. **Confirm**: read the newly created entry back. Without confirmed
   read-back, migration has not happened.
5. **Only then**, delete the short-term file and its line in `MEMORY.md`.

Never jump directly to step 5. An unconfirmed migration is data loss rather
than relocation: the entry exists nowhere until someone notices the
mistake. When unsure whether an entry still deserves its place in the fast
index, leave it there. Migrating later costs nothing, but a lesson lost
from both locations is expensive to relearn.

## The generalizable idea

Long-term storage can be Obsidian (see
[08-obsidian-memory.md](08-obsidian-memory.md)), a wiki, or a plain
documentation folder. The generalizable part is the two-layer design: a
cheap, always-loaded index for information worth surfacing automatically
now, and a deliberate, confirmed promotion path to unlimited long-term
storage when something earns a permanent place. The fast layer remains
small by design; the long-term layer has no size limit because it never
loads automatically.

## Tutorial — setting up from scratch

1. **Create the folder and index file.** Choose a memory folder, such as
   `.claude/memory/` or your tool's equivalent, and create an empty
   `MEMORY.md` with a title explaining its purpose.
2. **Write usage rules in a separate file**, such as `INSTRUCTIONS.md` in
   the same folder: saving criteria, frontmatter format, and growth policy.
   Load it automatically at every session start through an `@import` in
   `CLAUDE.md` or your tool's equivalent mechanism. Otherwise someone must
   remember to open the file manually, and memory requiring manual
   reminders is not automatic memory.
3. **Apply the saving criterion to a real case.** Suppose the agent spent
   considerable time investigating silent image upload failures, eventually
   discovering an undocumented size limit in an intermediate proxy. Apply
   the literal test: would a future session be surprised and grateful to
   know this before starting? Yes: no comment documents it, and reading the
   code does not make it obvious. It deserves an entry.
4. **Write the topic file.** Create
   `.claude/memory/image-upload-limit.md` with complete frontmatter (`name`,
   `description`, `type: architecture`, source, evidence, last verified date,
   and invalidation condition in this case), and a body
   explaining the fact, why it matters, and when it applies.
5. **Add one index line.** In `MEMORY.md`:
   `- [Image upload limit](image-upload-limit.md) — the proxy silently drops uploads above X without returning an error`.
6. **Before the next entry, check the index size.** Count nonempty lines in
   `MEMORY.md`. Below the cap (about 130 lines), simply add the entry.
   Above it, apply the growth policy first: migrate lower-value entries to
   long-term storage through the five-step sequence before writing the
   new entry.

A ready-made prompt avoids setting this up manually each time: see
[Memory bootstrap](../prompts/06-memory-bootstrap.md), which applies these
steps in a new project or an existing project without memory.

## Examples — good and bad entries

These illustrative bodies show the saving criterion; a real saved entry must
also include the provenance and freshness fields above.

### Bad — derived from the code itself

```markdown
---
name: project-uses-nextjs
description: the project uses Next.js and React
metadata:
  type: reference
---

This project is built with Next.js and React.
```

Fails the test: opening `package.json` reveals this in five seconds. It was
not expensive to learn, and a future session is neither surprised nor
grateful; it simply wastes time reading an entry teaching nothing new.

### Good — a business rule implicit in the code

```markdown
---
name: coupon-cannot-stack-with-first-purchase
description: discount coupons cannot combine with the first-purchase promotional discount
metadata:
  type: business-rule
---

The price calculator applies only one discount per order: if both a coupon
AND the first-purchase discount are eligible, the larger one wins; they
never add together. No comment or type documents this rule, only an `if`
in the total calculation function. A new discount type must explicitly
check this exclusion, or the final total silently becomes incorrect.
```

Passes the test: function signatures do not make this obvious, and learning
it the hard way through a customer's complaint about an incorrect total
costs much more than reading a memory entry.

### Bad — a deadline and temporary context

```markdown
---
name: run-tests-before-friday
description: run tests before Friday because the customer demo is Monday
metadata:
  type: feedback
---

Run the complete test suite before Friday because the customer demo is
scheduled for Monday morning.
```

Fails: this is a specific deadline at a specific moment, rather than a
durable lesson. In two weeks, it means nothing and only occupies index
space.

### Good — a mistake repeatedly corrected during the session

```markdown
---
name: form-field-needs-shared-validation
description: every new form field also needs validation in the shared schema
metadata:
  type: feedback
---

When adding a form field, the agent forgot the corresponding validation
rule in `shared/validation/*.ts`, the file used by both client and server,
three times in the same session before the user corrected it. Always
check this file when changing form fields, even if the original request
only mentions the screen.
```

Passes: the mistake already required three manual corrections, exactly the
kind of friction a memory entry should prevent in the next session.

### Bad — a debugging recipe

```markdown
---
name: how-i-fixed-the-login-bug
description: restarting the dev server and clearing cache fixes the login bug
metadata:
  type: feedback
---

Fixing the development login bug only required restarting the dev server
and deleting the local cache folder.
```

Fails: this is a fix recipe for one symptom, the kind of information that
already belongs, or should belong, in the fixing commit's message. It is
an isolated operational step rather than a lesson about the system.

### Good — an architectural pattern discovered after a failed attempt

```markdown
---
name: coupon-validation-is-intentionally-synchronous
description: checkout coupon validation is synchronous by design rather than leftover old code
metadata:
  type: architecture
---

The checkout coupon-validation call is synchronous, blocking the response
until the validation service responds. This was deliberate, rather than
an unoptimized version forgotten in place. An earlier asynchronous
implementation allowed an order to be marked paid before coupon
validation returned, accepting an invalid coupon. A future attempt to
make this nonblocking for speed would reopen that bug.
```

Passes: this decision can look naive from outside (“why does this block the
response?”) but only makes sense with knowledge of previous failures: the
classic `architecture` entry.

### Bad — already documented elsewhere in the project

```markdown
---
name: how-to-run-tests
description: the command to run the test suite is npm run test
metadata:
  type: reference
---

The command to run all project tests is `npm run test`.
```

Fails: this is already, or should be, in the project's
`CLAUDE.md`/`README.md` command section. Duplication only creates two
sources of truth that can drift apart.

### Good — where external information lives

```markdown
---
name: postmortems-live-in-notion
description: production incident reports live in a Notion database rather than this repository
metadata:
  type: reference
---

Production incident postmortems (post-incident analyses) are written in
the team's Notion database, not anywhere in this repository. Before
assuming a production incident was never investigated, search there.
```

Passes: this information exists nowhere in the code, and a new session
could not guess it independently.

## Tips and pitfalls

- **The ~130-line cap is a maintenance trigger, not a hard error.** Do not
  wait until 300 lines to start migrating. The later cleanup happens, the
  larger the batch of entries requiring decisions.
- **`type` has only four values; resist inventing another.** An entry that
  fits none of them may not belong in memory at all.
- **An entry merely repeating a commit message is a code smell**, a sign
  of poor structure. The commit message already serves that purpose; the
  index does not need to duplicate history.
- **Never delete before confirming read-back during migration.** If the
  session is interrupted between creating the new note and deleting the
  old one, recoverability depends on never deleting first.
- **Write for a future session, rather than your current self.** A fact
  you will obviously remember in five minutes does not need a permanent
  entry; one a fresh agent with no history could not guess does.
- **The `description` line is the only part read automatically every
  day.** If it is vague (`"a note about the backend"`), the index loses its
  purpose. Give it more care than the topic file's body.

## Frequently asked questions

**Does this replace a database or vector search system (embeddings)?**
No, deliberately. It is plain Markdown, without infrastructure to maintain,
a running service, or cost beyond disk space. That simplicity makes it
work even in small projects.

**What if I do not have an Obsidian-like vault for older entries?**
Long-term storage can be anything you can search, create in, and read back:
a wiki, a normal documentation folder, or even a second larger Markdown
file. What matters is the migration sequence: check duplicates → adapt the
format → create → confirm → only then delete, rather than the chosen tool.

**Who decides what becomes a memory entry?**
The agent applies the literal test, ideally without reminders. A person
can also simply ask “save this” during a session.

**Must I read all of `MEMORY.md` every session?**
Yes, by design: the index exists to be small enough to read completely
every day without burdening context. That size constraint is the reason
for the ~130-line cap.

**Can an entry have more than one `type`?**
No: choose the best fit. If a fact truly spans two types, such as both a
business rule and an external reference, it usually indicates two entries
rather than one.
