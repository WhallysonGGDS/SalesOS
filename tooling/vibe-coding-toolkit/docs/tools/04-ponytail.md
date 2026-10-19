# Ponytail

## What it is

Ponytail is a plugin — a package that extends the agent's behavior
inside Claude Code, installed with a slash command ("/") directly in the
conversation — that gives the agent an engineering discipline persona: the
"lazy senior developer." Lazy here means efficient,
never careless: the laziness of someone who has seen overly complicated code
fail in the middle of the night and learned never to write complexity that
nobody asked for again.

In practice, the plugin injects a fixed decision ladder that runs before
any line of code is written. The agent climbs it one rung at a time
and stops at the first one that solves the problem — never climbing further
"just in case." Source: [`DietrichGebert/ponytail`](https://github.com/DietrichGebert/ponytail).

## Why use it

An AI agent given an open-ended task tends toward abstraction,
configurability, and defensive code nobody requested — without an explicit
brake, it optimizes for "looking complete" rather than "solving
exactly what was asked." Common results: a cache class with a
pluggable strategy when a one-line decorator would do; an
interface with a single implementation; a configuration file for a
value that never changes.

Ponytail forces the cheapest option to be considered first,
always, before any code is written. It does not let "laziness" become
an excuse to cut corners on security, validation, or error handling —
only on what remains after ensuring those parts are covered.

## How to install/activate

Inside a Claude Code session:

```bash
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
```

The first command registers the GitHub repository as an installable
plugin source (a "marketplace"); the second installs the `ponytail` plugin
from that source.

Once installed, Ponytail is active in every response by default, at the
`full` level. It stays active even when it is unclear whether the current task
applies — the underlying rule is "assume yes." To turn it off during
the conversation, simply write "stop ponytail" or "normal mode" — no need
to uninstall the plugin. The selected level applies only to the current session;
a new session returns to the default.

### Codex and persistent instructions

[Official Ponytail](https://github.com/DietrichGebert/ponytail#install) also provides a Codex plugin. In the terminal:

```bash
codex plugin marketplace add DietrichGebert/ponytail
codex plugin add ponytail@ponytail
```

Open `/hooks` in Codex, inspect the plugin hooks, and complete the trust flow. Start a new conversation. If using only the skill, check discovery in the client's documented paths; an already installed distribution does not need another copy.

To record the intensity preference, use the [`AGENTS.md` template](../../templates/AGENTS.md.template) or incorporate this into the existing file: “Ponytail active at `full` for coding, preserving requirements, security, and accessibility.” The [Codex guide](15-codex-workflow.md) explains installation and instruction precedence.

## Step-by-step tutorial

### 1. Understand the problem before climbing the ladder

The ladder shortens the *solution*, never the *reading*. Before choosing a
rung, the agent needs to trace the actual flow and fully read the code
the change will affect. A small diff (the set of lines altered by a
change) in the wrong place is not laziness — it is a second bug. This
step always happens, even for requests that seem trivial.

### 2. Climb the ladder one rung at a time and stop at the first solution

| # | Question | If the answer is yes |
|---|---|---|
| 1 | Does this need to exist? | Speculative work — skip it and say so in one line (YAGNI: "you aren't gonna need it," meaning do not build today what nobody has requested yet) |
| 2 | Does something equivalent already exist in this codebase? | Reuse it — reimplementing something a few files away is the most common form of unnecessary complexity |
| 3 | Does the language or framework's standard library already do this? | Use the standard library |
| 4 | Does a native platform feature cover this? | Prefer native — `<input type="date">` over a calendar library, CSS over JS, a database constraint over application code |
| 5 | Does an installed dependency solve this? | Use it — never add a new dependency for something a few lines can solve |
| 6 | Can it be a single line? | Write that line |
| 7 | (only if none of the above solved it) | The minimum new code that actually works |

Do two rungs solve it equally well? Choose the higher one — the simpler one
— and move on. The first lazy solution that works is the right one,
once the problem has actually been understood.

### 3. Fix bugs at the root cause, not the symptom

A bug report describes a symptom. Before editing, the agent searches
(`grep`) every caller of the function it is about to change. The lazy
version IS the root-cause fix: a guard inside the shared
function is a smaller diff than repeating the same guard at every
call site — and fixing only the path described in the original report leaves
all sibling functions broken. Fix it once, where every caller passes through.

### 4. Mark deliberate simplifications with a `shortcut:` comment

When cutting a corner is intentional and has a known ceiling (a global
lock — a concurrency guard — instead of one per record, a scan that
scales poorly with input size, a simple heuristic), mark it
with a comment naming the limit and upgrade path:

```js
// shortcut: global lock; switch to a per-account lock if
// throughput becomes a bottleneck
```

This differs from leaving a hidden limitation — the comment exists
so the next person (or the agent itself in a future session) knows
it was a choice, not an oversight.

The current marker is `shortcut:`. `/ponytail-debt` gathers these comments as trackable debt; older installations may also recognize `ponytail:`. Preserve limits and review criteria when updating existing comments.

### 5. Finish with a minimal check when the logic is nontrivial

Code with a branch, loop, parser, or any path involving
money or security does not ship without a check that fails if the logic
breaks: the smallest possible test — an `assert` (a line that checks a
condition and stops execution if it is false) inside a
`demo()`/`__main__` block, or a small `test_*` file — without a test
framework, fixtures, or a suite per function unless requested. A trivial
one-liner needs no test: YAGNI applies to tests too.

### 6. Answer directly: code first, explanation in at most three lines

After the code, at most three short lines: what was left out, and
when to add it. No long essay, feature tour, or
design notes — if the explanation is longer than the code, the right instinct is
to delete the explanation, because every paragraph defending a simplification is
complexity returning disguised as text. This does not apply to an explanation
the user explicitly requested (a report, a walkthrough, notes
per phase) — provide that in full; the rule only targets unsolicited
prose.

Pattern: `[code] → skipped: [what was left out], add when: [when to add it]`.

## Concrete examples

### Example 1 — avoiding reflexive abstraction

**User request:** "Add a cache for this API's responses."

**Without Ponytail** — a plausible response from an agent without this brake:

```python
class ApiCache:
    def __init__(self, backend="memory", ttl=300, max_size=1000):
        self.backend = self._resolve_backend(backend)
        self.ttl = ttl
        self.max_size = max_size

    def _resolve_backend(self, name):
        if name == "redis":
            return RedisCacheBackend()
        return MemoryCacheBackend()

    def get_or_fetch(self, key, fetch_fn):
        ...  # 40 more lines of expiration and eviction policy
```

A new class, a pluggable backend interface nobody requested,
Redis support when it is not even installed in the project — all to solve a
simple cache.

**With Ponytail active:**

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def fetch_response(request_key):
    ...
```

The `@` before `lru_cache` is a Python decorator: a way to wrap
an existing function with extra behavior without rewriting it. `lru_cache` is
already a ready-made in-memory cache in the language's standard library.

`→ skipped: custom cache class. add when: lru_cache becomes measurably insufficient.`

Rung 3 of the ladder (the standard library already does it) solved it —
rung 7 was never reached.

### Example 2 — fixing the root cause, not the symptom

**User request:** "Fix this bug: `formatCurrency()` breaks when the
value is `undefined`."

**Without Ponytail** — fix only where the bug was seen:

```js
// at the only site that reported the error
const label = value !== undefined ? formatCurrency(value) : "—";
```

It works there. But `formatCurrency()` has three other callers in the project —
all remain broken for the same case.

**With Ponytail active** — the first step is to find every caller of
`formatCurrency`, then put the fix in the shared function:

```js
function formatCurrency(value) {
  if (value === undefined) return "—";
  return `R$ ${value.toFixed(2)}`;
}
```

`→ skipped: repeated guard at all 4 call sites — solved once in the function. add when: never, this is the right place for this check.`

Smaller diff, with no remaining symptom in the other three callers.

### Example 3 — when laziness does not apply

**User request:** "Add CPF validation to this registration
form."

Input validation at a trust boundary — the point where data
arrives from outside the system's direct control, in this case user
input — is nonnegotiable. Even with Ponytail at `full`, the agent
does not deliver a superficial check to "save lines": it writes the
actual validation, including the check digits, because that was explicitly
requested and is exactly the kind of shortcut the ladder never authorizes.

`→ skipped: nothing. Trust-boundary validation is on the list of things laziness never simplifies.`

## Tips and pitfalls

- **The ladder runs only after reading, never instead of it.** If a
  response "solved it too quickly" without citing the actual flow it read,
  be skeptical — skipping understanding to deliver a small diff is the
  dangerous kind of laziness: it disguises itself as efficiency and delivers a
  confident, incorrect fix.
- **Ponytail is not synonymous with a short response.** Its brevity is about
  avoiding unsolicited prose defending a simplification — unlike
  [Caveman](05-caveman.md), which compresses prose word by word. The
  two layers are independent and additive: one decides what gets built,
  the other decides how the agent talks about it.
- **Two standard-library options of equal size:** the tiebreaker is
  correctness on edge cases, not which is shorter to
  write. Laziness means writing less code, not choosing the more fragile
  algorithm.
- **A complex or ambiguous request does not block the response.** Ponytail delivers the
  lazy version and asks in the same response — "did X; Y covers the case;
  need full X? say so" — instead of stopping for confirmation
  it could already reasonably infer.
- **The level applies only to the current session.** Changing it with `/ponytail
  lite|full|ultra` does not persist across sessions; every new session restarts at
  the default (`full`).

## Frequently asked questions

**Will Ponytail simplify validation, error handling, or security to
save lines?**
No. Those items — plus basic accessibility and anything explicitly
requested — are beyond laziness's reach at every intensity
level.

**Do I need to reinstall the plugin whenever I want to change the level?**
No. `/ponytail lite|full|ultra` changes the level at any time within the
current conversation.

**Does Ponytail write tests automatically?**
Only when the logic is nontrivial — a branch, loop, parser, money
or security path — and even then it leaves only a minimal check, not
an entire suite. A trivial one-liner generates no test.

**Are Ponytail and Caveman the same thing?**
No. Ponytail decides what gets built; [Caveman](05-caveman.md) decides
how the agent talks about what it built. They are independent but
combinable plugins.

**Does the ladder change between languages?**
The reasoning does not change — standard library, native feature, already
installed dependency, one line, and only then new code — but what each rung
solves does: in a frontend stack, rung 4 might be a native HTML
element; in a backend, it might be a database constraint.
