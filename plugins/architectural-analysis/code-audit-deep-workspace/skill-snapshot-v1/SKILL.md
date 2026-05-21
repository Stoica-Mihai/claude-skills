---
name: code-audit-deep
description: >
  Line-level code audit skill. Surfaces concrete, actionable findings —
  perf hotspots, error-handling correctness bugs, memory-shape problems,
  function-level complexity, and semantic coupling — that file-level
  architectural analysis cannot see. Use this skill when the user asks
  to audit code, find perf issues, hunt bugs, review error handling, do
  a deep code review, find what is slow, look for syscalls in loops,
  check memory footprint, or get specific `file:line — finding — fix`
  recommendations. Also trigger on "audit this", "review this code",
  "find bugs in X", "what's wrong with X", "deep review", "perf review",
  "look for correctness issues", "what can go wrong here", even when
  the user does not literally say "audit". Pairs with the companion
  `architectural-hotspots` skill — that one says *which files* to look
  at, this one says *what is wrong inside them*.
---

# Code Audit (Deep)

Line-level audit. Companion to `architectural-hotspots`. Hotspots ranks
files by structural shape (fan-in, fan-out, LOC, cycles); this skill
reads files and emits specific, actionable findings with line numbers
and fix sketches.

The core failure mode this skill exists to prevent: producing vague
"consider refactoring X" advice instead of `commit.rs:426 — NonceGen
calls SystemTime::now() per nonce; hoist or seed-and-increment`. The
first is what a graph tool already said; the second is what the user
actually wanted.

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
- Style / formatting issues → clippy / eslint / ruff handle these.
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

2. **Read each target end to end.** Headers and type signatures are
   not enough. A finding requires a line number, and a line number
   requires having read the line. Skim-reading is the most common
   failure of this skill — defend against it actively.

3. **Audit along the five axes** (next section). Most files only hit
   two or three axes. Don't reach for findings in an axis that
   genuinely doesn't apply.

4. **Emit findings in the fixed format** (later section). Categorized.
   `file:line`. One-line symptom. One-line fix sketch. No paragraphs
   of prose around each finding — the user is reading for signal.

5. **Pick the top 3-4 highest-leverage fixes** out of the full list
   and name them at the end. This is the deliverable the user will
   actually act on first.

## The five axes

Each axis answers a different question. They are deliberately
orthogonal — a finding belongs in exactly one category.

### 1. Perf

*What is making this slow that shouldn't be?*

Smells:
- **Syscalls in per-element loops.** `open`, `stat`, `exists`,
  `metadata`, `read_dir` called inside a loop body.
- **Time / RNG / clock calls per element.** `SystemTime::now()`,
  `Instant::now()`, `rand`, `gettimeofday` — fine once, expensive
  per element.
- **Allocation in hot loop.** `String::new`, `Vec::new`, `.clone()`
  of non-trivial data, `.to_owned()`, `format!` in inner iter.
- **Full re-scans where incremental would do.** Re-running a regex
  over the entire post-image to detect changes. Re-walking a tree
  that was just walked. Recompiling a pattern per call.
- **Redundant parse / compile.** Same file read twice. Same regex
  compiled in two paths. Same tree-sitter Query built twice.
- **Forced materialization.** `.collect::<Vec<_>>()` of a stream
  whose only consumer is `.iter()` or one-pass.

Probes (use as starting points, not as the audit itself):
```
rg -n 'SystemTime::|Instant::|\.now\(\)' <file>
rg -n '\.exists\(\)|\.metadata\(\)|fs::read|read_to_string' <file>
rg -n '\.clone\(\)' <file>
rg -n 'collect::<Vec' <file>
```

### 2. Correctness — error handling

*Where do errors silently disappear?*

Smells:
- `let _ = fallible_call();` — return value, including errors,
  discarded. Sometimes intentional (best-effort cleanup) but often
  a hidden bug. If intentional, the comment must explain.
- `.ok()` immediately after `?`-able call — converts to `Option`,
  drops error type.
- **First-error-wins aggregation** where the caller needs to see
  *all* failures: `results.into_iter().find(|r| r.is_err())`,
  `.collect::<Result<Vec<_>, _>>()` when partial success matters.
- **Cleanup / rollback / recover that can itself fail silently.**
  A rollback function returning `()` that calls `fs::rename`
  internally without surfacing failures is hiding partial-state
  bugs.
- `?` inside a loop where one bad element should not abort the
  whole batch (or vice versa — `?` *missing* where it should fail
  fast).
- `match` arms that absorb specific err variants without comment.
- `fsync` / `sync_all` on a parent dir failing silently — only
  observable when the OS later loses data.

Probes:
```
rg -n 'let _ = ' <file>
rg -n '\.ok\(\);|\.ok\(\)$|\.ok\(\)\?' <file>
rg -n 'unwrap_or\(|unwrap_or_else' <file>
rg -n 'if let Err' <file>      # often where silencing happens
```

### 3. Memory shape

*What is held in memory that doesn't need to be, or held twice?*

Smells:
- **Pre- and post- of the same data held together.** Struct holds
  full new text *and* the rendered diff of old→new. The diff
  already encodes the new text relative to old — keeping both
  doubles per-file footprint.
- `Vec<String>` where `Vec<&str>` would suffice given lifetimes.
- `Arc<Mutex<T>>` where `T: Copy` + atomics would do.
- **Large enum variants forcing the whole enum to its max
  variant.** One 200-byte variant inflates every instance.
  `Box<LargeVariant>` fixes.
- Long-lived caches with no eviction policy.
- Whole-file buffers in a tool that could stream.
- Per-file accumulator holding original + new + diff
  simultaneously while only one is consumed downstream.

### 4. Function-level complexity

*Where is one function doing too much, or too dangerously?*

These are visible only by reading function bodies — graph tools
miss them because they live below the file boundary.

Smells:
- **Recursion with no depth bound** — especially on data the user
  controls (parser, walker, AST visitor). Stack-overflow vector.
- Function > ~80 lines doing more than one thing.
- `match` dispatch with > ~10 arms — table-driven version often
  clearer and easier to extend.
- Closure capturing `&mut` to many outer variables — usually a
  struct trying to be born.
- Function with > 5 parameters — parameter object or builder.
- Two functions whose bodies differ only by a constant or branch
  — collapse to one.

### 5. Coupling — semantic, not graph

*What couples that the import graph cannot see?*

`architectural-hotspots` sees file-to-file imports. This axis
catches the rest:
- Two modules look orthogonal but both call the same set of
  helpers from a third — they share an implicit protocol that
  wants to be made explicit.
- A "library" module that branches on a value it gets from
  exactly one caller — the abstraction has one user. Inline it
  or own the branch in the caller.
- **Dual orchestrators with overlapping imports** — one
  orchestrator can usually absorb the other, or both should
  delegate to a thinner core. Hotspots flags both as "tangles"
  without naming the relationship.
- Type defined in module A, used only by module B — wrong home.
- "Generic" helper used only by one site — not generic, just
  premature.

## Output format

Use this exact template. Counts in the headings let the user scan
volume at a glance. Omit any section with zero findings — do not
pad.

```
**Perf (N)**
- `file:line` — symptom in ≤8 words. Fix: <one short phrase>.

**Correctness (N)**
- `file:line` — symptom. Fix: <one short phrase>.

**Memory (N)**
- `file:line` — symptom. Fix: <one short phrase>.

**Complexity (N)**
- `file:line` — symptom. Fix: <one short phrase>.

**Coupling (N)**
- `file_a:line + file_b:line` — symptom. Fix: <one short phrase>.

**Top targets**
3-4 highest-leverage fixes, named with file + symptom.
```

### Examples

Good:

> **Perf (2)**
> - `commit.rs:426` — `NonceGen::next` calls `SystemTime::now()` per
>   nonce. Fix: hoist call, increment counter.
> - `commit.rs:328` — `recover_sweep` does `exists()` syscall per
>   backup. Fix: single `read_dir` + filter.

Bad (vague, no line, no fix):

> Consider refactoring `commit.rs` for performance. Some operations
> may be inefficient.

Bad (over-prosaic, paragraph form):

> Looking at `commit.rs`, around the `NonceGen` struct, I noticed
> that it calls `SystemTime::now()` which is a syscall. This could
> be slow if called many times, although it depends on the use
> case…

The format constraint matters because the user reads dozens of
findings; signal density wins.

## Calibration

A good audit of a single ~500-line file usually yields 5-15
real findings. Fewer than ~3 means either the file is genuinely
clean (a real outcome, say so) or the audit was too shallow.
More than ~20 usually means the bar dropped — drop the weakest
ones rather than pad the list.

Every finding must survive the "would the user act on this?"
test:

| Finding | Acts on it? |
|---|---|
| `commit.rs:426 — SystemTime::now() per nonce, hoist` | yes |
| `commit.rs is long, consider splitting` | no — that's hotspots |
| `function could be more idiomatic` | no — that's clippy |
| `naming could be clearer` | no — not what this skill is for |

When in doubt, drop it.

## Anti-patterns

- **Skim-reading.** Defaulting to function signatures and headers,
  emitting findings about "what the function probably does".
  Always read bodies before claiming a finding.
- **Overconfident fix sketches.** "Fix: use `tokio::spawn`" when the
  codebase is sync. Match fixes to the project's actual stack.
- **Findings the codebase already addresses.** A `// SAFETY:` block,
  a documented `let _ =`, a comment explaining why a clone is
  required — not findings. Read the comments.
- **Hand-waving "consider X" verbs.** Replace with concrete
  imperatives: *hoist*, *inline*, *collapse*, *extract*, *box this
  variant*, *bound the recursion*, *aggregate all errors*.
- **Trying to be exhaustive.** A focused list of 8 real findings
  beats a sprawling list of 25 mostly-noise. The user picks 3-4 to
  act on either way.
