# Audit: `crates/recast-core/src/plan.rs`

Scope: memory shape (what is held in RAM, and for how long, vs. what the data
flow strictly requires) and redundant work across passes. Cross-checked
against `rewrite.rs`, `pattern.rs`, `walker.rs`, `commit.rs`, `structural.rs`,
and the binary consumers in `crates/recast/src/main.rs`.

The file is small and the contracts are clean. The findings below are real,
but ranked: the first three are worth acting on; the rest are notes for when
the file is touched again.

---

## Findings (memory shape)

### M1. Unified diffs are rendered for every change regardless of consumer. (high impact)

`process_one` always calls `unified_diff(&label, &before, &outcome.after)` and
stuffs the result into `FileChange.diff` (plan.rs:277-285). Looking at the
binary side, the diff string is only ever read in two places:

- `emit_diff` (`main.rs:445-446`) — `--diff` mode (the default), writes
  `change.diff` to stdout.
- `emit_apply` does **not** read `diff`; even with `--verbose` it only prints
  `change.path` and `change.matches` (`main.rs:469-475`).
- `--check` (`main.rs:369-377`) only reads `plan.changes.len()`.
- `--apply` (`main.rs:359-367`) discards the plan after handing it to
  `apply_changes`, which reads `path`, `after`, `matches`, `permissions` —
  never `diff` (`commit.rs:137-163`).
- JSON `from_plan` emits `{path, matches}` per change, no diff
  (`json.rs:78-88`).
- JSON `from_apply` / `from_check` likewise ignore `diff` (`json.rs:90-103`).

So in `--apply`, `--check`, and `--json`-modes that aren't `Plan`-with-text,
`FileChange.diff` is dead weight. For a heavily-modified file the diff
string is `O(before.len() + after.len())` — roughly the same size as `after`
itself for whole-file rewrites. That doubles peak planner memory for a
workload that never looks at the diffs.

The `serde` skip on `after` already acknowledges that the post-image is
internal-only state (plan.rs:76-77); `diff` deserves symmetric treatment in
the *compute* dimension, not just the wire dimension.

**Fix sketch:** make `diff` lazy. Two reasonable shapes:

1. Push diff rendering down to `emit_diff` (and the JSON-with-diff caller, if
   one is added). `FileChange` carries `before: String` (or just the
   pre/post pair on demand) only when the caller asked for diffs. The
   "drop pre-image after diff" comment in plan.rs:62-70 is fine reasoning
   for the *current* design but assumes the diff will always be consumed.
2. Or: thread a `want_diff: bool` (or `OutputFormat`) into `PlanOptions`,
   skip the `unified_diff` call when false, and store `String::new()` (or
   make the field `Option<String>`). This is the smaller change.

Either way you avoid the `similar::TextDiff` allocation + the diff string for
every `--apply` invocation. On a tree of, say, 500 changed files at 50 KiB
each, this is ~25 MiB the planner currently pins for no reason.

### M2. Regex convergence check does a full `find_iter().count()` when `is_match` would do. (medium impact)

`regex_convergence_check`:

```rust
fn regex_convergence_check(pattern: &CompiledPattern, after: &str) -> Result<usize> {
    Ok(pattern.regex().find_iter(after).count())
}
```

It is consumed by `process_one` as:

```rust
let extra = convergence_check(pattern, &outcome.after)?;
if extra > 0 {
    return Err(Error::NonConvergent { path: ..., extra });
}
```

The exact count is plumbed into `Error::NonConvergent { extra }`
(`error.rs:31-34`), so it has *some* observable value. But for the common
case where the rewrite is convergent (zero extra matches — the happy path
on every well-formed rewrite), `find_iter().count()` still walks the entire
post-image looking for additional hits past the first. `regex::Regex::is_match`
short-circuits on the first hit and skips the rest, which is the only signal
`process_one` needs to *decide* whether to error.

**Fix sketch:** check existence with `is_match` first (cheap, allocation-free,
short-circuits); only when it returns true does the more expensive
`find_iter().count()` need to run to populate the error message. For
convergent rewrites (the dominant case) this turns an O(file) probe into a
near-O(1) probe once Aho-Corasick / DFA seeks past the end.

Same idea applies inside `process_one` regardless of pipeline:

```rust
if !opts.allow_non_convergent {
    if !regex.is_match(&outcome.after) {
        // convergent — skip the count entirely
    } else {
        let extra = regex.find_iter(&outcome.after).count();
        return Err(Error::NonConvergent { ... });
    }
}
```

### M3. Scripted convergence check re-runs the full Rhai rewrite on the post-image, only to compare strings. (medium impact, scripted-only)

```rust
let converge = |p: &CompiledPattern, s: &str| -> Result<usize> {
    let outcome = rewrite_text_scripted(p, worker, s)?;
    Ok(if outcome.after != s { outcome.matches } else { 0 })
};
```

This does the regex scan over `s`, allocates a `Captures` per hit, builds a
`Vec<&str>` of captures per hit, evaluates the Rhai AST per hit, builds the
post-post-image string, then throws all of that away except a bool-shaped
return. For a file with N matches, that is N Rhai evaluations purely to
detect "would the script change anything?".

There's no fully general cheap version — scripts are opaque. But the cost can
be capped by bailing on first divergence. A drop-in upgrade:

```rust
let converge = |p: &CompiledPattern, s: &str| -> Result<usize> {
    use std::cell::Cell;
    let diverged = Cell::new(false);
    let mut count = 0usize;
    for caps in p.regex().captures_iter(s) {
        let caps_vec: Vec<&str> = caps.iter()
            .map(|m| m.map(|m| m.as_str()).unwrap_or("")).collect();
        let replacement = worker.replace(&caps_vec)?;
        let matched = &caps.get(0).unwrap().as_str();
        if replacement != *matched {
            diverged.set(true);
            count = 1;
            break;
        }
    }
    Ok(if diverged.get() { count } else { 0 })
};
```

(There's no `extra > 1` reporting requirement for scripted, so a single
"yes/no" suffices. The error message would lose granularity but the scripted
path is rare and the savings are large on big files.)

If you want to keep the exact count, at minimum avoid building the
post-image string: use `captures_iter` directly so the `replace_all`
string-building cost goes away.

### M4. `par_iter().collect::<Vec<Result<Option<FileChange>>>>()` materializes every per-file result before any consolidation. (low impact at current limits)

```rust
let results: Vec<Result<Option<FileChange>>> = files.par_iter().map(...).collect();
let changes = collect_changes(results)?;
```

The two-stage shape costs:

- An intermediate vec of `Result<Option<FileChange>>` (one entry per scanned
  file, including skipped binaries and no-match files — i.e. `Vec<Result<None>>`
  for the majority of typical workloads).
- A second walk in `collect_changes` that moves each `Some(change)` into a
  fresh `Vec<FileChange>` and drops the rest.

With `max_files = 1000` default this is microscopic. But:

- **Fail-fast is lost.** A single non-convergent file triggers `Err`, yet
  rayon has already paid the rewrite cost for *every* file in the walk
  because `collect` waits for all workers. On a 10k-file tree (raised
  `max_files`) with a non-convergent pattern, the planner does ~10k full
  reads + regex passes before reporting the first failure.
- **Memory peak** holds both the `results` vec *and* the in-progress
  `changes` vec for the duration of `collect_changes`, plus all the
  `FileChange` payload strings (`after`, `diff`).

**Fix sketch:** use `try_fold` + `try_reduce` to combine and fail fast, or at
minimum `try_for_each_init` for non-error termination:

```rust
let changes: Vec<FileChange> = files.par_iter()
    .map(|p| process_one(...))
    .filter_map(|r| r.transpose()) // Result<Option<T>> -> Option<Result<T>>
    .collect::<Result<Vec<_>>>()?;
```

This still doesn't cancel in-flight tasks (rayon doesn't support that), but
it removes the intermediate `results` vec and the second pass. The same
applies to the scripted variant and to `plan_structural_rewrite` in
`structural.rs:356-369`, which has the same shape — worth lifting into a
helper given the DRY rule in AGENTS.md.

### M5. `FileChange.permissions` is `Option<Permissions>` but is always `Some(permissions)` at construction site. (low impact, type-shape)

`process_one` does `permissions: Some(permissions)` (plan.rs:284) and
`structural::plan_one` does the same (`structural.rs:406`). The only places
in the workspace that ever set it to `None` would be hand-constructed
`FileChange`s in tests; production code is always `Some`.

`commit::stage_one` then does `change.permissions.clone()` and matches on
the `Option`. The `Option` discriminant is useless given current call
sites — it just costs one branch per file in commit.

**Fix sketch:** make it `Permissions` directly. Saves the `Option` tag (1 word
on most platforms) per `FileChange` and removes the `if let Some(perm) = ...`
in `stage_one`. Pre-1.0, AGENTS.md §11 says break freely.

### M6. `permissions` is cloned twice per file. (negligible)

`read_text_or_skip_binary` returns the `Permissions`, `process_one` moves it
into `FileChange`, then `stage_one` clones it (`commit.rs:143`) only to
hand it to `fs::set_permissions(...)`. On unix `Permissions` is a thin
`u32` wrapper, so the cost is real-but-rounding-error; flagging only because
the comment block at plan.rs:62-70 explicitly trumpets the "one stat per
file" optimization, and a future maintainer who reads it will assume
permissions are equally tight throughout.

If you're already touching commit.rs, `stage_one` can move out of `&change.permissions`
via a borrow rather than `.clone()`.

---

## Findings (redundant work / passes)

### R1. Two convergence concepts running side-by-side. (clarification, not a bug)

The regex pipeline runs *two* convergence checks:

1. `CompiledPattern::is_convergent()` — once per invocation, pure analytical
   probe on the replacement template (`pattern.rs:62-65`). Result is fed to
   `finalize_plan` only to decide whether a zero-match scan is
   `AlreadyApplied` vs. a normal `Changes` (with empty changes — which
   reduces to "no changes" either way).
2. `regex_convergence_check` — per-file, applied to the post-image of every
   changed file inside `process_one`. This is what actually rejects
   `a → aa`.

For non-script regex rewrites, when `is_convergent()` is `true`, the per-file
check is *almost* guaranteed to find zero extra matches — *almost* because
the replacement can interact with adjacent source bytes to form a new match
that the static probe couldn't see (`X` → `Y` where the surrounding text is
`X` and the file contains `XX`, etc.). So both are load-bearing.

But the `is_convergent` result is currently *only* used to decide a
near-tautological branch in `finalize_plan` (zero matches + convergent →
`AlreadyApplied`). Since `process_one` already filters out files with zero
matches and `total_matches == 0` implies `changes.is_empty()` (see N1
below), the `convergent_or_scripted` flag in `finalize_plan` only differs
behaviorally when the *whole tree* matched zero times — i.e. exactly the
"already applied" classification. That's fine and correct, but the
relationship is non-obvious and worth a sentence in the docs of
`finalize_plan` so a future reader doesn't think the per-file check is
redundant when `is_convergent()` is true.

### R2. `read_text_or_skip_binary` issues two syscalls per file (metadata + read). (acknowledged, probably right)

`fs::metadata` then `fs::read_to_string`. The metadata call is used for:

- `max_bytes` pre-check (avoid reading a 4 GiB binary into RAM)
- capturing `permissions` so commit doesn't stat again

Both are real reasons. `fs::read_to_string` would itself return
`InvalidData` for non-UTF8 and would happily over-read past `max_bytes`
before discovering the problem. So the dual-syscall is the right shape;
leave it.

The only micro-optimization is `File::open` + `metadata()` on the handle
to keep things FD-local, but that's noise.

---

## Findings (small/cosmetic)

### N1. `finalize_plan` defensively replaces `changes` with `Vec::new()` when `total_matches == 0`.

```rust
if total_matches == 0 && convergent_or_scripted {
    return Ok(Plan {
        changes: Vec::new(),
        ...
    });
}
```

`process_one` returns `Ok(None)` whenever `outcome.matches == 0 || outcome.after == before`,
so `total_matches == 0` strictly implies `changes.is_empty()` already. The
`Vec::new()` is defensive belt-and-braces. Either drop it (pass `changes`
through) or keep it with a one-line `// invariant: changes is empty here`
comment to forestall a future maintainer's "why?". Negligible perf
difference (an empty Vec doesn't allocate), purely a clarity issue.

### N2. `label_for_path` reallocates per change.

`rewrite::label_for_path` builds a `PathBuf` then converts to `String`
(`rewrite.rs:87-98`). Called once per `FileChange`, only used as the diff
header. Not a hot path, but it's a `PathBuf` allocation just to drop leading
`./`. A direct `String` builder over `path.components()` would avoid the
intermediate `PathBuf`. Touch only if you're already in `rewrite.rs`.

### N3. Two near-identical `plan_*` functions and a copy in `structural.rs`.

`plan_rewrite`, `plan_rewrite_scripted`, and
`plan_structural_rewrite` (in `structural.rs`) all follow the same shape:
walk → enforce `max_files` → compile → `par_iter.map(process_one)` →
`collect_changes` → `finalize_plan`. AGENTS.md §11 calls out DRY explicitly.

The three differ in:

- which compiler runs (regex / regex+script-engine / tree-sitter)
- what `map_init` initializer the workers need (none / `script.fresh()` /
  `(parser, cursor)`)
- whether a convergence check applies

A shared `plan_pipeline<C, R, W>(walker_input, opts, init_worker, process_file)`
helper would consolidate the three, and the fail-fast `try`-collect from M4
above would land in one place. This is a refactor not strictly demanded by
the audit prompt, but the duplication will rot the worst the next time
`PlanOptions` grows a field that needs handling in all three call sites.

### N4. Trace noise in tight loops.

`trace!(path = %path.display(), ...)` inside `process_one` formats the path
into the event even when the `trace` level is disabled. `tracing` macros do
gate at level, but `path.display()` is a wrapper, not a string allocation,
so this is fine. Mentioning only to confirm I checked it.

---

## Summary

Highest-leverage fixes, in order:

1. **Don't render diffs when no consumer will read them** (M1). Biggest peak
   memory win; trivial to gate via `PlanOptions` or by deferring rendering
   to the caller.
2. **Short-circuit the convergence probe via `is_match`** (M2). Cheap edit,
   measurable in benchmarks for the common convergent case on large files.
3. **Bail the scripted convergence check on first divergence** (M3). Bounded
   savings but they grow with N (matches per file) for the script-heavy
   path that's already the slowest.
4. **Use a fail-fast `try`-collect and lift the shared pipeline** (M4, N3).
   Improves error latency on large trees and removes the duplicated control
   flow.
5. **Drop the `Option` wrapper on `FileChange.permissions`** (M5). Pre-1.0,
   no compat cost.

Everything else (R1, N1, N2, N4, M6) is taste-level or doc-only.

Key files cited:

- `/home/mcs/Documents/git/recast/crates/recast-core/src/plan.rs`
- `/home/mcs/Documents/git/recast/crates/recast-core/src/rewrite.rs`
- `/home/mcs/Documents/git/recast/crates/recast-core/src/pattern.rs`
- `/home/mcs/Documents/git/recast/crates/recast-core/src/commit.rs`
- `/home/mcs/Documents/git/recast/crates/recast-core/src/structural.rs`
- `/home/mcs/Documents/git/recast/crates/recast-core/src/json.rs`
- `/home/mcs/Documents/git/recast/crates/recast/src/main.rs`
