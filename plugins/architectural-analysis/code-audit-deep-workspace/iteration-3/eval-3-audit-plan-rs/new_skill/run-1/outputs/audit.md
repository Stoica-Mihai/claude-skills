**Perf (4)**
- `plan.rs:278` — `unified_diff` rendered eagerly per file but only consumed by `emit_diff` in the non-quiet, non-JSON, non-apply, non-check path (see `main.rs:444-447`); `--apply` / `--check` / `--json` / `--quiet` all build a diff they throw away. Fix: thread a `needs_diff: bool` (or `DiffMode`) into `PlanOptions`, build diff only when set; callers in apply/check/json/quiet leave it off.
- `plan.rs:140` — `regex_convergence_check` does `find_iter(after).count()` (full scan of post-image) but the only consumer at `plan.rs:272` branches on `extra > 0`. Fix: return `bool` via `regex().is_match(after)` for early exit; collapse `Error::NonConvergent.extra` to a presence signal (or count lazily only when constructing the error).
- `plan.rs:264` — `rewrite_text` always returns an owned `String` (via `.into_owned()` in `rewrite.rs:43`) even when `outcome.matches == 0`; the caller throws it away at line 265. Fix: make `rewrite_text` return `Cow<'a, str>` (or a sentinel `Unchanged` variant); `process_one` short-circuits without ever materializing the post-image.
- `plan.rs:271` — convergence recheck runs for every changed file even when the pattern is statically convergent (`compiled.is_convergent() == true`) and literal (no boundary-introduced matches possible). Fix: gate the per-file dynamic recheck behind `!compiled.is_convergent() || !pattern.is_literal()`; pure-literal convergent rewrites need no second scan.

**Correctness (1)**
- `plan.rs:194-199` (`collect_changes`) — `?` returns the first `Err` from the parallel results vector, silently dropping every subsequent worker error. The rayon collection itself completed all work, so the data is present; the function is choosing to discard it. Fix: aggregate errors into a `Vec` (or a dedicated `Error::Multiple { errors }`) so the user sees every failure, not just the lexicographically-first path that exploded.

**Memory (2)**
- `plan.rs:73-81` (`FileChange`) — holds `after` (full post-image) *and* `diff` (unified diff of before→after) for every changed file; the diff already encodes `after` relative to the pre-image, so the planner's peak memory is roughly `2 × Σ file_size` instead of `1 ×`. Fix: pair this with the lazy-diff Perf finding above — store only `after`, render diff on demand from `&before` (re-read or kept by caller) when `emit_diff` actually prints. If retaining `before` for diffing is unacceptable, make `diff: Option<String>` populated only in diff mode.
- `plan.rs:259` (`process_one`) — `before` and `outcome.after` are both fully resident across the convergence check and diff build (lines 264-278); for large files this is `2 × file_size` per worker in flight. Fix: drop `before` immediately after `unified_diff` returns (`drop(before)` before the `Ok(Some(...))`) so the `before` arena is released before the `FileChange` is enqueued; better still, combine with the lazy-diff change so `before` lifetime ends at line 265 on the no-change path.

**Coupling (1)**
- `plan.rs:264 + rewrite.rs:43` — `rewrite_text` unconditionally calls `.into_owned()` on the `regex::replace_all` `Cow`, materializing a full clone even when zero matches; the only caller (`process_one`) discards it one line later in the no-match branch. The two files together pay an `O(file_size)` alloc per scanned file that contains no matches. Fix: return `Cow<'a, str>` from `rewrite_text` (or `enum RewriteOutcome { Unchanged, Changed { after, matches } }`); update `rewrite_text_scripted` and `process_one` in lockstep.

**Top targets**
1. `plan.rs:278` — make diff rendering lazy / opt-in; pure win for `--apply`, `--check`, `--json`, `--quiet` (CPU + memory).
2. `plan.rs:140` — switch convergence recheck to `is_match` for early exit on the common convergent path.
3. `plan.rs:264 + rewrite.rs:43` — return `Cow` / `Unchanged` variant from `rewrite_text`; eliminates a full file-size alloc per no-match file.
4. `plan.rs:194` — aggregate parallel worker errors instead of first-error-wins so users see every failure in one pass.
5. `plan.rs:271` — skip per-file dynamic convergence recheck when the static probe + literal-pattern combo already proves convergence.
