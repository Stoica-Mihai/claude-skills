---
name: code-audit-deep
description: >
  Line-level code audit skill. Surfaces concrete, actionable findings —
  perf hotspots, error-handling correctness bugs, durability / ordering
  bugs, memory-shape problems, function-level complexity, semantic
  coupling, and concurrency-primitive scope mistakes — that file-level
  architectural analysis cannot see. Language-agnostic. Use this skill
  when the user asks to audit code, find perf issues, hunt bugs, review
  error handling, do a deep code review, find what is slow, look for
  syscalls in loops, check memory footprint, or get specific
  `file:line — finding — fix` recommendations. Also trigger on "audit
  this", "review this code", "find bugs in X", "what's wrong with X",
  "deep review", "perf review", "look for correctness issues", "what
  can go wrong here", even when the user does not literally say
  "audit". Pairs with the companion `architectural-hotspots` skill —
  that one says *which files* to look at, this one says *what is wrong
  inside them*.
---

# Code Audit (Deep)

Line-level audit. Companion to `architectural-hotspots`. Hotspots ranks
files by structural shape (fan-in, fan-out, LOC, cycles); this skill
reads files and emits specific, actionable findings with line numbers
and fix sketches.

The core failure mode this skill exists to prevent: producing vague
"consider refactoring X" advice instead of `commit.rs:426 — clock
sampled per element in hot loop; hoist or seed-and-increment`. The
first is what a graph tool already said; the second is what the user
actually wanted.

## Language scope

This skill is **language-agnostic**. The smells below are concepts that
recur across stacks; the parenthetical examples are illustrative for a
few common languages but never exhaustive. When you read a file, map
each smell to the *equivalent* construct in the target language:
- "fallible call return value discarded" covers `let _ = f()` (Rust),
  bare `f()` ignoring its `error` return (Go), `try: f(); except:
  pass` (Python), unawaited `f()` returning a Promise (TS / JS), `_,
  _ = f()` patterns (Lua / Go), `f(); // ignore` everywhere.
- "owned-when-borrow-suffices" covers `Vec<String>` vs `Vec<&str>`
  (Rust), `[]string` copies vs slice aliases (Go), deep-copying lists
  (Python), `.slice()` cloning vs index access (JS), `std::string` vs
  `std::string_view` (C++).
- "lock-when-atomic-suffices" covers `Arc<Mutex<u64>>` (Rust),
  `sync.Mutex` for a counter (Go), `threading.Lock` around an int
  (Python), `Object.synchronized` for a primitive (Java).

Never report a finding using a language construct the project does not
use. Substitute the project's equivalent before writing the fix sketch.

## When to run

Use whenever the user wants *findings inside code* rather than *rankings
across files*. Triggers include:

- "audit `commit.rs`" / "review `plan.rs`"
- "find perf issues in this module"
- "what could go wrong in `apply_changes`?"
- "deep review of the parser"
- "where is this slow?"
- After running `architectural-hotspots` and the user wants the next
  level of detail on the flagged files.

Do **not** use when the user wants:
- Architectural overview / rankings → that's `architectural-hotspots`.
- Style / formatting issues → clippy / eslint / ruff / staticcheck etc.
- Security review of specific CVE classes → a dedicated security skill
  should run. Overlap is fine; this skill won't hunt for known CVEs.
- A single trivial bug fix in a known file — just fix it.

## Method

The strength of this skill comes from depth, not breadth. Better to
audit three files thoroughly than ten superficially.

1. **Pick targets.**
   - If the user named files, those are the targets.
   - If not, and a recent hotspots report exists, take the top 3-5
     files by combined signal (god + hub, god + tangle, or any file
     inside a cycle).
   - If neither, ask the user *which files* — not "should we audit?"
     but "which files do you want audited?" so the answer drives
     work.

2. **Read every function body end to end.** Headers and type
   signatures are not enough. A finding requires a line number, and a
   line number requires having read the line. Do not skip a function
   because its name sounds boring or routine — `apply_changes`,
   `commit_one`, `cleanup`, `recover`, `flush` often hold the
   subtle ordering bugs. Skim-reading is the dominant failure mode of
   this skill — defend against it actively by asking, for each
   function, "if this had a bug, where would it be?".

3. **Audit along the seven axes** (next section). Most files only hit
   three or four. Don't reach for findings in an axis that genuinely
   doesn't apply.

4. **Emit findings in the fixed format** (later section). Categorized.
   `file:line`. One-line symptom. One-line fix sketch. No paragraphs
   of prose around each finding — the user is reading for signal.

5. **Pick the top 3-5 highest-leverage fixes** out of the full list
   and name them at the end. This is the deliverable the user will
   actually act on first.

## The seven axes

Each axis answers a different question. They are deliberately
orthogonal — a finding belongs in exactly one category.

### 1. Perf

*What is making this slow that shouldn't be?*

Smells:
- **Syscalls / IO inside a per-element loop.** File-system probes
  (exists / stat / metadata / readdir), opens, reads, network
  round-trips, DB queries — fine once, expensive per element.
- **Clock / RNG / time calls per element.** Wall-clock or
  monotonic-clock samples, RNG draws, UUID generations done per
  iteration when one sample-and-increment would do.
- **Allocation in hot loop.** Building a fresh container, formatting
  a fresh string, copying a non-trivial value each iteration when a
  reused buffer or borrowed view would do.
- **Full re-scans where incremental would do.** Re-running a regex
  / parse / hash over the *entire* post-image to detect changes that
  could be tracked at write-time. Re-walking a tree that was just
  walked.
- **Redundant parse / compile.** Same input parsed twice. Same
  pattern compiled in two code paths. Same query / plan built per
  call instead of cached.
- **Forced materialization.** Collecting a stream into a fully
  materialised container whose only consumer is one-pass iteration.

How to look: read the body of every loop. Ask "is this O(work-per-item)
or am I doing O(work-per-file * items)?".

### 2. Correctness — error handling

*Where do errors silently disappear?*

Smells:
- **Fallible call whose return value is discarded.** Often
  intentional (best-effort cleanup) but often a hidden bug. If
  intentional, a comment explains why. If no comment, suspect.
- **Error converted to absent-value type, original error dropped.**
  The error type carried useful information; the caller has lost it.
- **First-error-wins aggregation** where the caller needs to see
  *all* failures. Common in parallel / batch contexts — collecting
  results and returning only the first `Err` hides every other
  failure.
- **Cleanup / rollback / recover function whose own failures are not
  surfaced.** A rollback that itself calls a fallible operation and
  returns `()` is hiding partial-state bugs.
- **Early-return inside a loop where one bad element should not
  abort the batch (or vice versa — should fail fast but does not).**
- **`match` / `switch` arms that absorb specific error variants
  without comment** — silently classify an error as success.
- **fsync / flush failure ignored** — only observable when the OS
  later loses data.

### 3. Correctness — durability / ordering

*If the process dies mid-operation, what state remains?*

Smells, applicable any time the code mutates shared / persisted /
external state:
- **Effect ordered before its precondition is durable.** Deleting
  backups before fsyncing the new content's parent directory. Removing
  the old row before the new row is committed. Releasing the
  in-memory lock before the on-disk update is observable.
- **Commit before fsync.** Reporting success before the write is
  durable.
- **Cache invalidation before write.** Readers can observe the gap.
- **Lock released before the protected state is fully published.**
- **Compensating-action ordering wrong.** Rollback does steps in
  same order as forward path, leaving an inconsistent intermediate.
- **Parent-directory fsync skipped.** On POSIX, a fsynced file in
  an un-fsynced directory can vanish on crash. Easy to forget.

How to look: trace the *order of side-effects* through each function
that touches shared state. Ask "if I crash here, can a reader see
the new state without the old state, or vice versa, in a way the
contract forbids?".

### 4. Concurrency / pool placement

*Are concurrency primitives installed in the scope the caller
expects?*

Smells:
- **Worker pool / thread pool installed around the wrong scope.**
  The user-facing flag (`--threads N`, `--concurrency M`) is honored
  in one phase but ignored in another because the pool wasn't
  scoped wide enough.
- **Async runtime spawned per call** instead of shared.
- **Connection pool / channel pool created at wrong unit of work**
  (per-request when it should be per-process, per-process when it
  should be per-tenant).
- **Per-thread state read from cross-thread context** (or vice
  versa).
- **`spawn` / `Promise.all` / `errgroup` with no bound on
  parallelism** — accidentally unlimited fan-out under load.
- **Single-threaded fast-path inside otherwise-parallel pipeline**
  — a serial bottleneck masked by aggregate timing.

How to look: find every place the project defines a pool, an
executor, a runtime, a spawn site. For each one, identify the
*scope* it covers and the *scope* the caller assumed. Mismatches
are the bug.

### 5. Memory shape

*What is held in memory that doesn't need to be, or held twice?*

Smells:
- **Pre- and post- of the same data held together.** Struct holds
  full new text *and* the rendered diff of old→new. The diff already
  encodes the new text relative to old — keeping both doubles
  per-item footprint.
- **Owned-when-borrow-suffices.** A copy is taken where a view or
  reference into the original would be safe given lifetimes /
  ownership.
- **Lock-when-atomic-suffices.** A mutex protects a value that fits
  in a machine word and could be an atomic.
- **Variant-size disparity.** One large variant of a discriminated
  union inflates every instance — boxing the large variant fixes.
- **Long-lived cache with no eviction policy.**
- **Whole-input buffer where a stream would work** — tool that
  could pipeline reads holds the entire input in memory.
- **Optional / nullable field that is always populated in
  practice** — the absent case is dead, the wrapper costs bytes
  and forces every reader to handle a case that cannot occur.

### 6. Function-level complexity

*Where is one function doing too much, or too dangerously?*

Visible only by reading function bodies — graph tools miss these
because they live below the file boundary.

Smells:
- **Recursion with no depth bound** — especially on data derived
  from user input (parser, walker, AST visitor, JSON decoder).
  Stack-overflow vector. The iterative-stack version is usually
  one rewrite away.
- **Function > ~80 lines doing more than one thing.**
- **Dispatch / switch / match with > ~10 arms** — often a table or
  registry pattern is clearer and easier to extend.
- **Closure / inner function capturing many outer mutable
  variables** — usually a struct trying to be born.
- **Function with > 5 parameters** — parameter object or builder.
- **Two functions whose bodies differ only by a constant or a
  branch** — collapse to one parameterised version.

### 7. Coupling — semantic, not graph

*What couples that the import graph cannot see?*

`architectural-hotspots` sees file-to-file imports. This axis
catches the rest:
- Two modules look orthogonal but both call the same set of
  helpers from a third — they share an implicit protocol that
  wants to be made explicit.
- A "library" module that branches on a value it gets from exactly
  one caller — the abstraction has one user. Inline it or own the
  branch in the caller.
- **Dual orchestrators with overlapping responsibilities** — one
  orchestrator can usually absorb the other, or both should
  delegate to a thinner core. Hotspots flags both as "tangles"
  without naming the relationship.
- Type defined in module A, used only by module B — wrong home.
- "Generic" helper used only by one site — not generic, just
  premature.
- Two functions doing the same operation in slightly different
  ways across modules — same shape, divergent details.

## Output format

Use this exact template. Counts in the headings let the user scan
volume at a glance. Omit any section with zero findings — do not
pad.

```
**Perf (N)**
- `file:line` — symptom in ≤8 words. Fix: <one short phrase>.

**Correctness (N)**
- `file:line` — symptom. Fix: <one short phrase>.

**Durability/ordering (N)**
- `file:line` — symptom. Fix: <one short phrase>.

**Concurrency (N)**
- `file:line` — symptom. Fix: <one short phrase>.

**Memory (N)**
- `file:line` — symptom. Fix: <one short phrase>.

**Complexity (N)**
- `file:line` — symptom. Fix: <one short phrase>.

**Coupling (N)**
- `file_a:line + file_b:line` — symptom. Fix: <one short phrase>.

**Top targets**
3-5 highest-leverage fixes, named with file + symptom.
```

### Examples

Good:

> **Perf (2)**
> - `commit.rs:426` — clock sampled per nonce in hot path. Fix:
>   sample once at construction, increment a counter.
> - `commit.rs:328` — FS-probe syscall per backup entry. Fix:
>   single directory listing, then filter in memory.
>
> **Durability/ordering (1)**
> - `commit.rs:301` — backup deleted before parent-dir fsync.
>   Fix: fsync parents first, then unlink backups.
>
> **Concurrency (1)**
> - `main.rs:343` — `--threads` flag scoped only around planner;
>   apply phase runs on global pool. Fix: install scoped pool
>   around the whole pipeline.

Bad (vague, no line, no fix):

> Consider refactoring `commit.rs` for performance. Some
> operations may be inefficient.

Bad (over-prosaic, paragraph form):

> Looking at `commit.rs`, around the nonce generator, I noticed
> that it samples the wall clock, which involves a syscall. This
> could be slow if called many times, although it depends on the
> use case…

The format constraint matters because the user reads dozens of
findings; signal density wins.

## Calibration

A good audit of a single ~500-line file usually yields 6-18 real
findings across the active axes. Fewer than ~3 means either the
file is genuinely clean (a real outcome, say so) or the audit was
too shallow. More than ~25 usually means the bar dropped — drop
the weakest ones rather than pad the list.

Every finding must survive the "would the user act on this?"
test:

| Finding | Acts on it? |
|---|---|
| `commit.rs:426 — clock per nonce, hoist` | yes |
| `commit.rs:301 — backups deleted before fsync, swap order` | yes |
| `commit.rs is long, consider splitting` | no — that's hotspots |
| `function could be more idiomatic` | no — that's clippy |
| `naming could be clearer` | no — not what this skill is for |

When in doubt, drop it.

## Anti-patterns

- **Skim-reading.** Defaulting to function signatures and headers,
  emitting findings about "what the function probably does".
  Always read bodies before claiming a finding. The most
  bug-prone functions are the ones whose names sound mundane —
  read them first, not last.
- **Reporting in the wrong language.** Writing a Rust-flavoured
  fix sketch for a Python project. Match the project's actual
  stack.
- **Findings the codebase already addresses.** A safety
  annotation, a documented "ignore error here because X", a
  comment explaining why a clone is required — not findings.
  Read the comments.
- **Hand-waving "consider X" verbs.** Replace with concrete
  imperatives: *hoist*, *inline*, *collapse*, *extract*, *box*,
  *bound the recursion*, *aggregate all errors*, *swap order*,
  *scope the pool*.
- **Trying to be exhaustive.** A focused list of 10 real findings
  beats a sprawling list of 25 mostly-noise. The user picks 3-5
  to act on either way.
- **Confusing axes.** Durability/ordering bugs are not perf
  bugs. Concurrency-scope mistakes are not correctness in the
  error-handling sense. Pick the axis that points to the right
  fix shape.
