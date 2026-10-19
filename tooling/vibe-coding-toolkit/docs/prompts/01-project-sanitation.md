# Project sanitation

## When to use

Use this prompt for a general "clean up this code" pass: dead code,
forgotten `TODO`/`FIXME` comments, dependencies nobody imports anymore.
The central idea is an agent that **measures before acting**, instead of
guessing each problem's severity or silently taking risks on its own.
For large codebases, combine it with [parallel dispatch of specialist
subagents](../tools/02-subagent-orchestration.md) instead of running the
whole prompt through a single agent.

## Why it works

The logic separates **measuring** from **acting**. Every claim about the
code's state — warning counts, whether the build passes, how many
dependencies are unused — must come from a real command run now, never an
estimate or a number remembered from an earlier run. On that factual
foundation, the prompt separates safe mechanical fixes (which can proceed
without asking) from decisions requiring human judgment — for example,
"is this export really unused, or does it only look that way because it is
consumed through reflection or dynamic imports?" — with the conservative
option as the default if nobody responds. Finally, it requires small,
verifiable execution steps, each proven by a real check, instead of one
huge diff (the comparison between two versions of the code) mixing ten
unrelated fixes that become impossible to review confidently.

## How to adapt the placeholders

- **`[LINT_COMMAND]`** — the command that runs the project's linter (e.g.
  `npm run lint`, `ruff check .`, `golangci-lint run`).
- **`[TYPECHECK_COMMAND]`** — the command that runs type checking (e.g.
  `npm run typecheck`, `tsc --noEmit`, `mypy .`).
- **`[TEST_COMMAND]`** — the command that runs the test suite (e.g.
  `npm test`, `pytest`, `go test ./...`).
- **`[BUILD_COMMAND]`** — the command that compiles/builds the project (e.g.
  `npm run build`, `make build`).
- **`[DEPENDENCY_AUDIT_COMMAND]`** — the command that audits dependencies
  for unused packages or vulnerabilities (e.g. `npm audit`,
  `npx depcheck`, `pip-audit`).
- **`[PACKAGE_MANIFEST]`** — the file declaring the project's dependencies
  (e.g. `package.json`, `requirements.txt`, `go.mod`).
- **`[STACK/FRAMEWORK]`** — a short stack description (e.g. "Next.js +
  TypeScript", "Django + Python 3.12").
- **`[ROOT_PATH]`** — the root path where the agent should operate. Useful
  for restricting the pass to a particular package in a monorepo.

## The prompt

```
You are doing a codebase sanitation pass. Goal: leave the repo measurably
cleaner without changing behavior, and without guessing at the current state.

## 0. Ground truth — run these now, don't estimate
- Lint: `[LINT_COMMAND]`
- Typecheck: `[TYPECHECK_COMMAND]`
- Tests: `[TEST_COMMAND]`
- Build: `[BUILD_COMMAND]`
- Dependency audit: `[DEPENDENCY_AUDIT_COMMAND]`

Report the literal output of each — pass/fail counts, warning counts,
vulnerability counts. This is the baseline everything below is measured
against. If any of these are already failing, say so before doing anything
else; don't layer cleanup on top of a broken baseline.

## 1. Inventory — find, don't fix yet
- Dead code: unused exports, unreachable branches, orphaned files.
- `TODO` / `FIXME` / `XXX` markers, with file:line and enough context to
  judge whether they're stale or still real.
- Unused dependencies declared in [PACKAGE_MANIFEST] but never imported.
- Anything the Step 0 commands already flagged before you touched a thing.

## 2. Prioritized plan — safe default vs. needs sign-off
Split findings into:
1. **Safe / conservative (default if I don't respond).** Mechanical and
   behavior-preserving only: unused imports, files with zero references,
   TODOs that reference already-resolved work.
2. **Needs my sign-off before you touch it.** Anything where "unused" is
   ambiguous (reflection, dynamic imports, public API surface), any
   dependency removal that might be a transitive/peer requirement, and any
   TODO documenting a real known gap.
3. **Out of scope — note only.** Architectural debt, anything not already
   surfaced by Step 0.

Present the plan and wait for a decision on group 2. If I don't respond,
proceed with group 1 only.

## 3. Execute in small, verifiable steps
One item at a time — never a bundle of unrelated cleanups in one diff.
After each change, re-run the specific check that proves it, the actual
command, not the full suite from memory. Move to the next item only once
the current one is verified.

## 4. Final report
Re-run every Step 0 command once more and show before/after numbers side
by side. Never write "fixed" or "cleaned up" without the command output
that proves it.

Codebase: [STACK/FRAMEWORK], root at [ROOT_PATH].
```

## Usage example

Imagine inheriting the backend of a task management app — a Node.js/Express
API with TypeScript that grew for two years without a systematic cleanup.
You would fill in the placeholders like this:

- `[LINT_COMMAND]` → `npm run lint`
- `[TYPECHECK_COMMAND]` → `npm run typecheck`
- `[TEST_COMMAND]` → `npm test`
- `[BUILD_COMMAND]` → `npm run build`
- `[DEPENDENCY_AUDIT_COMMAND]` → `npx depcheck`
- `[PACKAGE_MANIFEST]` → `package.json`
- `[STACK/FRAMEWORK]` → "Node.js + Express + TypeScript"
- `[ROOT_PATH]` → `/apps/api` (for a monorepo with multiple packages)

When run, the agent first executes the five commands from step 0 and reports
the real numbers — for example, "14 lint warnings, build passing, 3 unused
dependencies, 0 vulnerabilities". It then lists the inventory: exports never
imported, a handful of two-year-old `TODO`s, and the 3 unused dependencies.
The prioritized plan splits these into group 1 (remove unused imports,
delete an orphaned utility file) and group 2 — for example, an apparently
unused dependency actually required as a peer dependency (a package the
dependency itself expects the host project to provide) by another package,
or a `TODO` documenting a real limitation worth keeping. You approve or
correct group 2, the agent executes item by item, confirming each check
before continuing, and the final report shows before/after side by side
(e.g. "14 → 2 warnings", "3 → 0 unused dependencies").

## Tips

- In a large codebase, split the inventory in step 1 and execution in step
  3 among specialist subagents by directory or domain, instead of having
  one agent process everything in sequence.
- Run step 0 again, from scratch, whenever reporting a number — a value
  remembered from earlier in the session is the most common way that number
  drifts away from reality.
- Group 2 is the core of the exercise; resist putting a "probably safe"
  item into group 1 just because deletion looks easy.
