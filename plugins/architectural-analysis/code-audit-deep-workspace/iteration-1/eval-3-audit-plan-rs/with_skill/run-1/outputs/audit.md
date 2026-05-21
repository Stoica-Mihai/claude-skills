**Perf (5)**
- `plan.rs:264` (calls `rewrite.rs:43`) — `replace_all(...).into_owned()` deep-clones every file even on zero matches. Fix: match the `Cow` and only own on `Cow::Owned`, or `regex.find(before).is_none()` short-circuit in `process_one`.
- `plan.rs:278` — `unified_diff` rendered for every changed file in `--apply` and `--check` modes that never read it (see `main.rs:459` / `main.rs:369`). Fix: defer diff rendering behind a `DiffMode` flag on `PlanOptions`, render lazily in `emit_diff`.
- `plan.rs:139-141` — `regex_convergence_check` does a full second regex scan over each post-image even when `compiled.is_convergent()` and the replacement has no `$N`/`${name}`. Fix: skip per-file rescan when static convergence holds and template carries no capture refs.
- `plan.rs:168-170` — scripted convergence re-runs the entire Rhai-driven rewrite over the post-image (one Rhai call per match). Fix: probe with `regex.find(after).is_none()` first; only rerun script when a residual regex match exists.
- `plan.rs:297, 306` — `read_text_or_skip_binary` issues `fs::metadata` then `fs::read_to_string`: two stat-class syscalls per file. Fix: `File::open` once, `f.metadata()` on the fd, then `read_to_string(&mut f)`.

**Memory (3)**
- `plan.rs:73-81` — `FileChange` holds full `after` and rendered `diff` simultaneously for the whole plan. `--diff` never reads `after`; `--apply` never reads `diff`. Fix: enum `Payload::Apply(String) | Payload::Diff(String)`, picked by `PlanOptions::mode`.
- `plan.rs:80` — `permissions: Option<Permissions>` is unconditionally `Some(...)` in both production producers (`plan.rs:284`, `structural.rs:406`); only tests use `None`. Fix: store `Permissions` directly, construct test fixtures with the real default.
- `plan.rs:123-134` — `par_iter().map(...).collect::<Vec<Result<Option<FileChange>>>>()` materializes the full result vector including every `None` skip slot before filtering. Fix: `filter_map` into the parallel reduction (`fold`/`reduce` on `Result<Vec<FileChange>>`).

**Complexity (1)**
- `plan.rs:112-181` — `plan_rewrite` and `plan_rewrite_scripted` differ only by the rewrite/converge closures and the `convergent_or_scripted` flag. Fix: collapse to one private `plan_with(...)` taking the two closures + flag; the two `pub` entries become thin wrappers.

**Coupling (1)**
- `plan.rs:73 + main.rs:446 + commit.rs:150` — `FileChange` is one struct serving two disjoint downstream consumers (diff renderer reads `diff`, commit writer reads `after`), with each consumer ignoring the other's field. Fix: split per planner mode (see memory finding above) so the planner produces only what the chosen mode consumes.

**Top targets**
1. `plan.rs:278` — kill unconditional `unified_diff` rendering in `--apply` / `--check`. Biggest wall-clock win on large rewrites; touches one call site.
2. `rewrite.rs:43` via `plan.rs:264` — stop deep-cloning the whole pre-image for zero-match files. Dominant alloc cost in scan-heavy `--diff` runs.
3. `plan.rs:73-81` — collapse `after`+`diff` coexistence; both fields are alive together but never both read. Halves planner peak memory in the common case.
4. `plan.rs:168-170` — scripted convergence rerun is the worst hidden cost in the script path; one-line probe with the regex first avoids re-invoking Rhai over the whole file.
