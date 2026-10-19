# Split the giant files revealed by the line ceiling

## Shortcut: just the link

After prompt 08 measures and gives you the list of files above the ceiling,
paste this line:

```
Read https://raw.githubusercontent.com/soumatheusgomes/vibe-coding-toolkit/main/docs/prompts/09-file-size-refactor.md
and execute the prompt in that file in this project. Use MAX_LINES=350,
BATCH_SIZE=3 and RULE_ID=quality/max-lines. Discover the lint, test and
typecheck commands by reading package.json yourself.
```

The rest of this document contains the same prompt in full.

## When to use

Use this prompt after the per-file size ceiling is installed and the linter
has identified the files exceeding it — usually right after
[`08-eslint-quality-gates-install.md`](08-eslint-quality-gates-install.md).
This is the second phase: 08 installs the ruler and measures; this prompt
tells the agent to take the files that did not fit and turn them into
smaller, isolated modules.

Do not use it for clearing lint warnings in general — that is
[`02-eslint-warning-burndown.md`](02-eslint-warning-burndown.md), which is
broader and works rule by rule. This prompt only concerns file size,
because splitting an 800-line file is different work from fixing 240
`complexity` warnings: every change here moves code between files, which
is where behavior changes hide.

## Why it works

The question that makes this work go wrong is always the same: *where to
cut*. An agent without guidance cuts where the line count dictates — takes
200 lines from the end, puts them in `utils.ts`, and produces two files
that only make sense when read together. The file passes lint and the code
gets worse.

That is why the prompt defines the split by responsibility, not line
number, using the same four seams the rule's own message suggests: business
logic becomes a domain service, repeated UI becomes a subcomponent, data
access becomes a repository, and a cluster of helpers becomes a domain
utility module. If none of these seams exists in the file, the instruction
is to say so and stop — inventing an abstraction just to satisfy the linter
trades a visible problem for an invisible one.

The second mechanism is pacing: **one file at a time, one commit per file**,
with tests and type checks between each. Splitting six files in one commit
means that when something breaks, you do not know which extraction caused
it. The third is preservation: the original file's public exports remain,
with the same names and signatures. Importers should not even know the
file was split.

Finally, the prompt requires the final count to come from rerunning the
command, never from mentally adding up what was done.

## How to adapt the placeholders

- **`[LINT_COMMAND]`** — the command that runs lint with full output per file
  and rule. Some CI wrappers summarize output; if yours does, invoke it
  directly.
- **`[TEST_COMMAND]`** — the test suite command.
- **`[TYPECHECK_COMMAND]`** — the type-checking command. For plain JavaScript,
  write `none` and the prompt skips this step.
- **`[MAX_LINES]`** — the ceiling configured in the rule. Toolkit default:
  `350`.
- **`[BATCH_SIZE]`** — how many files to split before stopping and showing
  you the result. Start with `3`. Increasing this before trusting the first
  three results is the fastest way to accumulate a diff nobody reviews.
- **`[RULE_ID]`** — the size rule's ID. If installed through prompt 08, it is
  `quality/max-lines`.

## The prompt

```
Split the files that exceed this project's per-file size budget into
smaller, focused modules. This is behavior-preserving refactoring, not a
rewrite and not a feature change.

## 0. Ground truth

Run [LINT_COMMAND] and list every file reported by [RULE_ID], with its
actual line count, sorted largest first. Use the real output from running
it now. Never a count from memory, from a previous message, or from a
summary — if the command's output is truncated by a wrapper, run the
linter directly until you have the full list.

Report that list before touching anything.

## 1. Pick the batch

Take the [BATCH_SIZE] largest files. Do not start on any others.

For each one, before editing, state:
  - what the file is responsible for today, in one sentence
  - the seams you found, and which one you will cut on
  - what its public exports are (the names other files import from it)

## 2. Where to cut

Cut on responsibility, never on line count. The four seams worth looking
for, in this order:

  - business logic mixed into a UI or route file -> a domain service or
    use-case module
  - a repeated block of UI -> a reusable sub-component
  - data access (queries, ORM calls, raw SQL) -> a repository or adapter
  - a cluster of helpers that only serve one concept -> a
    domain-specific utility module

If a file has no seam — it is one long, genuinely cohesive
implementation — say so, leave it alone, and move to the next file. Adding
an abstraction that exists only to satisfy the linter makes the codebase
worse than the long file did. Report it as "no natural seam" and let a
human decide.

Never split at an arbitrary line number to get under the budget. A file
named helpers.ts, utils.ts, misc.ts or common.ts holding whatever was
left over is a failure, not a result.

## 3. Preserve the interface

After the split, the original file's public exports must still exist,
with the same names and the same signatures. Prefer leaving the original
file as a thin module that re-exports from the new ones over editing
every import site across the codebase.

Rewriting import sites is allowed only when the original file is meant to
disappear entirely, and only when you say so explicitly before doing it.

## 4. One file at a time

For each file in the batch, in order:

  a. make the split
  b. run [TYPECHECK_COMMAND] (skip if it is "none")
  c. run [TEST_COMMAND]
  d. run [LINT_COMMAND] and confirm the file is no longer reported, and
     that no NEW violation appeared anywhere
  e. commit, with a message naming the file and the seam you cut on
  f. only then move to the next file

If b, c, or d fails, fix it before moving on. Do not proceed with a
failing check and do not batch the fixes at the end.

Watch for a specific trap in step d: extracting code frequently trades one
violation for another. A function pulled out of a long file can push its
new home over the budget, and an extraction can change a function's
inferred return type, which surfaces as a type error rather than a lint
error. Both are your problem, in the same commit.

## 5. Stop and report

After [BATCH_SIZE] files, stop. Do not continue into the next batch on
your own.

Report:
  - the files you split, and the seam used for each
  - the files you deliberately did NOT split, and why
  - the output of [LINT_COMMAND] run one final time: how many files are
    still over the budget, and their names
  - any violation of another rule that appeared as a side effect

Mark nothing as done that you did not verify by running the command again.

Codebase: [STACK/FRAMEWORK]. Budget: [MAX_LINES] lines. Rule: [RULE_ID].
```

## Usage example

Imagine prompt 08 just reported eleven files above 350 lines in a Next.js
app, the largest being a 780-line `src/app/dashboard/page.tsx`. Fill in:

- `[LINT_COMMAND]` → `npm run lint`
- `[TEST_COMMAND]` → `npm test`
- `[TYPECHECK_COMMAND]` → `npm run typecheck`
- `[MAX_LINES]` → `350`
- `[BATCH_SIZE]` → `3`
- `[RULE_ID]` → `quality/max-lines`

The agent lists the actual eleven files, takes the three largest, and
reports for `page.tsx`: current responsibility "builds the dashboard and
also calculates balance aggregates"; seams found "aggregate calculations
(business logic) and three repeated metric cards (UI)"; public exports
"default `DashboardPage`". It extracts aggregates to a domain module and
cards to a subcomponent, preserves `export default`, runs typecheck, tests
and lint, confirms no new warnings, and commits. Then it handles the second
file. In the third, it finds a 400-line parser that is one cohesive state
machine — reports "no natural seam", leaves it untouched, and stops. At
the end, it says eight files remain above the ceiling and lists them.

## Tips

- A low `[BATCH_SIZE]` is not excessive caution: it keeps the diff at a size
  a human actually reviews. Three files per round, one commit per file,
  gives six recovery points if something goes wrong.
- When the agent says "no natural seam", read the file before disagreeing.
  Sometimes it is right, and the right action is adding that specific file
  to the rule's `ignore` instead of chopping it up.
- Combine with [`03-multi-agent-code-review.md`](03-multi-agent-code-review.md)
  at the end of each batch — extraction is exactly the kind of change
  where a separate reviewer sees what the extractor misses.
- The pitfalls in step 4d have concrete code examples in
  [`../tools/06-eslint-biome-quality-gates.md`](../tools/06-eslint-biome-quality-gates.md)
  — worth reading before the first round.
