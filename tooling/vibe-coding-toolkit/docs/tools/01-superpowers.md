# Superpowers

> [!IMPORTANT]
> If you adopt only **one** tool from this entire repository, make it this one. The rest of the toolkit — subagent orchestration, token proxies, engineering personas, lint quality gates — optimizes *how* work gets done. Superpowers changes *when* and *whether* work should even begin: it turns the AI agent from an executor that starts coding at the first plausible interpretation of your request into a disciplined partner that questions, plans, delegates, and verifies before writing the first line of code. Everything else in this repository assumes that habit is already in place.

## What it is

`superpowers` is a Claude Code plugin — an installable package that adds **skills** (named workflows the agent can invoke on demand). It bundles a library of **process skills**: reusable workflows for every real stage of building software — exploring the intent behind a request, planning, implementing, debugging, reviewing, and finishing a branch.

This differs from an *implementation* skill, which teaches a specific technology or API ("how to use React Router," "how to structure a migration"). Process skills sit **above** implementation skills: they decide when and how to approach a task before any domain-specific skill decides what to write. That extra layer — deciding *whether* coding can begin yet — is missing from most AI workflows, and it is exactly what this plugin addresses.

Source: [`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official).

## Installation

Inside a Claude Code session:

```text
/plugin marketplace add anthropics/claude-plugins-official
/plugin install superpowers@claude-plugins-official
```

No additional configuration. From then on, the `using-superpowers` skill — the central rule described next — loads automatically at the beginning of every conversation, and the other skills are available for the agent to invoke on demand.

## The central rule

One skill runs underneath all the others: `using-superpowers`. It loads at the beginning of every conversation and defines a single rule, treated as nonnegotiable in the skill's own text:

> If there is even a 1% chance that a skill applies to what you are doing, you must invoke it — **before any response or action**, including clarification questions, code exploration, or file checks.

This reverses the seemingly natural order. The instinct is: understand the request, ask a clarification question if needed, *then* find a tool. Superpowers runs the process skill first — usually `brainstorming` for anything creative — and clarification questions happen *inside* it, not before. Answering, or even just asking, before invoking the skill is precisely the failure mode this rule exists to prevent.

### Process skills come before implementation skills

When more than one skill applies, the one deciding the approach comes first:

- "Let's build X" → `brainstorming` first, implementation skills afterward.
- "Fix this bug" → `systematic-debugging` first, domain skills afterward.

### The "red flags" — thoughts where the agent talks itself into skipping the rule

The skill includes a table of common rationalizations, because "it's just a simple question" is exactly the kind of thinking that skips the step that would prevent rework later. A sample from the original:

| Thought | Why it is a trap |
|---|---|
| "This is just a simple question" | Questions are tasks. Check whether a skill applies. |
| "I need more context first" | The skill check comes BEFORE clarification questions. |
| "Let me explore the code first" | Skills tell you HOW to explore. Check before exploring. |
| "This doesn't need a formal skill" | If the skill exists, use it. |
| "I remember this skill" | Skills evolve. Read the current version. |
| "The skill is overkill for this" | Simple things become complex. Use it anyway. |

An important caveat, also from the skill's original text: your explicit instructions — the project's `CLAUDE.md` or a direct request such as "skip brainstorming, just do X" — take precedence over skills. The rule prevents the agent from skipping the step **on its own**, not from leaving you the final decision. We return to this in the frequently asked questions at the end of this document.

## The six essential skills

These skills form the core cycle — from a loose idea to tested code. For each: what it does, when it activates, and a concrete example. The examples revolve around the same fictional scenario — a generic online store — so you can follow one story from start to finish.

### `brainstorming`

**What it does:** leads a Socratic exploration — focused questions, one at a time, in the style of Socrates' teaching through questions — of the intent, requirements, and design behind a request, **before** any creative work begins. "Creative" here includes creating a feature, building a component, adding functionality, or changing existing behavior.

**When it activates:** every such request first goes through a three-path classification, which the agent states aloud so you can correct it:

- **Spike** — a feasibility question ("can we do X?"). The result is an answer, not permanent code.
- **Bounded** — a well-defined change to a flow that **already exists** in the code: a new flag, a small endpoint, a one-file fix.
- **Architectural** — a new project, new subsystem, or any change restructuring how the pieces fit together.

When uncertain between two paths, the skill says to choose the heavier one. Adjustment goes one way: hidden complexity discovered mid-task escalates the path — never downgrades it.

The detail most people miss: **all** three paths have an approval gate (the skill calls it a *hard gate*). No code, no scaffold, no implementation skill is invoked before you hear what the agent intends to do and give an explicit "yes." Only the ceremony's size changes between paths — two chat sentences for bounded work, a full design document saved to disk for architectural work — approval itself is never optional.

**Practical example.** Request: "add a notification system to the app."

Without the skill, an "executor" agent would start writing a notification service with email, push, and in-app all at once — the obvious options — and probably build at least one incorrectly because it never asked about the actual requirement.

With the skill:

```text
Agent: This is a new subsystem, so I'll treat it as architectural — I'll
ask a few questions before proposing a design.

First question: which notification channels matter now — email,
push, in-app, or more than one?

You: just in-app for now.

Agent: Understood. Second question: does it need to be real time (the
notification appears without reloading the page), or would a counter that
updates on the next page load suffice?

You: real time would be ideal.

Agent: Third: what volume do you expect — dozens of notifications per
day, or thousands per minute at peak times?
```

Only after this sequence — never more than one question per message — does the skill propose 2 to 3 approaches with their advantages and disadvantages (for example: simple *polling* every N seconds vs. a stream through *Server-Sent Events*, SSE, a one-way HTTP channel from server to browser vs. a full WebSocket), recommend one, present the design in individually approved sections, and only then write a design document (spec). The skill stops there — literally stops without touching code — until you approve that document in writing.

### `writing-plans`

**What it does:** turns an already approved specification into a step-by-step, verifiable implementation plan, assuming whoever executes it — possibly a subagent with no project context — knows nothing about your code or testing best practices.

**When it activates:** immediately after `brainstorming` finishes the architectural path, or whenever a multistep requirement already exists before touching code. Never before an approved design exists.

Mechanics worth knowing:

- Every plan starts with a fixed header: a one-sentence Goal, the architecture in 2–3 sentences, the technical stack, the path to the spec document the plan implements, and a **global constraints** section (rules applying to every task — minimum library version, naming convention, etc.).
- Each task lists the exact files it creates or modifies, interfaces consumed from previous tasks and produced for subsequent ones, and "bite-sized" steps: 2 to 5 minutes each — "write the failing test," "run and confirm it fails," "implement the minimum," "run and confirm it passes," "commit."
- An explicit **zero-placeholder** rule: phrases such as "add appropriate error handling," "similar to Task 3," or a test described in prose without actual code are considered plan failures, not details to resolve later. Each step must include the actual content the implementer will use.
- Before delivery, the skill reviews itself: does it cover the entire spec? Are there hidden placeholders? Do function and type names used in later tasks match those defined earlier?

**Practical example.** Continuing the notification system: with the design approved (in-app, real-time through SSE, low volume), `writing-plans` generates a file such as `docs/superpowers/plans/2026-08-14-in-app-notifications.md`, with tasks in this format:

```text
### Task 3: Notification SSE endpoint

**Files:**
- Create: `src/routes/notifications/stream.ts`
- Test: `tests/routes/notifications-stream.test.ts`

**Interfaces:**
- Consumes: `NotificationService.subscribe(userId): AsyncIterable<Notification>` (Task 2)
- Produces: `GET /notifications/stream` route, emits `notification` SSE events

- [ ] Step 1: write the failing test (connect, publish a
      notification for the user, wait to receive the SSE event)
- [ ] Step 2: run and confirm it fails because the route does not exist
- [ ] Step 3: implement the minimal route passing the test
- [ ] Step 4: run and confirm it passes
- [ ] Step 5: commit
```

None of these lines is a summary — the actual plan includes the test body, exact function signature, and exact file path. Whoever implements Task 3 need not guess any of those details.

> Ready-made prompt covering exactly this transition from a loose idea to a formal plan: [Brainstorm to plan](../prompts/04-brainstorm-to-plan.md).

### `subagent-driven-development`

**What it does:** executes a plan by dispatching an implementer **subagent** — a separate agent instance that does not inherit the current conversation history and receives only the context you choose to pass — for each task under a fixed contract: if the task is ambiguous, the subagent asks **before** writing any code; implements using TDD (the next skill in this list); self-reviews before reporting; and returns one of four explicit statuses — `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED` — never a free-form summary.

**When it activates:** after a written plan exists and you decide to execute it in the current session. (The alternative, `executing-plans`, runs in a separate session with human review pauses between tasks — see the supporting skills section.)

Important detail: the skill defaults to **serial** execution — one implementer at a time, never two in parallel — because two subagents editing the same file simultaneously can interfere, and two concurrent commits can corrupt git history. After a subagent finishes and reports, the orchestrator dispatches a *second* subagent — a task reviewer — checking two mandatory things: the task matches the specification, **and** code quality is adequate. Only both approvals together complete the task; otherwise a correction loop begins with a bounded number of attempts before escalating the decision to you. After all tasks, a final review examines the entire branch.

> [!TIP]
> This serial pattern is the skill's *default*, not a physical law — multiple **genuinely independent** tasks can run safely in parallel, provided no two touch the same file and no implementer commits independently. This is exactly what [Subagent orchestration](02-subagent-orchestration.md) describes as "wave execution," automated by the ready-made [Parallel wave dispatch](../prompts/05-parallel-wave-dispatch.md) prompt.

**Practical example:**

```text
[Task 2 of the notification plan: NotificationService.send()]

Implementer subagent: Before starting — if delivery fails (a user
without configured preferences, for example), should the function throw an
exception or return a typed error result?

You: return a typed result — { ok: false, reason: string }.

Subagent: [implements through TDD, runs tests, self-reviews, finds
and fixes a missing case — a user with notifications disabled in
preferences — and commits]

Status: DONE. 6/6 tests passing. Nothing outstanding.

[Orchestrator dispatches a task-reviewer subagent]

Reviewer: Spec ✅ — all Task 2 requirements met. Quality:
approved. No findings.

[Task 2: complete. Next task.]
```

If the implementer subagent had become stuck ("I need more context about X"), the orchestrator would answer and redispatch it — never force a stuck subagent to retry without changing anything.

### `dispatching-parallel-agents`

**What it does:** when 2 or more genuinely independent problems exist — no shared state, neither depending on the other's order — dispatches a subagent for each **in the same message** instead of investigating or implementing one at a time.

**When it activates:** the skill's canonical case is investigation: several disconnected failures (different test files, different subsystems) after a large change. It also applies to any pair of independent tasks outside that case — but when tasks are steps in **the same** implementation plan, the more specific pattern is "wave execution," described above under `subagent-driven-development` and detailed in [Subagent orchestration](02-subagent-orchestration.md).

**Practical example.** After a large checkout refactor, three test suites turn red simultaneously in unrelated files:

```text
tests/cart/discount-calculation.test.ts   — 2 failures
tests/checkout/payment-flow.test.ts       — 1 failure
tests/orders/history-pagination.test.ts   — 3 failures
```

Investigating them one by one wastes time because fixing discount calculations has no effect on order-history pagination. The skill dispatches all three at once, each with its own scope, context, and constraints:

```text
Subagent 1: "Fix the 2 failures in discount-calculation.test.ts. Do not
change any other file. Return: root cause + what changed."
Subagent 2: "Fix the failure in payment-flow.test.ts. [same rules]"
Subagent 3: "Fix the 3 failures in history-pagination.test.ts. [same rules]"
```

All three calls go out in the same response — this defines "parallel" here: more than one dispatch in the same message runs concurrently; one dispatch per message runs serially even if the problems are independent. When all three return, the orchestrator reads all three summaries, checks whether any changed another's files, and only then runs the full suite.

### `systematic-debugging`

**What it does:** evidence-based **root-cause** investigation — the actual source of a problem, not where its symptom appears — before proposing any fix. The rule the skill's own text calls its "iron law": **no fixes without root-cause investigation first.**

**When it activates:** any bug, failing test, or unexpected behavior — especially under time pressure, precisely when "just change this line and test" becomes most tempting.

The actual mechanics, in four mandatory phases, in this order:

1. **Root-cause investigation** — read the entire error message (not just the first line), reproduce the problem reliably, check recent changes (`git log`, `git diff`), and — in multilayer systems — instrument **every boundary** between components with logging to see exactly where the expected value becomes wrong instead of guessing the guilty layer.
2. **Pattern analysis** — compare against a similar working example; list every difference, however small it seems.
3. **Hypothesis and minimal test** — one hypothesis at a time ("I think the cause is X because Y"), the smallest possible change to test it, never two changes simultaneously.
4. **Implementation** — only now write a test reproducing the bug (handoff to `test-driven-development`), fix the root cause — never the symptom — and verify.

If three consecutive fixes fail, the skill says to **stop** and question the architecture instead of trying a fourth: three failed attempts usually mean the problem is not where you are looking.

**Practical example.** Report: "the cart total is sometimes wrong after applying a discount coupon."

Without the skill, the agent would see the discount-calculation line, think it understood the problem, change rounding, and deliver — never confirming that this was actually the cause.

With the skill:

```text
Agent: I'll reproduce it before changing anything.
[Reproduces: happens only when the user changes an item's quantity
AFTER applying the coupon.]

I'll check recent changes in the discount area.
[git log --oneline -- src/cart/discount.ts, last 30 days]

The system has 3 layers here — cart service, discount engine,
price formatter. I'll log the value at every boundary to find where
it becomes wrong instead of guessing the layer.
[Runs once with temporary logging]

Finding: the value enters the discount engine correctly, but LEAVES with the discount applied
twice. Hypothesis: the cart recalculates the discount from scratch on every quantity
change but never removes the previous discount before recalculating.

[Makes the smallest possible change to test the hypothesis, confirms, ONLY THEN
writes the regression test and fixes the source: cart
recalculation, not the discount engine.]
```

The final fix lands on a very different line than the initial "guess" would have changed — and comes with a test protecting that specific scenario permanently.

### `test-driven-development`

**What it does:** the classic *red-green-refactor* cycle: write the test first (red — it **must** fail), the minimal implementation making it pass (green), then improve the code while keeping tests passing (refactor). The skill's iron law: **no production code without a test that failed first.**

**When it activates:** every new feature and bug fix, before writing any implementation code — including within each task dispatched by `subagent-driven-development`.

The detail commonly skipped: after writing the test, run it and **confirm it fails for the right reason** — "function does not exist" or "wrong result," never a typo or configuration error. A test passing on its first run proves nothing: you never saw it fail, so you do not know whether it tests the right thing. If implementation code was accidentally written before the test, the rule is literal: delete it and start over. Do not "adapt it while writing the test afterward" or keep it "as a reference."

**Practical example.** The `applyDiscountCode()` function in the same fictional store:

```javascript
// RED — write first, run, confirm failure
test('applies a 10% discount with a valid coupon', () => {
  const cart = { items: [{ price: 100 }], total: 100 };
  const result = applyDiscountCode(cart, 'SAVE10');
  expect(result.total).toBe(90);
});
// Run: FAIL — applyDiscountCode is not defined. Correct reason.

// GREEN — minimal passing implementation
function applyDiscountCode(cart, code) {
  if (code === 'SAVE10') {
    return { ...cart, total: cart.total * 0.9 };
  }
  return cart;
}
// Run: PASS.

// REFACTOR — only after green, without changing behavior
// (e.g., extract the coupon table into a separate object)
```

Without the skill, the reverse order is common: implement `applyDiscountCode` already covering several coupons and edge cases "just in case," write a test afterward just for a glance, and never actually know whether that test would catch a regression.

## The rest of the cast: supporting skills

The six above cover the heart of the cycle — from idea to tested code. The seven below cover the rest of the lifecycle: isolating work, finishing a task, giving and receiving reviews, and maintaining the skill library itself. Less individual prominence, but each closes a gap that would otherwise become a silent bad habit.

| Skill | Lifecycle role |
|---|---|
| `using-git-worktrees` | Isolates work in a *worktree* — a second working copy of the same git repository in another folder on its own branch — before implementation begins, so it never dirties your existing branch. |
| `executing-plans` | The alternative to `subagent-driven-development` when subagents are unavailable or you want to run the plan in a separate session with a human review pause between tasks instead of continuous execution. |
| `requesting-code-review` | Dispatches a reviewer subagent with precise context (never the entire session history) after each task, a major feature, or before merging — catches problems before they spread. |
| `receiving-code-review` | How to process review feedback: read everything, restate the requirement in your own words, check against the actual code, and only then agree or disagree technically — never an automatic "you're absolutely right!" or blind implementation. |
| `finishing-a-development-branch` | After tests are green: runs the full suite, detects whether you are in a worktree, presents actual options (local merge / push + PR / keep as is), and cleans the workspace — never discards work without explicit, literal confirmation. |
| `verification-before-completion` | The final brake: no "done," "fixed," or "tests pass" claim without running the verification command **in that same turn** and reading the actual output. "It should work now" does not count. |
| `writing-skills` | The skill writing other skills — literally TDD applied to process documentation: write a pressure scenario, observe an agent fail without the skill, write the skill, confirm it now obeys. This is how the skill catalog itself evolves. |

## From vague request to code: a chained example

The sections above show each skill individually. In practice they chain together within **one** request without you manually invoking anything — the central rule (`using-superpowers`) decides what runs next. Reconstructing the fictional store example from start to finish:

**1. Request:** "add a notification system to the app."

**2. `brainstorming` takes over before any response.** Classifies it as architectural (new subsystem), asks questions one at a time (channel, real time, volume), proposes SSE instead of polling or a full WebSocket, presents the design in sections, writes `docs/superpowers/specs/2026-08-14-notifications-design.md`, and stops — literally stops without touching code — until you approve in writing.

**3. You approve. `writing-plans` takes over.** Turns the approved spec into `docs/superpowers/plans/2026-08-14-in-app-notifications.md`: a header with goal, architecture, and global constraints, and bite-sized tasks — notification-table migration, `NotificationService`, SSE endpoint, frontend notification-bell component — each with exact files and tests containing actual code, without placeholders. At the end, it asks: subagent execution or inline in this same session?

**4. You choose subagents. `subagent-driven-development` takes over.** One implementer per task, each following `test-driven-development` internally (test first, run, see failure, implement the minimum, rerun, commit), self-reviewing before reporting. Two tasks — the database migration and the text for a sample transactional email — neither depend on each other nor touch the same files: this is where [Subagent orchestration](02-subagent-orchestration.md)'s wave execution dispatches both together instead of waiting for one to finish. Each task passes through a reviewer subagent (spec + quality) before being marked complete.

**5. If a bug appeared along the way** — say the unread notification counter falls out of sync after marking one as read — `systematic-debugging` would take over before any fix: reproduce, check recent changes, instrument boundaries between service and component, one hypothesis at a time.

**6. After the final task, final review, and `finishing-a-development-branch` takes over.** The full suite runs green, the skill detects an isolated worktree, and asks: local merge, push + PR, or keep as is?

Six skills, one chain, zero manual "which tool now?" decisions from you along the way. For a more complete example — including how this fits into the rest of the repository's workflow — see the [Onboarding playbook](../02-playbook-onboarding.md).

## Tips and best practices

**When it is appropriate to skip a skill.** Strictly, according to `using-superpowers` itself, the answer is "never, if it applies" — but "applies" is measured by `brainstorming`'s classification (spike / bounded / architectural), which exists precisely to scale ceremony to task size. A one-line fix in an already read and understood area is **bounded**: a couple of questions, a two-sentence design in chat, approval, implement — never a 300-word spec document. The common mistake is forcing a small task onto the architectural path (too much ceremony) or calling something bounded when it actually restructures an interface other system parts depend on (too little ceremony). Your project should formalize objective criteria for genuinely trivial work in its `CLAUDE.md` (file count, whether an existing flow is available to change) so the agent does not keep reclassifying the same kind of task.

**Combining with subagent orchestration.** `subagent-driven-development` decides **what** each subagent does and under which contract (ask first, TDD, self-review, explicit status) — but defaults to one implementer at a time, serially. [Subagent orchestration](02-subagent-orchestration.md) decides **how many** run simultaneously: tasks with entirely disjoint files and no mutual dependencies can run in parallel "waves," provided no subagent commits independently — the orchestrator does that after the whole wave ends. The two layers complement rather than compete: neither replaces the other's contract.

**Model selection.** Preserve the authorized main model and authentication. Without an authorized selection policy, pass the session model in supported delegation. With such a policy, choose capability by task and risk according to the [orchestration guide](02-subagent-orchestration.md#part-b--model-selection-discipline). A skill example does not authorize a provider switch or API billing. Process skills also respect user instructions, including direct execution and approvals already granted.

**Process skills do not replace implementation skills — they precede them.** After `brainstorming` approves a component design, for example, the stack-specific patterns skill still decides implementation details. `using-superpowers` only ensures the order never reverses.

## Frequently asked questions

**Does this make everything slower?**
For a trivial task, if you unnecessarily force the architectural path, yes. But the spike/bounded/architectural classification exists exactly to avoid that — a bounded fix costs a couple of questions and two design sentences, not a spec document. Time the skill "spends" asking is usually less than time lost implementing the wrong interpretation of an ambiguous request or discovering two weeks later a bug whose root cause was never actually investigated.

**Does it work for small tasks too?**
Yes — that is literally why the **bounded** path exists: quick context, the questions that actually matter, a few-sentence design in chat, approval, implement. No spec document, no formal plan. The skill is never all-or-nothing.

**Can I disable a specific skill?**
The plugin has no "turn off just this skill" button. What exists, explicitly in `using-superpowers` itself, is a priority hierarchy: your direct instructions — a project's `CLAUDE.md` or an explicit request such as "skip brainstorming, just implement this" — take precedence over any skill. The rule prevents the agent from skipping a step on its own, not from leaving you the final say. To disable it permanently, uninstall the entire plugin.

**What if I simply ask the agent to code directly without the process?**
That works — and differs from the agent deciding to skip the step on its own. Your explicit request is the highest-priority instruction in the system; the skill only covers cases where nobody said anything and the agent would go directly to code on its own.

**Does Superpowers conflict with Ponytail or Caveman?**
No — they are independent layers solving different problems. Superpowers decides **when** to stop to ask, plan, and verify. [Ponytail](04-ponytail.md) decides **what** to build once implementation is underway (the minimum that solves the problem, without speculative abstraction). [Caveman](05-caveman.md) decides only **how** the agent talks about what it did. All three compose well because none governs another's territory — see [Overview](../00-overview.md) for how the toolkit pieces fit together.
