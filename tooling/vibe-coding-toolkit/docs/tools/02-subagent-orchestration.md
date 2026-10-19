# Subagent orchestration

## What it is

Not a plugin or something you install — it is a **pattern** (a recurring
way to solve a problem that you reapply whenever it
appears) you build into your project's own instructions (a
`CLAUDE.md`, `AGENTS.md`, or equivalent file your AI tool
loads automatically). When delegation pays off, define
specialist agent **roles** with narrow scopes and one-line descriptions
of when to use each. Select roles by task;
a persistent roster only makes sense for proven recurring
needs. Delegable tasks are routed to the appropriate specialist
when the client and chosen workflow support that execution.

A subagent here is a separate AI agent instance — dispatched
(launched) solely to handle a specific task, with its own context,
reporting back to whoever dispatched it when finished.

## Why use it

A generalist agent re-derives the right checklist for each domain every time
it encounters it: what to check in a *migration* (a script changing the
database structure), which vulnerability classes matter in an
authentication change, which *hook* rules (special React functions
such as `useState` and `useEffect` providing access to framework
features inside a component) a component might violate. A
specialist already knows its domain checklist because that is all
it does.

The gain is not "more agents for vanity" — every dispatch arrives with
the right checklist for that domain, instead of a generalist reinventing
the wheel under time pressure every single time.

## Part A — specialist roster and routing table

Give each specialist a name and a "when to use" sentence. That sentence has
a dual role: it also serves as the routing rule. There is no
separate "task type → specialist" table to keep synchronized
with this one — both would be the same mapping read in different
directions. A representative roster looks like this:

| Specialist | When to use |
|---|---|
| `orchestrator` | Coordinates work spanning several domains, delegating to other specialists — the first to invoke when a task crosses layers (e.g., backend + frontend together). |
| `code-reviewer` | General review of any code change — bugs, error handling, test coverage. |
| `security-reviewer` | OWASP-class vulnerabilities (the organization maintaining the reference list of common web application security flaws), secrets committed to source code, authentication failures, CVEs (public identifiers for known vulnerabilities) in dependencies. |
| `typescript-reviewer` | Type safety, async code correctness, injection risk, *prototype pollution* (a flaw allowing an attacker to alter properties shared by all JavaScript objects) in TS/JS. |
| `react-reviewer` | React *hook* rules, server/client component boundaries, accessibility, rendering performance. |
| `react-build-resolver` | Broken *build* (packaging code to run in production) or development server — *bundler* configuration (the tool packaging code for browsers), compilation errors, missing types. |
| `test-engineer` | Unit and integration tests, written *test-first* (the test before implementation), covering edge cases. |
| `qa-automation-engineer` | End-to-end tests (simulating a real user browsing) and CI/CD (continuous integration and delivery — automated build, test, and deploy pipelines) *quality gates* (automated quality barriers) for a critical user flow. |
| `database-architect` | *Schema* design (database table structure), *migrations*, indexes, query strategy. |
| `devops-engineer` | Deployment, CI/CD pipelines, infrastructure, production operations. |
| `backend-specialist` | API *endpoints* (entry points, each associated with a URL), server business logic, data persistence. |
| `frontend-specialist` | UI components, layout, styling, frontend architecture. |
| `seo-specialist` | Metadata, structured data (special HTML markup helping search engines understand page content), search engine indexing, visibility in AI searches. |
| `performance-optimizer` | A bottleneck already identified through *profiling* (performance measurement) — slow endpoint, high memory usage, poor Core Web Vitals (Google metrics for a page's actual loading and response experience). |
| `product-manager` | Undefined or ambiguous requirements, before a *story* (a small, deliverable work item) even exists. |
| `product-owner` | Turns a business goal into acceptance criteria for a *story*. |
| `project-planner` | Breaks a *feature* or *epic* (a large set of related features) into ordered, executable tasks. |
| `code-archaeologist` | Understands legacy or undocumented code before changing it. |
| `debugger` | Finds the root cause of a bug, crash, or flaky test — before proposing any fix. |
| `explorer-agent` | Maps an unfamiliar or complex codebase before planning a change. |
| `documentation-writer` | READMEs, API documentation, *runbooks* (step-by-step operational guides) — written or updated on request. |
| `penetration-tester` | Simulated attack techniques against a real authentication flow or release. |
| `security-auditor` | Defense-in-depth review (multiple redundant protection layers so one failure does not bring everything down) and threat modeling before an important release. |

The names are illustrative — use whatever makes sense in your project.
What matters is the shape: narrow scope, a clear usage trigger, and zero
overlap with neighboring table entries. If two specialists in your roster
cover the same trigger, one is redundant.

This covers the usage **pattern** — building the roster and routing tasks
to it. The technical **mechanism** declaring an actual subagent (the
`.claude/agents/*.md` file, precedence determining which model tier each
dispatch uses, isolation through `isolation: worktree`) is covered by the
[official Claude Code subagent documentation](https://code.claude.com/docs/en/sub-agents) —
it does not duplicate this document; it is the technical foundation on which this
pattern is built.

<a id="part-b--model-selection-discipline"></a>

## Part B — model and authentication

Preserve the authorized native client, main model, and authentication. **Without an authorized selection policy, subagents use the session model.** Installing a tool does not grant permission to change models, providers, or billing modes.

The user can authorize a task-based selection policy without choosing every model by name. The [existing-project prompt](../prompts/12-existing-project-setup.md) grants this authorization within the current provider and authentication, respecting explicit restrictions. It does not authorize changing the main agent, installing a proxy, configuring API billing, or contradicting an existing model restriction.

### Choose capability at dispatch time

Discover the models and reasoning efforts actually available on the host. With authorized selection, prefer the lightest model able to meet acceptance criteria, considering complexity, ambiguity, risk, and review effort. Check the client's current recommendations; do not hardcode commercial names in portable instructions.

| Work | Capability guidance |
|---|---|
| Targeted search, inventory, links, log reading, and small mechanical changes | Lightweight capability with verifiable output |
| Bounded implementation, contracts, and behavior review | Enough capability for the scope's reasoning and checks |
| Architecture, authorization, security, migrations, concurrency, or ambiguous causes | Greater capability when the required judgment warrants it; do not downgrade solely for price |

Select model and effort explicitly through supported controls. If the host only supports inheritance or agent configuration, follow the documented mechanism and record the limitation; do not invent parameters. Poor understanding or low quality calls for diagnosis and possible escalation, not indefinite repetition on a cheap model. Respect finite time, attempt, and resource limits defined for the task.

This choice follows the guidance on [models and reasoning in Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) and [model selection for Claude Code costs](https://code.claude.com/docs/en/costs). Concrete mechanisms vary by client and version. This toolkit's tables are decision criteria, not benchmarks or savings promises.

### Context, tools, and integration

Use direct execution or deterministic tools when they solve the task with less coordination. Delegate to isolate context, use specialization, or execute independent parts. The names in Part A are illustrative roles, not automatically installed agents.

Each briefing includes the objective, necessary context, applicable instructions, files, dependencies, mutable resources (ports, build directories, test databases, and services), acceptance criteria, and checks. Prefer clean context over copying the entire conversation. Request a short report with paths, findings, evidence, and limitations. Grant only necessary tools/permissions; a read-only reviewer does not implicitly become a writer. [Claude Code subagent best practices](https://code.claude.com/docs/en/sub-agents) document this isolation.

The coordinator checks the diff and validates integration. Lockfiles, shared configuration, the ledger, and Git operations have a single owner. Control concurrency using the host's actual resources and limits; do not create agent trees without clear benefits. Record observed models/efforts without estimating tokens or savings when no measurements exist.

## Review after implementation or fixes

Choose review scope from the changed contracts, risk, and unresolved evidence.
There is no universal minimum of 3–8 cycles. A small documentation change may
need one focused consistency check; security or data changes may need distinct
specialist reviews and integration checks. Respect any review count explicitly
requested by the user; internal fixes do not restart that count.

Before dispatch, freeze the target: exact base and head commits, or an explicit
working-tree snapshot including staged, unstaged, and relevant untracked files.
Reviewers inspect the diff plus connected callers, contracts, and tests. They
remain read-only: no automatic fixes, commits, or publishing. The coordinator
deduplicates findings by root cause and verifies evidence before reporting.

Define the stop condition before review: the requested scope and rounds are
covered, findings have evidence and disposition, and relevant checks are
reported. Continue beyond that only for a newly identified risk or user request;
report residual uncertainty instead of manufacturing more rounds. Suggest
additional review only when a concrete gap justifies it. Fixes require existing
or explicit authorization; review alone does not authorize implementation.

## Recovering an interrupted run

A worker's failure does not complete the coordinator's scope. Confirm that the agent stopped before taking over its files, inspect partial changes, and resume from the verified point. If state remains uncertain, preserve ownership of those files and advance only independent work. Do not repeat the same attempt without new evidence; respect gates and limits. The [playbook](../02-playbook-onboarding.md#execution-continuity) collects these agreements and evaluation scenarios, also available in the shared-instructions template.

## Before waves: deciding how to split tasks

Everything Part C teaches — marking `Files:`, `Depends-on:`, and `Resources:`, grouping into
waves, serializing commits — starts from a question it does not
answer: who decides where to split work into tasks? That
decision happens **before** wave mechanics, not after the plan is already
assembled.

Anthropic's official post
[Multi-Agent Systems: When to Use Them](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them)
(Jan/2026) addresses exactly this question, with a finding worth citing
directly: running multiple agents costs **3 to 10 times more tokens** than
one agent solving the same task alone. That cost only pays off
in three scenarios — outside them, multi-agent execution is expense without return:

- **Context protection** — isolate something that would create substantial noise in
  the main context (a large investigation, verbose output) in a
  separate instance instead of polluting the coordinator's
  context window.
- **Real parallelization** — genuinely independent work that can run
  simultaneously without one task waiting for another's result.
- **Genuine specialization** — the task requires a checklist, context, or
  instruction set a generalist agent does not carry by
  default.

The post's central principle: decompose along **isolatable context
boundaries** — what each task *needs to know* to do its
own work without depending on any other task's complete
context — not by problem type or work phase.

The post explicitly names the most common anti-patterns in this decision —
worth knowing by name because they are easy to fall into unnoticed:

- **Problem-centered decomposition** — splitting by topic ("one
  agent for the database, one for frontend, one for security") instead of actual
  context boundaries.
- **Sequential phase splitting** — planning, implementation, and testing as
  **separate** agents when all three actually share the same
  working context and should be one unit — or at least not
  pretend to have independence that does not exist.
- Separating **tightly coupled components** merely because they are,
  technically, "two parts."
- Work depending on **mutable shared state** — if one
  task needs to read what another is writing *while* it writes,
  they are not independent tasks; they are one task pretending to be
  two.

This is a layer **preceding and complementing** Part C's wave execution,
not replacing it: the post helps decide **how to
split** work into tasks that each justify existing
alone; Part C teaches **how to execute** those tasks
once split — disjoint files, independent mutable resources, no
cross-dependencies, commits always serialized by the orchestrator. One
question does not replace the other; the second only makes sense after the
first is answered.

## Part C — execution in parallel waves

This is the part worth reading carefully, because mistakes here are
exactly how you create the bug this pattern exists to prevent.

### The problem

The safe default for executing a plan is **serial dispatch**: one
implementer, one task, one commit (a record of a change in Git
history), then the next. It is correct — and slow for genuinely
independent work. Three bug fixes in three completely unrelated
files do not need to wait for each other.

The naive solution — dispatch every task's implementer simultaneously
— is fast and risky: two agents may edit the same file at the same
time and one overwrite the other's work unnoticed, or both may
race to run `git commit` first.

### The solution

Three parts reduce these coordination risks:

1. **Annotate each planned task** with the exact file paths it
   touches, the other tasks it depends on, and `Resources:` identifying
   ports, build directories, test databases, and services used by checks. A task without these
   annotations — or with any real uncertainty about its scope — is
   treated by safety default as depending on **everything**. This is
   the pattern's safety net: an underspecified task does not become a
   false-parallelism risk; it simply degrades to normal serial
   execution.
2. **Two tasks enter the same wave only if all conditions hold
   simultaneously**: neither depends on the other, even transitively (that
   is, through a third task along the way); **and** the
   sets of files they touch are completely disjoint, with no shared
   files; **and** mutable resources are independent or explicitly isolated.
   If any condition fails or is uncertain, serialize the affected work.
   Disjoint source files alone do not isolate builds or test services.
3. **Implementers within a wave never commit on their own.** They
   edit files and report changes; when commits are authorized, the orchestrator makes them
   afterward, one per task in wave order, capturing the current
   `HEAD` (Git's pointer to the branch's latest commit) immediately before
   each commit — never an old or predetermined reference. This
   eliminates commit contention entirely: there is only one
   agent committing, and it acts serially even when editing
   happened in parallel.

### Per-wave execution loop

1. Write an instruction file for each task in the wave.
2. Dispatch all wave implementers **in a single message** — this
   is the only point where actual parallelism happens.
3. Wait for everyone to finish.
4. When authorized, make commits in order, one per task, capturing the current
   `HEAD` immediately before each commit. Otherwise record working-tree snapshots
   for review; do not require a commit to continue.
5. Dispatch reviewers against each task's exact before/after range and connected
   code. Reviewers remain read-only. Run them together only when any checks use
   independent mutable resources; isolate or serialize shared builds, ports,
   databases, and services. Review does not authorize fixes or commits.
6. Make exactly **one** tracking entry per wave (a log, a
   progress spreadsheet), never one per task — two agents competing to
   write the same tracking file is the same class of bug as
   two agents competing to commit.

### Escape hatch: worktree isolation

When tasks collide, serialize or combine them first. Optional isolation can
justify parallelism when its benefit outweighs setup cost: use a separate Git
*worktree* (a parallel repository copy in a separate folder, synchronized
with the same history) and its own *branch*. This makes independent
commits safe again because there is no shared index left to
contend over.

Worktrees do not isolate ports, databases, or external services. Allocate those
separately or serialize their checks. A branch name alone is not an isolated
working directory; neither branches nor worktrees are required for this pattern.

### What changes (and what does not)

This pattern only changes **orchestration**. The contract between implementer and
reviewer remains exactly the discipline described in
[01-superpowers.md](01-superpowers.md) (specifically the
`subagent-driven-development` skill): ask first if the task is ambiguous,
TDD (*test-driven development* — write the test before implementation),
self-review before reporting, and a final status from a small
set of explicit options. Waves do not loosen that contract — they only
allow multiple instances to run simultaneously when it is
proven safe.

See
[`templates/rules/parallel-subagent-driven-development.md`](../../templates/rules/parallel-subagent-driven-development.md)
for this same reasoning already written as a literal rule, ready
to paste into project instructions. And see [Parallel wave
dispatch](../prompts/05-parallel-wave-dispatch.md) for a ready-made *prompt*
(instruction text you give the agent) applying this entire
workflow to a real plan.

## Tutorial — building the pattern from scratch

This is the step-by-step process for building the whole pattern in your own
project, starting from scratch.

1. **Identify work deserving delegation.** Do not copy Part A's roster
   word for word. Select roles for actual tasks benefiting from
   isolation, specialization, or parallelism; having a database or
   frontend does not require creating an agent for each domain.
2. **Write each one's "when to use" sentence.** One objective line,
   without overlap with the others. This sentence is the routing table — do not
   write a separate table.
3. **Document only proven recurring roles.** When needed,
   maintain a short table in the instructions or a document they
   reference. One-off roles stay in task briefings;
   do not load a whole team into every session.
4. **Define the capability policy.** Without authorized selection, preserve the session model; with authorization, choose capability by task and risk according to Part B. Specify model and effort through supported controls, preserving the client, authentication, and explicit restrictions.

The pattern is now assembled — steps 5 through 8 cover
using it in a real plan by applying Part C's wave execution:

5. **List the current plan's tasks.** For each: a short ID (`T01`,
   `T02`...), a one-line description, and the responsible specialist.
6. **Annotate `Files:`, `Depends-on:`, and `Resources:` on every task.** Be exact about
   file paths — when in doubt, list more files, not fewer. Any
   real uncertainty becomes `Depends-on: everything listed so far`.
7. **Group tasks into waves**, applying all conditions from the
   previous section: no dependencies (even transitive ones) and fully
   disjoint files and independent mutable resources. Show the result as a table: wave number, its tasks,
   each task's specialist.
8. **Execute wave by wave**, following Part C's loop: dispatch the
   wave's implementers in one message, wait for all, commit
   in order, dispatch its reviewers together, record progress
   once, and move to the next wave.

## Examples

### Example 1 — discount coupon in an e-commerce app

A team receives a request to add a discount coupon to the cart and
includes two old, unrelated bugs already
in the backlog:

| ID | Description | Files: | Depends-on: | Specialist |
|---|---|---|---|---|
| T01 | Create the `coupons` table (migration + schema) | `db/schema/coupons.ts`, `db/migrations/0007_coupons.sql` | none | `database-architect` |
| T02 | Endpoint validating and applying the coupon to the cart | `src/server/coupons/apply-coupon.ts`, `src/app/api/coupons/apply/route.ts` | T01 | `backend-specialist` |
| T03 | Coupon field on the checkout screen | `src/components/checkout/CouponField.tsx` | T02 | `frontend-specialist` |
| T04 | Fix broken date formatting in order history | `src/components/orders/OrderDate.tsx` | none | `frontend-specialist` |
| T05 | Fix broken pagination in the admin user list | `src/app/admin/users/page.tsx` | none | `frontend-specialist` |

Assume each task has independent build output, ports, and test data; otherwise
serialize those checks. Applying the conditions:

- **Wave 1 — T01, T04, T05.** None depends on anything, and the three
  file sets have nothing in common — even though T04 and T05 belong to the
  same domain (frontend) and specialist, they touch different
  files and resources, so they go together.
- **Wave 2 — T02, alone.** Depends on T01 already being committed — the table
  must exist before the endpoint tries to use it. No other
  dependency-free task remains to accompany it, and that is fine: a
  single-task wave is the correct result when the rule yields it,
  not a system failure.
- **Wave 3 — T03, alone.** Depends on T02 — the checkout field needs to
  know the actual API response shape before being implemented
  against it.

Notice what the annotations prevented: T04 and T05 look like "just two frontend
bugs," the kind of tasks tempting to mix directly into
other frontend work (T03). But T03 has an actual dependency
(T02), while T04 and T05 do not — the annotations, not the intuition that "they
belong to the same specialist," decide where each goes.

### Example 2 — three bug tickets for a blog

Three tickets arrive on the same day for a blogging platform:

| ID | Description | Files: | Depends-on: |
|---|---|---|---|
| T01 | Loading spinner never disappears on the tag-filter page | `src/components/blog/TagFilter.tsx` | none |
| T02 | Author avatar looks blurry on the article page | `src/components/blog/ArticleHeader.tsx` | none |
| T03 | Align the "share" button with the new design system (the product's visual guide) | `src/components/blog/ArticleHeader.tsx`, `src/styles/share-button.css` | none |

Assume independent test/build resources for this example. None declares a dependency on another — at first glance all three seem
perfect candidates for one wave. But T02 and T03 touch the same
file, `ArticleHeader.tsx`. Lack of dependencies alone is insufficient;
file sets must also be disjoint, and here they are not.

- **Wave 1 — T01, T02.** No dependency between them, entirely different
  files.
- **Wave 2 — T03, alone.** Shares a file with T02, which ran in the
  previous wave.

An equally valid alternative here — and usually better when two
tickets happen to touch the same file — is simply merging T02
and T03 into one task before assembling waves, since one implementer
will change that file anyway. Separate waves and merged tasks
solve the same problem; merging even avoids an extra commit's cost.

## Tips and pitfalls

- **Vague `Files:` is the same as leaving it blank.** "Several frontend
  files" is not an annotation — it is a task that will (correctly)
  degrade to depending on everything. List actual paths.
- **Capturing `HEAD` only once at the start of the wave is the classic mistake.**
  Capture it again, on the spot, immediately before each commit — after the
  wave's first commit, the old `HEAD` is already outdated.
- **"Same file" disqualifies the wave even for different sections of that
  file.** Two agents editing different parts of the same file can still
  produce a broken merge or silent overwrite — the rule is
  per file, not per line.
- **Do not make an exception for "just this once, the implementer commits alone."** That is
  exactly how the *race condition* (two concurrent
  operations contending for the same resource, with the final result
  depending on which "wins") returns; the rule only works if
  it is absolute.
- **Model and authentication follow the authorized policy.** A specialist's name does not authorize changing providers or billing. Dynamic model selection requires a user-selected policy; without it, preserve the session model.
- **Worktree isolation is not free.** Each worktree usually needs
  dependencies installed and the environment configured again — use it only
  when the gained parallelism truly outweighs the cost.
- **Parallel reviewers are safe only while review stays read-only.**
  If your review process ever writes back to code
  (for example, independently applying an automatic lint fix), that
  part stops being read-only and requires serialization again.

## Frequently asked questions

**Is this a plugin I install?**
No. It is a pattern — a way to organize the instructions you already write
for your agent. There is no package to install; there is a table and some rules
to put in your `CLAUDE.md` (or equivalent).

**Do I need exactly these 23 specialists?**
No — Part A's roster is illustrative. Adapt it to your project's actual
domains; an agent for a domain you do not have is dead weight in the
table.

**What if I get the `Depends-on:` annotation wrong?**
An omitted dependency can cause a race or invalid result. If scope is uncertain,
serialize the task and inspect dependencies and resources before dispatch; the
fallback helps only when the uncertainty is recognized.

**Can I use this without Claude Code, with another AI tool?**
Yes. The pattern is tool-independent — what matters is an
instruction file the tool loads automatically and the
ability to dispatch more than one agent (or session) at a time.

**Is there a maximum number of tasks per wave?**
There is no universal number. First select tasks without dependencies and with
disjoint files and independent mutable resources; then cap concurrency at the host's authorized slots,
resources, and budget. A structurally valid wave may need to
run in smaller batches.

**Can reviewers in one wave disagree about neighboring tasks?**
Yes. Reviewers inspect connected callers and contracts, so findings may overlap.
The coordinator verifies evidence, deduplicates root causes, and checks whether
the overlap reveals a missed dependency before the next wave.
