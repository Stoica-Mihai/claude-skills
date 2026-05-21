# Hotspots in `/home/mcs/Documents/git/recast`

Two-layer report: file rankings first ("where to look"), then line-level
findings inside the top targets ("what is wrong").

## File rankings

Analyzer ran across 30 source files, 13 internal import edges. The Rust
`mod` tree routes everything through `lib.rs`, so fan-in/fan-out signal is
thin — LOC and the file's *role* (orchestrator vs. leaf) are the
load-bearing signals here.

| File | LOC | Fan-in | Fan-out | Why it shows up |
|---|---:|---:|---:|---|
| `crates/recast-core/src/structural.rs` | 610 | 1 | 0 | God module. Single largest file; mixes language registry, query compilation, AST→query lowering, template parsing, and the multi-file pipeline. |
| `crates/recast/src/main.rs` | 446 | 0 | 1 | God + sole tangle. CLI parse, mode dispatch, plan emission, stdin path, structural path, recover path, lock acquisition all in one file. |
| `crates/recast-core/src/commit.rs` | 387 | 1 | 0 | Atomic-commit core. Below the god threshold but the highest-risk file in the crate by responsibility (durability + rollback + recovery sweep). |
| `crates/recast-core/src/plan.rs` | 289 | 1 | 0 | Pipeline orchestrator. Two near-duplicate `plan_rewrite` / `plan_rewrite_scripted` paths; this is the seam where regex + script + structural converge. |

No cycles detected. No grab-bag-named hubs (`utils`, `helpers`, `common`).
Naming hygiene is good across the tree.

Caveat on the rankings: the import graph is thin because Rust `mod`
declarations route every cross-module use through `lib.rs`, so the
analyzer's fan-in column understates real coupling. Treat LOC + role as
the real signal, not graph degree.

## Line-level findings

### `crates/recast-core/src/commit.rs`

**Perf (2)**
- `commit.rs:425` — `SystemTime::now()` syscall per generated sibling name in the hot stage/commit loop. Fix: sample epoch once in `NonceGen::new()`, mix only the counter per call.
- `commit.rs:399` — `target.file_name().to_string_lossy().into_owned()` allocates a new `String` per sibling name. Fix: take a `&str` and write directly into the formatted output buffer, or cache per-`FileChange`.

**Correctness (3)**
- `commit.rs:130` — first-error-wins in stage phase: every non-first stage error is silently dropped (`if first_error.is_none()`). Fix: collect all errors and surface them, or at minimum log dropped ones at `warn!`.
- `commit.rs:158` — `set_permissions` failure deletes the temp and returns, but the parent dir's fsync state was already advanced for it; on the rare partial-fail this is fine, but the comment-less `let _ = fs::remove_file(&temp_path)` swallows the cleanup error. Fix: surface cleanup failure via `tracing::warn!`.
- `commit.rs:226` — rollback rename inside `commit_one` (`fs::rename(&backup_path, &staged.target)`) ignores its `Result`; if that restore fails the caller sees only the *original* error and the on-disk state is now inconsistent. Fix: log the secondary failure with `warn!(path = …, "rollback rename failed")`.

**Durability/ordering (3)**
- `commit.rs:247-250` — `best_effort_cleanup_backups` runs *before* `best_effort_fsync_parents`. A crash between unlink and parent-dir fsync can leave a directory entry that points to a hole-after-rename whose parent never saw a barrier. Fix: swap order — fsync parents first, then unlink backups; then fsync parents again to make the unlinks durable.
- `commit.rs:223` — `fs::rename(original → backup)` is not followed by a parent fsync before the temp→original rename. The two renames are not atomic across the pair; if the second rename's metadata is reordered before the first's, recovery sees both files missing. Fix: collect parent dirs touched and fsync once per directory between phases (or accept the bound and document it).
- `commit.rs:333` — `recover_sweep` calls `fs::rename(newest → target)` but does not fsync the parent directory afterward, so a crash immediately after recovery can lose the rename. Fix: collect parent dirs of restored files and fsync each once at the end of the sweep.

**Concurrency (1)**
- `commit.rs:114` — `stage_all` uses `par_iter` and will run on whichever rayon pool is currently installed. `main.rs:343` installs the user's `--threads N` pool only around `plan_rewrite`; the apply phase runs on rayon's *global* pool, so `--threads` is silently ignored during stage. Fix: install the scoped pool in `run()` around both planner and apply, not just the planner.

**Memory (1)**
- `commit.rs:254` — `HashSet<&Path>` borrows from `committed`, fine — but `committed: Vec<Committed>` itself carries a full `PathBuf` for both `target` and `backup_path`. With N files in flight this is 2·N path allocations after the original `FileChange` already held the same `target`. Fix: replace `Committed::target` with an index into the `staged` slice (or borrow); same for `Staged::target` vs `FileChange::path`.

### `crates/recast-core/src/structural.rs`

**Perf (2)**
- `structural.rs:177` — `Vec::new()` for `hits` allocates without capacity even though every match pushes one entry; large files cause repeated reallocs. Fix: pre-size with a heuristic like `source.len() / 256` or use `Vec::with_capacity` keyed off `cursor.matches` count where available.
- `structural.rs:357-362` — `par_iter().map_init(...)` creates a fresh `Parser` *and* `QueryCursor` per worker thread, fine, but `compiled.new_parser()` calls `Parser::new()` + `set_language` for every worker (cheap but allocates a TS parser object). Acceptable; the more interesting cost is `QueryCursor::new()` which has no scratch reuse across files within a worker. Fix: confirm tree-sitter QueryCursor reuse — current code does reuse, this is OK; instead investigate `cursor.set_byte_range` or `cursor.set_match_limit` to bound runaway queries.

**Correctness (3)**
- `structural.rs:164` — `let _ = parser.set_language(&self.ts_lang);` silently discards a failure; the comment claims it's infallible "in practice" because `compile` probed it, but a future ABI mismatch between probe and worker (different feature flags?) would surface as a confusing `StructuralParse` instead of the real `set_language` error. Fix: return `Result<Parser>` from `new_parser` and propagate.
- `structural.rs:206-213` — overlapping match dedup is "first-by-start-byte wins, later overlaps skipped" but the `applied` counter only increments for non-skipped hits. The `total_matches` user sees is therefore the post-dedup count, not the raw match count from the query. That's defensible, but undocumented in the user-facing summary. Fix: name the field accordingly or surface both numbers.
- `structural.rs:552` — `node.field_name_for_child(child.id() as u32)` — `child.id()` is a `usize` derived from the node pointer; `field_name_for_child` expects a *child index*, not an id. This is the canonical tree-sitter ID/index conflation bug. On a 64-bit host with low memory pressure the cast happens to produce small numbers that don't crash, but the function is returning the field name of whichever child happens to live at that numeric index. Fix: replace with `node.field_name_for_named_child(named_index)` after computing the named child index in the iteration, or use the cursor's `field_name()` method.

**Complexity (2)**
- `structural.rs:513-561` — `emit_node` is a recursive AST walker with no explicit depth bound. On a pathological pattern AST the call stack grows unbounded. Fix: convert to an iterative walk with an explicit `Vec<Frame>` stack, or document the practical pattern-size limit.
- `structural.rs:619-648` — `subtree_ellipsis_capture` does its own DFS with a `Vec<Node>` stack, but mixes "return early on parse error" via `?` inside the stack loop and accidentally returns `None` for unrelated UTF-8 errors as if they meant "no ellipsis present". Fix: distinguish parse error from "no ellipsis found"; surface real errors.

**Coupling (1)**
- `structural.rs:341` + `plan.rs:112` — `plan_structural_rewrite` and `plan_rewrite` duplicate the walk → file-limit check → par_iter → collect → guard pipeline shape. Fix: extract a `plan_files_with<F>(files, opts, per_file: F)` helper both call into.

### `crates/recast-core/src/plan.rs`

**Correctness (1)**
- `plan.rs:139` — `regex_convergence_check` re-runs `find_iter` over the *entire* post-image of every changed file. For large files with many matches this is O(N·M) work just to detect "no new matches". Fix: short-circuit on first match — `find(after).is_some() as usize` — since `process_one` only cares whether `extra > 0`.

**Perf (1)**
- `plan.rs:271` — `convergence_check` is invoked per file but compiles nothing new — fine. However the `rewrite_text_scripted`-based scripted variant at `plan.rs:168` runs the *whole rewrite again* just to count residual matches, doubling script execution time. Fix: in the scripted converge path, run the regex only (`pattern.regex().find(after).is_some()`); the script's output already lives in `outcome.after`.

**Memory (1)**
- `plan.rs:73` — `FileChange` holds both `after: String` (full post-image) *and* `diff: String` (rendered unified diff of pre→post). For files with small edits the diff is much smaller than `after`, but for files where the whole file changed, the diff embeds nearly the full new text plus the full old text. Both are kept until the plan is consumed. Fix: render the diff lazily on demand, or drop `diff` after emission for `--apply`-only paths.

### `crates/recast/src/main.rs`

**Complexity (2)**
- `main.rs:288-353` — `run()` is a 65-line top-level dispatcher branching on `completions`, `recover`, structural, stdin, regex, scripted — six modes interleaved with lock acquisition, pattern compilation, script loading, and plan dispatch. Fix: extract one `Mode` enum + per-mode `run_*` functions, dispatch via a single `match`.
- `main.rs:501-516` — `acquire_workspace_lock_for` cobbles together a lock root from `cli.paths.first().or(cli.pattern.as_ref())` — `cli.pattern` is a regex, not a path. Under `--recover` the recover path-list logic in `recover_paths()` already handles this correctly; the lock helper reimplements the same fallback inconsistently. Fix: have the lock helper consume `recover_paths()` (or a shared `effective_paths()` helper) so the two definitions can't drift.

**Coupling (1)**
- `main.rs:340-346` + `plan.rs:151` — `main.rs` chooses between `plan_rewrite` and `plan_rewrite_scripted` based on `script.is_some()`, but only the non-scripted branch installs the user's thread pool. Scripted plans silently use rayon's global pool, ignoring `--threads`. Fix: hoist the `pool.install` to wrap *both* branches.

## Top targets

1. **`commit.rs:247` durability ordering** — backup unlink runs before parent-dir fsync. The whole point of `recast` is atomicity; a crash window here is the worst failure mode the tool can have.
2. **`commit.rs:114` + `main.rs:343` thread-pool scoping** — `--threads N` is honored in the planner but ignored in stage/commit. User-visible flag with silent wrong behavior.
3. **`structural.rs:552` field_name_for_child ID/index conflation** — the cast hides a real semantic bug; whichever field name happens to be at the numeric index of `child.id()` is returned and used as the query's field qualifier. Latent until a pattern hits the wrong shape.
4. **`plan.rs:139` full re-scan in convergence check** — change one `find_iter().count()` to `find().is_some()` and the convergence guard becomes free on large files.
5. **`structural.rs:341` + `plan.rs:112` duplicate pipeline** — extract `plan_files_with<F>` so the regex, scripted, and structural pipelines share one walk-and-fold helper. Pays back the next time a fourth mode lands.

Caveats:
- LOC counts non-blank lines, not comment-stripped — the structural and main files are dense, not commented-out.
- The hotspot graph is undercounting cross-module coupling because of the Rust `mod` indirection; the LOC + role-based picks above are the real signal.
- A few findings (`commit.rs:130`, `commit.rs:164`) sit in code paths the author has already touched recently (per the git log); confirm whether the current dropping behavior is intentional before reordering.
