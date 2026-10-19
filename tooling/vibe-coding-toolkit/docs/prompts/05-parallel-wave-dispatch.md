# Parallel wave dispatch

## When to use

Use this prompt when you already have a task list — from a plan, an epic
(a larger set of related tasks), or simply a batch of independent fixes —
and want to turn it into safe parallel execution waves (groups of tasks
running at the same time) instead of a single agent working through tasks
sequentially. It is the "fill in the blanks" version of the same pattern
in [subagent orchestration](../tools/02-subagent-orchestration.md) and the
[parallel dispatch rule template](../../templates/rules/parallel-subagent-driven-development.md).

## Why it works

Parallel waves require no cross-dependencies, disjoint writable files, and
independent mutable resources. Separate source files can still share a port,
build directory, test database, or service. Allocate independent resources or
serialize the affected work; this reduces known races, not every integration
risk. Implementers only edit and report changes. When commits are authorized,
the orchestrator alone commits, sequentially, capturing the current HEAD for
each task rather than reusing an earlier reference.

## How to adapt the placeholders

- **`[FEATURE/PLAN/TASK LIST]`** — appears twice: on the first line (what to
  split into waves) and the last ("Plan/task list:"). Paste your task list,
  plan or epic there; if it is long, repeat just a name or short summary
  the second time instead of the entire text.
- **`[BACKEND_ROLE]`, `[FRONTEND_ROLE]`, `[DB_ROLE]`, `[TEST_ROLE]`** — merely
  example roles/specialists for each task's `Owner:` field. Replace them
  with the actual specialist agent names in your project (if you use
  Claude Code with an agent table in `CLAUDE.md`, use exactly those names
  so `Owner:` already points to the right agent to dispatch). Add or remove
  roles as needed — the prompt itself says to use "whatever roles this
  project defines".

## The prompt

```
Break [FEATURE/PLAN/TASK LIST] into parallel execution waves. Follow this
exactly — the safety of running multiple agents at once depends on the
rules below, not on judgment calls made in the moment.

## 1. List every task
For each unit of work, write:
- **ID** — short and stable (T01, T02, ...).
- **Description** — one line.
- **Files:** — every path/glob this task will create or modify. Be exact;
  when in doubt, list more rather than fewer.
- **Resources:** — ports, build directories, test databases, and services
  used by implementation or checks; state isolation or `none`.
- **Depends-on:** — task IDs whose output this task needs, or `none`.
- **Owner:** — the specialist role responsible (e.g. [BACKEND_ROLE],
  [FRONTEND_ROLE], [DB_ROLE], [TEST_ROLE] — use whatever roles this
  project defines).

Any task where `Files:`, `Resources:`, or `Depends-on:` is uncertain gets `Depends-on:
everything already listed` — that's the safe default, not a shortcut to
skip filling it in.

## 2. Group into waves
Two tasks go in the **same wave** only if ALL hold:
1. Neither depends on the other, directly or transitively.
2. Their `Files:` sets are completely disjoint — zero overlap.
3. Mutable resources are independent or explicitly isolated.

If any condition fails or is uncertain, put the dependent (or file-colliding) task in a later
wave. A task with no valid same-wave partner is simply a wave of one —
that's correct, not a failure of the grouping.

Show the result as a table: wave number, task IDs in it, owner per task.

## 3. Execute each wave, in order
For every wave:
1. **Dispatch every implementer in the wave in a single batch** — this is
   what makes it parallel instead of a string of sequential turns.
2. **Implementers do not commit.** They implement, verify their own work,
   and report exactly which files changed — and stop there.
3. **When commits are authorized, the orchestrator commits**, one task at a time, in a fixed order:
   right before each commit, capture the current HEAD fresh (never reuse a
   HEAD captured earlier, never assume `HEAD~1`), stage that task's files,
   commit.
4. **That wave's reviewers run together, after all its commits exist** —
   dispatch them in one batch too, each reviewing their task's own
   before/after range and connected callers, contracts, and tests. Reviewers
   remain read-only; serialize checks sharing mutable resources. Without commit
   authorization, use recorded working-tree snapshots instead.
5. Only once every task in the wave is verified and reviewed (and committed
   when authorized), move to
   the next wave.

Plan/task list: [FEATURE/PLAN/TASK LIST].
```

## Usage example

Imagine a small project with four queued tasks. The
`[FEATURE/PLAN/TASK LIST]` placeholder becomes this list, and generic roles
(`[BACKEND_ROLE]`, `[FRONTEND_ROLE]`, `[DB_ROLE]`) become actual project agents:

- **T01** — create the `reports` database table (migration). `Files:`
  `src/db/schema/reports.ts`, `drizzle/*`. `Depends-on:` none.
  `Owner:` database-architect.
- **T02** — endpoint exporting reports as CSV, reading the `reports` table.
  `Files:` `src/app/api/reports/export/route.ts`.
  `Depends-on:` T01. `Owner:` backend-specialist.
- **T03** — "Export CSV" button on the reports screen calling the new
  endpoint. `Files:` `src/components/reports/ExportButton.tsx`.
  `Depends-on:` T02. `Owner:` frontend-specialist.
- **T04** — fix a typo in the login screen text, unrelated to the other
  three. `Files:` `src/components/auth/LoginForm.tsx`. `Depends-on:` none.
  `Owner:` frontend-specialist.

This example assumes commits are authorized; otherwise use reviewed working-tree
snapshots at the same boundaries, without committing.

In Step 2, the agent builds the waves table: T01 and T04 belong in the
**same wave**, because neither depends on the other and their files do not
overlap, assuming independent resources for their checks. The owner alone
does not establish independence. Record the concrete resource allocation in
each task brief before dispatch.
T02 can only enter a wave after T01 is committed (wave 2), and T03 only
after T02 (wave 3) — even though T03 and T04 share no files, T03 cannot enter
wave 1 because it depends on T02, which does not yet exist.

In Step 3, wave 1 dispatches the T01 and T04 implementers together in one
batch; neither commits on their own, they only report changes. The
orchestrator commits T01 and then T04 (fixed order), capturing HEAD again
before each commit. T01 and T04 reviewers then run together. Only afterward
does wave 2 (T02 alone) start — followed finally by wave 3 (T03 alone).

## Tips

- When scope or resources are uncertain, serialize the task and inspect them.
  An unrecognized dependency can still cause a race.
- A fixed commit order per wave (not "whoever finishes first") keeps HEAD
  easy to track — capture it immediately before that specific task's
  commit, never earlier.
- When two tasks genuinely cannot avoid touching the same files, take it
  as a signal to combine them into one task or isolate each in a separate
  worktree (a parallel repository copy in another folder, isolated from
  the main one) — do not force both into the same wave. Serial execution is
  also valid. Worktrees are optional and do not isolate ports, databases,
  or external services.
