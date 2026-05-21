**Perf (3)**
- `commit.rs:425-426` — `SystemTime::now()` syscall sampled on every nonce (twice per file: stage + commit). Fix: sample epoch once in `NonceGen::new`, mix into a per-instance seed, then return `seed + counter`.
- `commit.rs:114` — `par_iter().collect::<Vec<Result<_>>>` fully materialises every stage outcome before draining errors. Fix: aggregate with `try_fold` / `try_reduce` so successes and errors merge during the parallel pass.
- `commit.rs:235` — `fs::remove_file(&c.target)` before `fs::rename(backup, target)` is a redundant syscall — POSIX `rename(2)` atomically replaces the destination. Fix: drop the `remove_file` and let the rename do the replace.

**Correctness (4)**
- `commit.rs:117-127` — first-error-wins aggregation across parallel stages silently drops every additional `Err`. Fix: collect all errors into an aggregate variant (e.g. `Error::MultiIo(Vec<Error>)`) or at minimum log the dropped ones at `warn!`.
- `commit.rs:225-227` — when the temp→target rename fails, the compensating `fs::rename(backup, target)` is swallowed by `let _`; the caller is told only about the original error while the target may be permanently missing. Fix: capture the restore error and wrap it into the returned `Error` (e.g. `Error::IoWithRollback { primary, rollback }`).
- `commit.rs:233-238` — `rollback_committed` discards every `fs::rename` failure with `let _`; a failed rollback leaves a partially-mutated tree and the caller has no signal. Fix: collect rollback failures into the returned error so a partial-rollback state is observable.
- `commit.rs:253-263` — `best_effort_fsync_parents` silently swallows both `File::open` failure and `sync_all` failure; on a flaky filesystem the apply is reported as durable when it isn't. Fix: surface fsync errors (return a `Result`) and at minimum log them at `warn!` instead of the bare `let _`.

**Durability/ordering (4)**
- `commit.rs:73-75` — `best_effort_cleanup_backups` runs *before* `best_effort_fsync_parents`; a crash in the gap loses the rename of temp→target while the backup has already been unlinked, with no recovery path. Fix: fsync parent dirs first, then unlink backups (and ideally fsync parents again after the unlink batch).
- `commit.rs:137-163` — `stage_one` fsyncs the temp file but never fsyncs its parent dir, despite the docstring at line 43-45 claiming exactly that; a crash between stage and commit can leave the temp file's directory entry unrecoverable. Fix: after `set_permissions`, open the parent and `sync_all` it (dedup across files so it's once per unique parent at end of `stage_all`).
- `commit.rs:233-238` — `rollback_committed` never fsyncs the parent dirs after un-renaming; a crash mid-rollback can leave the tree in an inconsistent intermediate that survives reboot. Fix: after the rollback loop, fsync every unique parent dir the same way the success path does.
- `commit.rs:334` — `recover_sweep` renames a backup back into place but never fsyncs the parent directory before reporting success; a crash immediately after recovery can lose the restore. Fix: collect unique parents during the rename pass and fsync each one before returning the summary.

**Concurrency (1)**
- `commit.rs:114` + `main.rs:343-344` — `stage_all` uses `par_iter` but `apply_changes` is invoked outside the `pool.install` scope (only `plan_rewrite` is wrapped), so `--threads N` is ignored during stage. Fix: in `main.rs`, install the pool around the whole pipeline (or specifically around `apply_changes`), not just the planner.

**Complexity (1)**
- `commit.rs:98-108` + `:178-216` — `apply_inner` / `commit_all_with_hook` are near-verbatim copies of `apply_changes` / `commit_all` with only a between-commits hook added. Fix: parameterise `commit_all` with `Option<&dyn Fn(usize) -> Result<()>>` (or a default no-op closure under test cfg) and delete the duplicates.

**Top targets**
1. `commit.rs:73-75` — swap order so parent dirs are fsynced before backups are unlinked. This is the one finding that can cause silent data loss on crash.
2. `commit.rs:225-238` — surface rollback / restore failures instead of `let _`-ing them; today a partial-rollback tree looks identical to a clean failure.
3. `commit.rs:114` + `main.rs:343` — install the rayon pool around `apply_changes` so `--threads` actually scopes the stage phase. Currently the flag is a no-op for apply.
4. `commit.rs:425-426` — hoist the `SystemTime::now()` sample out of `NonceGen::next`; sample once at construction, then `seed + counter`. Removes one syscall per sibling-name in the hot path.
5. `commit.rs:117-127` — replace first-error-wins with multi-error aggregation so a single bad disk doesn't mask the rest of the failures the user needs to see.
