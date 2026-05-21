**Perf (2)**
- `commit.rs:425-426` — `SystemTime::now()` sampled per nonce in parallel stage loop. Fix: sample once in `NonceGen::new()`, store as field, hash counter for each `next()`.
- `commit.rs:152` — `sync_all()` per file inside `par_iter` is the dominant cost; correct, but `--threads` is ignored here (see concurrency). Fix: ensure parallelism is honored so the kernel can overlap the syncs.

**Correctness (4)**
- `commit.rs:114-133` — `stage_all` first-error-wins; every other parallel failure dropped silently. Fix: aggregate all errors or at least log the dropped ones at `warn`.
- `commit.rs:225-228` — `commit_one` recovery rename's error is swallowed via `let _ =`; if both renames fail the original is gone and only the first error is reported. Fix: surface the recovery failure as a distinct error variant (`Error::CommitRollbackFailed { target, original, recovery }`).
- `commit.rs:233-238` — `rollback_committed` returns `()` while running two fallible renames per element; partial-rollback failures vanish. Fix: collect failures into a `Vec` and bubble them up so the caller can warn the user the tree is half-restored.
- `commit.rs:343-348` — `remove_nonced` uses `?` so one un-removable stale temp aborts the entire recovery sweep, leaving the rest of the tree dirty. Fix: best-effort per-entry, accumulate failures, continue.

**Durability/ordering (3)**
- `commit.rs:74-75` — `best_effort_cleanup_backups` runs before `best_effort_fsync_parents`; backups unlinked before new renames are durable. Fix: swap order — fsync parents first, then unlink backups.
- `commit.rs:137-163` — `stage_one` fsyncs the temp file but not its parent directory; doc comment at line 47 claims it does. Fix: either add a parent-dir `sync_all()` after the temp is in place, or update the doc to say parent fsync is deferred until commit completes.
- `commit.rs:247-263` — `best_effort_cleanup_backups` discards every unlink error; a backup that survives a successful apply is now an orphan recovery will try to restore over a live target. Fix: log the failure at `warn!` so users see leaked siblings; do not silently drop.

**Concurrency (1)**
- `main.rs:343-345` — `--threads` pool installed only around `plan_rewrite`; `apply_changes` (which calls `par_iter` in `stage_all`) and `plan_rewrite_scripted` run on the global pool. Fix: scope the pool across the whole pipeline (`pool.install(|| { plan_rewrite(...).and_then(|p| apply_changes(&p)) })`) and cover the scripted branch too.

**Memory (1)**
- `commit.rs:30-33` + `plan.rs:73-81` — `Staged` carries only paths but `FileChange::after` (the full post-image) and `FileChange::diff` (the rendered unified diff of the same change) are kept alive in `Plan` for the entire commit phase. Fix: drop `after` from `FileChange` (or move it into `Staged`) once `stage_one` has written it; the diff already encodes the new text.

**Complexity (1)**
- `commit.rs:178-216` — `commit_all` and `commit_all_with_hook` differ only by an extra fallible callback between iterations. Fix: collapse to one function taking `between_commits: impl Fn(usize) -> Result<()>` with a no-op default for production.

**Top targets**
1. `commit.rs:425-426` — clock-per-nonce in parallel hot path; hoist `SystemTime::now()` into `NonceGen::new()`.
2. `commit.rs:74-75` — backups unlinked before parent fsync; swap order so a crash between the two leaves recoverable state.
3. `main.rs:343-345` — `--threads` pool not scoped over the apply phase; install the pool around the full plan→apply pipeline.
4. `commit.rs:225-228` + `commit.rs:233-238` — rollback/recovery rename errors silently discarded; aggregate and surface so a half-restored tree is never reported as success.
5. `commit.rs:137-163` vs doc at line 47 — stage phase never fsyncs parent dir despite the contract; either add the syscall or correct the doc, then audit `recover_sweep` against whichever invariant wins.
