# Lint Quality Gates: ESLint + Biome

Two linters, two roles — deliberately, without overlap. One runs a
small, carefully selected set of rules targeting a handful of
specific anti-patterns. The other carries most of the coverage: rules
that need complete TypeScript type information, plus rules
specific to the framework the project uses. Running both at once is not
redundant — it lets each tool cover the area where it is fast
and precise, instead of choosing one and asking it to do the entire
job alone.

This guide first explains the reasoning behind that split — why
two tools, why a curated set of rules instead of the entire
"recommended" package, and why a lint warning can be a migration tool
rather than just a temporary state. Then a step-by-step tutorial
shows how to build this setup from scratch in a new project. Finally, five
code examples show the setup's most surprising pitfalls
in practice — the kind of thing that only becomes apparent after you have
run into it once.

## Before you begin: what a linter is, what a formatter is

If you have never configured any of this, start here — the rest of the text
assumes you know the difference between the two.

A **linter** is a program that reads your code without running it and flags
problems: a variable declared but never used, a pattern that often
hides bugs, a snippet that breaks a team convention. Each problem it
can detect is a **rule**, and each rule has a
**severity**: `"off"` (disabled), `"warn"` (a warning — appears in the terminal
or editor but does not block anything), or `"error"` (an error — can block a
build, commit, or CI pipeline, depending on how you connect the
linter to the rest of the workflow).

A **formatter** is a different tool with a narrower job:
it only handles code appearance — indentation, single or double quotes,
where to wrap a long line. It has no opinion about logic, only
visual style, and usually rewrites the file itself to apply
the chosen standard.

ESLint and Biome can each do both — lint and format.
This guide covers a specific decision: use each tool only for the part
of the work where it offers the most value, instead of choosing one and asking
it to handle everything alone.

## Why two linters instead of one

Any linter's "recommended" preset is a fixed package designed to
suit as many projects as possible at once — which, in
practice, means it misses in both directions: it includes rules that make no
sense in your specific context and still leaves out rules your
project actually needs. Splitting work between two tools
lets each cover what it does best and turns "what is enabled,
and why" into an explicit, defensible choice — recorded as
comments in the configuration itself — instead of a list inherited from an
industry default nobody on the team actually chose.

## Curated Biome rules, heavy coverage in ESLint

Biome is fast — fast enough (it is written in Rust, which explains much
of that) to run a small set of handpicked rules instead of
the full "recommended" preset it ships with (around
200 rules). Choosing five or six specific rules over
two hundred generic ones is a legitimate choice in itself — and the reason for each
choice should live in a comment right beside the configuration
applying the rule, not in a separate document nobody will remember to
keep updated alongside it:

```jsonc
// biome.jsonc
{
  // We deliberately do NOT use Biome's "recommended" preset
  // (~200 rules). Here Biome covers a handful of specific
  // anti-patterns; ESLint (with type-aware and framework-specific
  // rules) covers the rest. Overlapping coverage
  // between two linters just means maintaining the same
  // rule in two places.
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": false,
      "correctness": {
        // A variable declared but never used is almost always a
        // forgotten import or dead code — worth blocking as an error.
        "noUnusedVariables": "error"
      },
      "suspicious": {
        // Explicit "any" is not forbidden, but deserves visibility:
        // this is precisely where TypeScript stops checking types
        // for you. Keep it at "warn", not "error" — sometimes it is
        // the right solution, but must be a visible choice, not a habit.
        "noExplicitAny": "warn"
      }
      // ...a handful of additional rules, each chosen for a specific
      // reason — never "because they came in the package".
    }
  }
}
```

ESLint covers the rest: type-aware rules (more on those
later) that need the complete information only the TypeScript
compiler has, framework-specific rules (React hooks,
accessibility, route conventions), and any anti-pattern the curated
Biome set deliberately leaves out. This normally comes from the
`typescript-eslint` package, combining the TypeScript parser with rules
that know how to use type information, plus the plugin for the framework
the project uses.

## The formatter, deliberately disabled

Enabling an automatic formatter for the first time in a large codebase
that has never used one creates a wall of diffs — thousands of changed
lines across the files it touches, unrelated to any real bug.
This buries any actual review that should be happening: a
reviewer cannot distinguish "Biome changed single quotes to double quotes"
from "this line changed to fix a real bug." In such a codebase,
keeping the formatter disabled — and documenting why in the configuration
file itself — is a legitimate choice. It is not a gap that needs
an excuse.

```jsonc
// biome.jsonc
{
  // Deliberately disabled: this codebase predates Biome adoption
  // and has never used an automatic formatter. Running a
  // formatter for the first time across thousands of untouched files
  // would create a wall of formatting-only diffs unrelated
  // to real bugs — worse than leaving it disabled and explaining why,
  // right here.
  "formatter": {
    "enabled": false
  }
}
```

Notice that this reasoning applies specifically to a **large, existing**
codebase. If you are starting a project from scratch — the
scenario in the tutorial below — there is no "wall of diffs" to avoid,
because there is no history of never-formatted files. In that case, enabling
the formatter from the first commit is the simplest path: you never
pay the cost of formatting everything at once, because every file starts
formatted.

```jsonc
// biome.jsonc — new project, no legacy formatting to inherit
{
  "formatter": {
    "enabled": true
  }
}
```

## From warning to error: promotion as a migration tool

In an existing codebase, a newly introduced rule with violations may enter as
`"warn"`, while existing rules retain their severity. A new rule with no violations
starts at `"error"`. If the existing gate requires zero warnings, measure adoption
separately without weakening it. From there, the warning count
is a real, trackable number, not a "we'll tighten this
later" comment nobody ever revisits. Only when that count reaches
zero does the rule become `"error"` — and stay that way.

```js
// eslint.config.js (excerpt)
export default [
  {
    rules: {
      // New rule, introduced at "warn" to make the violation count
      // visible without blocking anyone now. Becomes "error"
      // when the count reaches zero.
      complexity: ["warn", 10],
    },
  },
];
```

`complexity` is a built-in ESLint rule that measures a function's **cyclomatic
complexity**: it starts at 1 (the function body with no
control-flow branches) and adds a point for each branch — each `if`/`else if`,
`case` in a `switch`, `&&`, `||`, `??`, loop (`for`/`while`), and ternary
operator (`? :`). The `10` in this example is the total ceiling, including the base:
at 11 points, the function triggers the rule. Remember that number — it
returns in Example 2 below, with one of the most surprising pitfalls
in this entire setup.

This warn → error workflow turns a vague promise into a migration with
command-verifiable success criteria — exactly the process
detailed in [ESLint warning burndown](../prompts/02-eslint-warning-burndown.md),
which describes planning and executing a warning-count reduction to zero
without introducing silent behavioral changes along the way.

## Architecture boundaries: blocking imports between layers

Import-restriction rules prevent one specific code layer
from directly importing another. Two common examples:
preventing UI code (screens, components) from accessing a database
client directly without going through the layer meant to orchestrate it; or
preventing any layer from skipping the domain layer to reach
low-level infrastructure directly. The central idea: dependencies
between layers may only flow in an agreed direction — never in the
opposite direction, even if the import could technically be written and
work.

A useful trick when some violations already exist throughout the
codebase: register the **same** restriction rule twice under two
different names, each with a different severity. One copy stays at
`"error"` — boundaries the team has committed never to cross again. The
other copy, targeting the same kind of violation but a different,
already known set of old files, stays at `"warn"` — visible,
tracked as debt, without blocking the entire build now.

This works because, in ESLint's configuration file, the rules block
is just a key-value object: you cannot write the same key
`"local/no-cross-layer-import"` twice in one block with different
severities — the second would simply overwrite the first. The solution is
to register the same rule function under two different names in your
local plugin, then use each name with its own severity:

```js
// eslint-plugin-local/index.js — one implementation, two rule IDs
import noCrossLayerImport from "./rules/no-cross-layer-import.js";

export default {
  rules: {
    "no-cross-layer-import": noCrossLayerImport, // used at "error"
    "no-cross-layer-import-legacy": noCrossLayerImport, // used at "warn"
  },
};
```

```js
// eslint.config.js (excerpt)
import local from "./eslint-plugin-local/index.js";

export default [
  {
    plugins: { local },
    rules: {
      // Boundaries the team has committed never to cross again.
      "local/no-cross-layer-import": ["error", { from: "ui", to: "database" }],
      // Same rule, same logic — a different, already known set
      // of violations still being paid down gradually. Visible,
      // without blocking the build.
      "local/no-cross-layer-import-legacy": ["warn", { from: "ui", to: "infra-adapters" }],
    },
  },
];
```

`from` and `to` are illustrative options in this example — a real
implementation of this kind of rule usually inspects each `ImportDeclaration`
node in the AST (the tree representing code structure; explained more
fully in the next section), checks whether the current file matches the
`from` pattern and the imported path matches the `to` pattern, and reports
only when both match simultaneously.

Before writing this rule from scratch, check whether an existing plugin
solves it: `eslint-plugin-boundaries` and `eslint-plugin-import`'s
`import/no-restricted-paths` rule cover this same problem for many
common cases. Writing your own rule pays off when your project's layer
structure differs from what these plugins expect — which brings us
to the next section.

## Custom lint rules

Community rules cover the general case. Sooner or later, every real
codebase hits a gap no published plugin covers — something
too specific to your domain for someone to have already written a generic
rule for it. At that point, writing a small custom rule
pays off more than continuing without any automated check for that
anti-pattern. Common categories of custom rules — illustrative
examples of the category, not a closed list or anything taken from a
specific real project:

- a maximum line count per file;
- a ban on unwrapped `console.*` in production code;
- a ban on accessing a low-level client or resource outside the
  layer that should be its sole accessor;
- a ban on floating-point arithmetic for monetary values
  (`0.1 + 0.2` is not exactly `0.3` in floating point — money
  requires a decimal type or integer cents, not a plain `number`);
- a rule requiring authentication checks before any mutation
  in an API route;
- a rule requiring a maximum character limit on every text field
  users fill in.

The minimal shape of one:

```js
// rules/no-console-in-production.js
module.exports = {
  meta: { type: "problem" },
  create(context) {
    return {
      "CallExpression[callee.object.name='console']"(node) {
        context.report({
          node,
          message: "Use the shared logger, not console.*, in production code.",
        });
      },
    };
  },
};
```

For anyone who has never written an ESLint rule, each part of this file:

- **`meta.type`** classifies the rule for ESLint and tools that
  generate documentation from it — `"problem"` means "this
  is probably a bug," unlike `"suggestion"` (style) or
  `"layout"` (spacing).
- **`create(context)`** is the rule body. It returns an object whose
  keys are **AST selectors**. Think of an AST (*Abstract Syntax Tree*)
  as code broken into a tree of
  nodes: a function call is one node, a variable declaration another,
  an `if` another. An AST selector works like a CSS selector,
  except it selects nodes in this tree rather than HTML elements.
- **`"CallExpression[callee.object.name='console']"`** reads: "any
  *function call* node whose call target is a property of an
  object literally named `console`" — meaning `console.log(...)`,
  `console.error(...)`, `console.warn(...)`, any `console.<anything>(...)`.
- **`context.report({...})`** actually generates the warning or error,
  with the message the developer sees in the terminal or editor.

This is enough to cover most simple custom rules —
anything more elaborate, such as the architecture-boundary rule in the
previous section, follows the same shape, just with a more specific selector and
a little more checking logic inside `create`.

## Type-aware lint, outside the fast path

Type-aware rules need complete information
that only the TypeScript compiler sees — not
just the syntax of an isolated file, but each value's actual type,
inferred from the entire project. These rules can notice
an `async` function called somewhere without `await`, or
a comparison between two types that could never be
equal. For this, ESLint needs to build a complete TypeScript program
behind the scenes — the same heavy work `tsc` does — which is
orders of magnitude slower than a purely syntactic rule that only
looks at one file's tree at a time.

In a large codebase, deliberately keep this checking level **outside**
the default lint script and pre-commit hook (the script that runs
automatically before each commit is created and can block it) —
otherwise every commit, even the most trivial, pays the cost of building
the entire TypeScript program. Instead, this level runs as a separate
manual command or only in CI (continuous integration — the pipeline
that runs automatically on each push or pull request on a machine separate
from yours):

```json
{
  "scripts": {
    "lint": "eslint .",
    "lint:typed": "eslint . --config eslint.typed.config.mjs"
  }
}
```

For new TypeScript projects, `lint:typed` is an explicit `check`/CI gate with
`no-floating-promises` and `no-misused-promises` at `error`. Use the
[focused profile](../../templates/eslint/next.typed.config.mjs.example), which
extends the fast configuration without a broad type-aware preset. Preserve
existing severities and gates. Only newly introduced rules with violations begin
at `warn`, with measured counts and a reduction plan; new rules without violations
start at `error`.
Measure elapsed time and peak memory before adding typed rules or widening scope;
keep the command separate from fast lint and Git hooks. The separate
[advanced typed profile](../../templates/eslint/eslint.typed.config.mjs.example)
retains the broader warning rules for gradual adoption. Preserve its checks in
projects already using it; the focused profile is the greenfield Next baseline.

## Tutorial: building this setup from scratch in your project

The text above explained the reasoning behind each piece. This section
assembles them in order in a new TypeScript project — adjust package
names and rules for your own framework where appropriate.

If you prefer delegating this entire tutorial to a coding agent,
[`07-eslint-complete-setup.md`](../prompts/07-eslint-complete-setup.md) is
the prompt version — covering the same philosophy, plus architecture
boundaries, custom rules, and the type-aware lint tier,
ready to paste into an agent and adapt to your project's placeholders.

### 1. Install both tools

```bash
npm install --save-dev eslint typescript typescript-eslint
npm install --save-dev --save-exact @biomejs/biome
```

`typescript-eslint` provides, in one package, the parser that teaches ESLint
to understand TypeScript syntax and the rule sets (including
type-aware ones) we will use in step 4. Biome's `--save-exact`
pins the exact version in `package.json` instead of a range — preventing a
rule from changing behavior by itself during someone else's `npm install`
on an arbitrary day without anyone deliberately choosing it.

### 2. Initialize and curate the Biome configuration

```bash
npx @biomejs/biome init
```

This creates a `biome.json` (change the extension to `.jsonc` — and adjust the
reference in `package.json` — if you want comments) with the
`"recommended"` preset enabled. Change it to `"recommended": false` and
add only the groups and rules you actually decided to use,
one by one — as in the curated example in "Curated Biome rules,
heavy coverage in ESLint" above. Start small: two or three obvious
correctness rules (`noUnusedVariables` is a good first step) are already worth more
than two hundred rules nobody will review individually.

### 3. Decide on the formatter

New project, starting from scratch now? Keep Biome's formatter enabled
from the first commit — it is the default after `init`, and costs
nothing in a project that has no nonconforming files yet. Only
disable it and document why ("The formatter, deliberately
disabled" above) if you are **importing** a large existing codebase
that has never used a formatter.

### 4. Configure fast ESLint, then focused type-aware rules

```js
// eslint.config.mjs
import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default [js.configs.recommended, ...tseslint.configs.recommended];
```

For Next.js, preserve its official ESLint presets instead of replacing them with
this generic baseline. Then copy the
[focused typed configuration](../../templates/eslint/next.typed.config.mjs.example) to
`eslint.typed.config.mjs`. Its `projectService: true` obtains TypeScript information;
`tsconfigRootDir: import.meta.dirname` locates the project. Adjust the source glob
to files included by the project's tsconfig. New projects use the two async-safety
rules as errors. Existing projects preserve their current protections and use
measured warnings only for newly introduced rules with violations.

### 5. Install your framework's plugin, if it has one

If the project uses React, Vue, or another framework with its own conventions
(hook rules, accessibility, route conventions), install its ESLint
plugin now and extend the same configuration array from step 4.
This plugin goes on top of the base presets — the same "presets are a
starting point, not the final word" logic.

### 6. Separate the fast script from the type-aware script

```json
{
  "scripts": {
    "lint": "eslint .",
    "lint:typed": "eslint . --config eslint.typed.config.mjs"
  }
}
```

Keep type-aware rules in the second configuration. Include `npm run lint:typed`
in the new project's explicit `check`/CI sequence. Preserve equivalent existing
script names, severities, and gates. For newly introduced rules with legacy
violations, measure warnings and runtime, then promote each rule once clean.
See "Type-aware lint,
outside the fast path" above for the reasoning.

<a id="7-connect-fast-lint-to-a-pre-commit-hook"></a>

### 7. Keep checks explicit

Run lint through project scripts. This setup does not install Git hooks, hook managers, branch blocks, or push restrictions.

Preserve existing hooks. If the user specifically requests this integration, use the mechanism already adopted by the project and keep type-aware lint off the fast path. Do not impose a new hook as a prerequisite for ESLint configuration.

### 8. Introduce new rules gradually in existing code

```js
// eslint.config.js (excerpt)
export default [
  {
    rules: {
      complexity: ["warn", 10],
    },
  },
];
```

Run `npm run lint` and record the current warning count — this number is the
migration's starting point, not a disposable detail. From here,
follow [ESLint warning burndown](../prompts/02-eslint-warning-burndown.md)
to plan the reduction to zero before changing `"warn"` to `"error"`.

### 9. Apply architecture boundaries if the project has layers

If your project already separates layers (UI, domain, infrastructure, or
otherwise) and you want to prevent one from jumping directly to another, follow the
dual-severity technique in "Architecture boundaries" above — or
start with existing plugins (`eslint-plugin-boundaries`,
`import/no-restricted-paths`) before writing your own rule.

### 10. Write your first custom rule only when truly needed

Do not start here. A custom rule is the last resort, after
confirming that no Biome, ESLint, or community plugin rule
already covers the anti-pattern you want to block. When that time
comes, "Custom lint rules" above shows the minimal
shape of one.

## Concrete examples: pitfalls in practice

The five most surprising pitfalls of this two-linter setup, one
by one — the code triggering the problem, what lies behind the
linter's report, and how to actually resolve it instead of merely silencing the warning.

### Example 1 — the "safely unsafe" regex

A common security rule tries to detect regexes vulnerable to **ReDoS**
(*Regular Expression Denial of Service* — a regular expression that, for
certain inputs, takes exponentially longer to process as the
input grows). The simplest way to implement this detection is a
heuristic: look for two or more quantifier groups (`+`, `*`,
`{n,m}`) in the same regular expression. Implementations of this kind —
`eslint-plugin-security`'s `security/detect-unsafe-regex` rule is a
well-known example — historically trigger on this pattern even when each
quantifier is already tightly bounded.

```js
// May trigger the "unsafe regex" rule despite being harmless: two
// sequential quantifier groups in the same expression, each already
// with a repetition ceiling.
const CODE_PATTERN = /^[A-Z]{2,4}-[0-9]{1,6}$/;
```

`{2,4}` and `{1,6}` are already bounded — this regex cannot reprocess the
same string segment exponentially because each group has a fixed
repetition ceiling. Even so, the heuristic only looks at the syntactic shape
("a quantifier followed by another quantifier"), not the actual
size of the ceilings, and flags it as suspicious.

The seemingly obvious fix — tightening the limits further, replacing
`{1,6}` with `{1,4}`, for example — solves nothing, because the heuristic
never looked at the ceiling's size, only at the presence of two sequential
groups. The actual fix is restructuring into separate expressions,
each with a single quantifier, and composing the result in ordinary code:

```js
// Actual fix: each regex has just one quantifier; the combined
// check happens in ordinary code, not in a single regex.
const PREFIX_PATTERN = /^[A-Z]{2,4}$/;
const SUFFIX_PATTERN = /^[0-9]{1,6}$/;

function isValidCode(value) {
  const [prefix, suffix] = value.split("-");
  return Boolean(
    prefix && suffix && PREFIX_PATTERN.test(prefix) && SUFFIX_PATTERN.test(suffix),
  );
}
```

### Example 2 — cyclomatic complexity inflated by optional chaining

Cyclomatic complexity rules, including ESLint's `complexity`
used in the warn → error example above, often count optional
chaining (`?.`) as a full branching point — the same weight as an
`&&`, `||`, or ternary. This technically makes sense (`a?.b` is,
under the hood, fairly similar to `a && a.b`), but in practice catches people
by surprise: a function with several chained optional accesses reaches the
complexity ceiling well before any visual count of `if`/`else`
would suggest.

```js
// There is only ONE actual "if" — but for most of these rules, each
// "?." and each "??" also adds a branching point.
function getShippingCity(order) {
  if (!order) return null;

  return (
    order.customer?.address?.city ??
    order.customer?.billingAddress?.city ??
    order.warehouse?.address?.city ??
    "unknown"
  );
}
```

Counting the way most of these rules count — 1 base point for the function
itself, plus 1 per control-flow branch — this function totals: 1 (base) + 1 (the
`if`) + 6 (six `?.`, two per line on three lines) + 3 (three `??`, one per
line) = **11**. That already exceeds the ceiling of 10 configured in the
warn → error example above — the rule triggers on this function even though it reads
like a single `if` followed by three fallback alternatives.

The fix is not rewriting the logic — it is recognizing that the rule's
complexity ceiling needs calibration with the knowledge that `?.` and `??` also
count, and that such a function (cascading fallbacks over optional
fields) is a candidate for a small utility function tested
separately, instead of a long chain of `?.`/`??` in a single
`return`.

### Example 3 — the extraction that fixes one warning and creates another

A strict line-count ceiling per file (for example, 400 lines) can leave
several files sitting right at the limit without any headroom. In that
scenario, a routine extraction — moving a function fragment into a
separate file to resolve ONE size warning — can push the extraction's
destination file above its own ceiling, creating a
new violation in a file that was not even part of the original problem.

- `file-a.ts` — 399 lines (1 line of headroom under the 400 ceiling)
- `file-b.ts` — 396 lines (4 lines of headroom under the 400 ceiling)

A naive extraction — moving a function from `file-a.ts` to
`file-b.ts`, together with a new `import`, an export line, and a
blank line — can get `file-a.ts` out of the red and push
`file-b.ts` to 401 or 402 lines. The original warning disappears; a new one
appears in a file that was not even on your list. That is why the
only reliable way to know whether a refactor solved (or created) a
size problem is to rerun the linter after the change — never
count lines manually or trust an estimate of how much the extraction
"should" save.

When a file is already at the ceiling, the order of preference, from
cheapest to most expensive, is:

1. **A nested closure with no parameters** — an inner function declared
   inside the existing one without passing any parameters (it already sees
   everything in the surrounding scope). Costs few lines and does not change
   any public signature.
2. **A guard closure** — extract only the guard check
   (`if (!condition) return`) into a small function, reducing repetition
   without touching the main logic.
3. **Compact existing code** — combine lines that exist only for
   formatting (for example, a `return` that could share the condition's
   line), without changing any behavior.
4. **Split the file in two** — only as a last resort, because it creates a
   new file, requires a new name and responsibility
   boundary, and is the kind of change deserving its own review, not a side
   effect of fixing a lint warning.

### Example 4 — the return type that changes by itself when extracting a function

```ts
// Written inline like this, TypeScript often infers a very precise
// return type: the union discriminated by "status", with no "data"
// appearing at all (not even optionally) in the error branch.
const parseResult = (input: string) => {
  if (input.length === 0) {
    return { status: "error" as const };
  }
  return { status: "ok" as const, data: input.trim() };
};

// Inferred type: (input: string) =>
//   { status: "error" } | { status: "ok"; data: string }
```

A caller using `if (result.status === "ok")` gets automatic
type narrowing: inside the `if`, TypeScript knows
`result.data` exists and is a `string` without any extra check.

```ts
// The SAME logic, extracted into a separate named function — seems
// like a purely mechanical, risk-free refactor.
function parseInput(input: string) {
  if (input.length === 0) {
    return { status: "error" as const };
  }
  return { status: "ok" as const, data: input.trim() };
}

// In some situations, the inferred type loses per-branch precision
// and becomes broader:
//   (input: string) => { status: "error" | "ok"; data?: string }
```

The shape changed from a discriminated union of two distinct shapes to
a single shape with an optional `data` field. For calling code,
this is a silent change: `result.data` is no longer
guaranteed inside `if (result.status === "ok")`, because TypeScript no
longer has two shapes to discriminate — it has one shape with a field
that may or may not be there. Every place relying on automatic
narrowing gets a type error — not in the file you just
edited, but in any distant file calling that function. At the time of
extraction itself, nothing flags a problem: the editor underlines nothing, and the
extracted function compiles cleanly. The error appears only at **call sites**,
possibly in files you never even opened.

This does not always happen — it depends on how each specific function is
written and which compiler version is in use — but happens often
enough to form a habit: before extracting a function where each
branch returns an object literal with a slightly different shape,
grep every caller first, and after extraction run the
entire project's typecheck — not just the changed file — before
considering the extraction complete.

### Example 5 — the shorthand property the analysis script cannot resolve

Custom tools walking the AST — for example, a homemade script
scanning code for a specific pattern using the
TypeScript compiler API or ESLint parser — often treat
`{ x: value }` (explicit property) and `{ x }` (shorthand property,
when the property name matches the variable name) as
different tree structures, even though they are semantically identical. A
script that can follow the assigned value in `x: value` but does not know
that `{ x }` is exactly the same thing, just written more briefly, will fail
to detect — or resolve the value — anywhere using the shorthand
form.

```js
const port = 8080;

// An analysis script that only understands the explicit form finds
// the value here without trouble:
const explicitConfig = { port: port };

// ...but cannot resolve the value here — despite being the SAME "port"
// with the SAME value, just written in shorthand:
const shorthandConfig = { port };
```

In the AST, `{ port: port }` normally appears as a `Property` node with
`key` and `value` as two distinct nodes (even with the same name).
`{ port }` is also a `Property` node, but with a
`shorthand: true` marker — and a script written assuming clearly separate
`key` and `value` nodes may not check this marker, or
may wrongly assume a shorthand property carries no value
to resolve. The result is a tool that passes the tests you
wrote (if all use the explicit form) and fails silently
in production, where shorthand is common. Deliberately write a
test case with a shorthand property in any
compiler-API analysis tool you build — this is not a
rare edge case; it is the form most developers write by
default when names already match.

## Known pitfalls (quick summary)

Recapping the five examples above as a quick reference —
for when you have already read the full reasoning once and only need to recall
the summary.

- **An "unsafe regex" heuristic can trigger on any regular
  expression with two or more sequential quantifiers**, even when
  each is already tightly bounded. The actual fix is restructuring into
  separate single-quantifier expressions — tightening the limits further
  solves nothing because the heuristic never looked at the ceiling's
  size (Example 1).
- **A cyclomatic complexity rule may count optional chaining
  (`?.`) as a full branching point** — the same weight as `&&`,
  `||`, or a ternary. A function with several chained `?.` reaches the
  complexity ceiling well before an eyeball count of `if`/`else`
  suggests (Example 2).
- **A strict per-file line ceiling can leave files exactly at the
  limit without any headroom.** An extraction intended to fix a warning
  can accidentally create a new violation in another file. Always
  recheck with the actual linter after any refactor —
  never by manually counting lines. Order of preference:
  parameterless nested closure → guard closure → compact existing
  code → split the file in two, only as a last resort
  (Example 3).
- **A function whose every branch returns an object literal may have its
  inferred return type change silently when extracted into a
  separate named function.** Some inference scenarios only preserve
  per-branch precision inline and lose it in a separate
  function signature — breaking callers' typechecks far
  from your edited file, without any warning during extraction.
  Always grep every call site before extracting a function
  of this shape (Example 4).
- **A handwritten AST analysis script may not resolve values
  through shorthand object properties** (`{ x }` vs. explicit `{ x: x }`).
  Write a dedicated test case for this in
  any custom compiler-API tool you
  build (Example 5).

## Frequently asked questions

**Do I need both linters, or can I choose just one?**

Technically, you can choose one — ESLint alone, with `typescript-eslint` and the right
plugins, covers practically everything Biome would cover too. Splitting into
two tools pays off mainly in speed: Biome runs its
small rule subset almost instantly, making it suitable for
checks you want running constantly on every
file save. If your project is small or you prefer a single
configuration, ESLint alone works — you only forgo Biome's speed
advantage for the most frequent checks.

**What if my project is small — is all this configuration worthwhile?**

For a small project, start with ESLint alone and an existing recommended
preset (from `typescript-eslint`, for example), plus the focused async-safety
profile for TypeScript. Add custom rules only for demonstrated project needs.
This entire split into two tools with curated rules solves a
scale problem: many files, many warnings, long lint times.
None of those problems exists yet in a small project. Revisit
this structure when `npm run lint` starts taking significant time, or
when the generic preset starts hindering more than helping — not
before then.

**How do I decide whether an anti-pattern needs a custom rule or can stay
without an automated check?**

Before writing anything, look for a community plugin that already
covers the case — for architecture boundaries, for example,
`eslint-plugin-boundaries` covers much of it before custom code
is needed. Write a custom rule when all three conditions hold:
(1) no published plugin covers the case; (2) the anti-pattern has already
caused a real bug or is sufficiently specific to your domain (money,
authentication, a low-level resource) to justify blocking it before it causes
one; and (3) the pattern is mechanical enough to detect through an AST — if
checking requires human judgment or business context the
code alone does not expose, a lint rule is not the right tool.

**Can I apply this entire setup at once to a large existing
project?**

Not all at once — that is essentially the opposite of what this document advocates. The
sequence would be: first, decide on the formatter (enabling it pays the wall-of-diffs
cost; disabling it with documentation is valid). Then install
Biome and ESLint with a minimal set of rules that **already pass cleanly**
today — start where the codebase actually is, not where you
wish it were. Only then add one new rule at a time, always
at `"warn"` first, following
[ESLint warning burndown](../prompts/02-eslint-warning-burndown.md) until the
count reaches zero before promoting to `"error"`. Applying everything at once,
including rules the codebase still violates in hundreds of places,
is a recipe for someone to disable the entire linter on the first
Friday with a tight deadline.

## The executable path: ready-made files

Everything above is the reasoning — why two tools, why warnings become
errors, why architecture boundaries belong in lint. If you want the
result without reconstructing the reasoning, the runnable files are in
[`templates/eslint/`](../../templates/eslint/): the three custom rules already
written and tested (file-size ceiling, direct console use, direct
database access from the presentation layer), the two configuration
skeletons, and a verifier proving the copy arrived intact.

You do not need to read these files to use them. Two prompts do the
work in this order:

1. [`08-eslint-quality-gates-install.md`](../prompts/08-eslint-quality-gates-install.md)
   — the agent downloads the rules, adapts configuration to your
   project's actual structure, runs the verifier, and reports violation counts per
   rule. It does not fix anything.
2. [`09-file-size-refactor.md`](../prompts/09-file-size-refactor.md) — the
   agent takes files exceeding the 350-line ceiling and breaks them
   into smaller modules, one file at a time, with tests running between
   each.

The first installs the measuring stick and measures; the second is the work that
measurement revealed.
