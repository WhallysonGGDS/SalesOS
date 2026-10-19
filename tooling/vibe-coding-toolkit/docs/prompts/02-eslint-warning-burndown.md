# ESLint warning burndown

## Shortcut: just the link

If you followed the sequence
[`08`](08-eslint-quality-gates-install.md) →
[`09`](09-file-size-refactor.md) and now want to clear the remaining warnings
(direct console use, misplaced data access, complexity budgets), paste this
line into your agent:

```
Read https://raw.githubusercontent.com/soumatheusgomes/vibe-coding-toolkit/main/docs/prompts/02-eslint-warning-burndown.md
and execute the prompt in that file in this project, for the entire set
of remaining warnings. Discover the lint, test, typecheck and build commands
by reading package.json yourself.
```

The rest of this document contains the same prompt in full, for those who
prefer to paste the entire text or choose one specific rule instead of the
whole set.

## When to use

If the project does not yet have a decent ESLint configuration, first use
one of the two configuration prompts:
[`08-eslint-quality-gates-install.md`](08-eslint-quality-gates-install.md)
(the shortcut — copy three ready-made rules and measure) or
[`07-eslint-complete-setup.md`](07-eslint-complete-setup.md) (the complete
version — the agent builds the config by reasoning about your stack). This
prompt comes afterward, when warnings from an existing configuration have
accumulated and it is time to clear them.

If the warnings you want to clear specifically concern **file size**, go
straight to [`09-file-size-refactor.md`](09-file-size-refactor.md): splitting
an 800-line file is different work from fixing 240 `complexity` warnings,
and that prompt is designed specifically for it.

Use this prompt when you have a large pile of lint warnings to clear — or
want to deliberately review and tighten a particular rule — without "just
fixing the warnings" silently becoming a major refactor. It was generalized
from a real warning burndown in which the costliest decision (how far to
pursue a rule in files not written with it in mind) needed an explicit human
answer before any code changed, rather than an assumption buried in an
implementation plan.

## Why it works

The logic turns implicit decisions into explicit ones, and claims into
commands. First, the prompt requires the real warning count now — never an
old number, because remembered counts drift from reality too quickly to
trust. Then it isolates the riskiest decision (how far to pursue the rule,
or whether simply loosening its scope makes more sense) in a numbered
**decision gate**, with explicit options and trade-offs — making clear that
"loosening the rule" is a configuration change, not code cleanup, so they
are never presented as the same thing. Success criteria become literal
commands instead of vague "should work" statements. Work is divided into
**waves** — groups of tasks with disjoint files, dispatched in parallel —
because a subagent only sees its own brief, never the entire planning
conversation; that is why the pitfalls list must be copied verbatim into
each one. And the final checklist is checked off only by running the
command again, never by assumption.

## How to adapt the placeholders

- **`[RULE_NAME]`** — the specific ESLint (or other linter) rule being cleared
  or reassessed — e.g. `no-unused-vars`, `complexity`, `max-lines`. If the
  burndown covers the entire warning set rather than one rule, say so
  explicitly — the prompt already supports this ("or the full warning set").
- **`[LINT_COMMAND]`** — the command that runs the linter with full output
  per file and rule. Note: some CI wrappers/proxies summarize output rather
  than displaying every line — the prompt already instructs the agent to
  use the flag or direct invocation that returns full output when needed.
- **`[TYPECHECK_COMMAND]`** — the type-checking command.
- **`[TEST_COMMAND]`** — the command that runs the test suite.
- **`[BUILD_COMMAND]`** — the build command.
- **`[STACK/FRAMEWORK]`** — a short stack description to give the agent context.

## The prompt

```
You are planning and executing a lint warning burn-down for [RULE_NAME] (or
the full warning set) in this repo. Do not start fixing anything until the
plan below is written and the decision gate in step 1 is answered.

## 0. Ground truth
Run `[LINT_COMMAND]` right now and report the actual current count — total
warnings, broken down by rule and by file. Do not reuse a number from an
earlier run, a commit message, or memory. If the output looks filtered or
truncated (some wrappers/proxies summarize instead of showing every line),
re-run with whatever flag or direct invocation gives full per-line output.

## 1. 🔴 Decision gate — answer before any implementation
Find the single riskiest or most expensive part of this burn-down — usually
one rule responsible for a large share of the count, concentrated in files
where "fixing" it is expensive or risky (e.g. a size cap tripped mainly in
generated or test files). State it with real numbers: file count, line
count, estimated new files/functions if applicable. Then present options:

- **(A) Fix every violation fully.** Default if there's no response — the
  fully-correct option is the safe assumption when scope wasn't explicitly
  narrowed.
- **(B) Fix most, track the rest as tracked debt.** Fix the cheap majority;
  leave the expensive tail as an explicit, visible exception (comment +
  issue/ticket reference), not a silent suppression.
- **(C) Re-scope or loosen the rule itself.** ⚠️ **This is a config change,
  not a warning fix — say so explicitly in the plan and in any PR. Never
  present it as if the code got cleaner.**

Wait for a decision before implementing anything in this area. Everything
outside the flagged risk area proceeds regardless of which option is picked.

## 2. Success criteria — commands, not prose
State every criterion as a command and its expected output, e.g.:
- `[LINT_COMMAND] shows 0 warnings for [RULE_NAME]`
- `[TYPECHECK_COMMAND]` clean
- `[TEST_COMMAND]` green
- **Zero behavior change.** Any fix that isn't a pure mechanical
  extraction/rename/move gets pulled out of this burn-down and flagged as
  its own item for separate human review — never folded in silently.

## 3. Break the work into waves
Group the remaining violations into ordered, file-disjoint waves. For each
task in each wave, specify: task ID, exact file scope (`Files:`), what it
depends on (`Depends-on:`, or "none"), and the specialist role that owns
it. Use the parallel wave dispatch worksheet (`05-parallel-wave-dispatch.md`
in this same folder) for the grouping rule and dispatch mechanics.

## 4. Pitfalls — copy verbatim into every task brief
List every concrete gotcha specific to this rule and this codebase — e.g. a
size cap with zero slack left in files already near the limit, a lint
cache that doesn't invalidate on config changes, an extraction that
silently widens an inferred type, a shared test fixture with many callers.
A subagent implementing one task sees only its own brief, never this
planning conversation — a pitfall not copied into the brief does not exist
for it.

## 5. Reviewer sign-off
For each wave, name every specialist reviewer required before that wave
counts as done — a domain-risk reviewer for anything security/money/auth-
adjacent, plus whatever language/framework reviewers match the files
changed. Before calling the whole burn-down complete, require a full-diff
pass by every relevant reviewer type, at the same rigor as a normal review,
not a lighter one just because it's "only" a lint fix.

## 6. Final checklist — mark only by re-running
Every box below is checked by an actually-executed command, never by
assertion:
- [ ] `[LINT_COMMAND]` shows 0 warnings for [RULE_NAME] (or the count
      agreed at the decision gate)
- [ ] `[TYPECHECK_COMMAND]` clean
- [ ] `[TEST_COMMAND]` green
- [ ] `[BUILD_COMMAND]` succeeds
- [ ] Every suppression added (`eslint-disable` or equivalent) is listed
      with its justification — or the list is empty
- [ ] Every non-mechanical fix pulled out under step 2 is listed and
      signed off — or the list is empty
- [ ] All reviewer sign-offs from step 5 are complete

Codebase: [STACK/FRAMEWORK]. Rule(s) in scope: [RULE_NAME].
```

## Usage example

Imagine a TypeScript monorepo where tightening ESLint's `complexity` rule
revealed 240 warnings across the project — 180 concentrated in six legacy
files with deeply nested conditionals. Fill it in as follows:

- `[RULE_NAME]` → `complexity`
- `[LINT_COMMAND]` → `npm run lint`
- `[TYPECHECK_COMMAND]` → `npm run typecheck`
- `[TEST_COMMAND]` → `npm run test`
- `[BUILD_COMMAND]` → `npm run build`
- `[STACK/FRAMEWORK]` → "Next.js + TypeScript monorepo"

The agent runs lint now and reports the real number (240, never from memory).
At the decision gate, it identifies the six legacy files as the expensive,
risky area, with real line and file counts, and presents the three options:
fix everything, fix most and track the rest as technical debt, or loosen
the rule's limit just for those six files (explicitly stating that this is
a config change, not code cleanup). Without your response, it assumes
option A by default and continues fixing the rest of the project while it
waits. Then it splits work into waves of disjoint files, with each known
pitfall copied into the brief (e.g. "this extraction must not change the
exported function's inferred return type"), runs specialist reviewers for
each wave, and only checks off the final checklist after actually rerunning
`[LINT_COMMAND]`, `[TYPECHECK_COMMAND]`, `[TEST_COMMAND]` and `[BUILD_COMMAND]`.

## Tips

- The decision gate in step 1 is the most tempting part to skip because it
  seems like a formality — in practice, it usually holds most of the work
  or real risk.
- Combine step 3 with
  [`05-parallel-wave-dispatch.md`](05-parallel-wave-dispatch.md) for real
  parallelism; without it, this degrades into one task at a time.
- Keep growing the pitfalls list from step 4 as you discover new ones
  during the burndown — a pitfall found in wave 2 also belongs in every
  wave from wave 3 onward.
