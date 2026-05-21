**Perf (3)**
- `commit.rs:425-426` — `SystemTime::now()` syscall sampled per nonce, called twice per file (stage temp + commit backup) and inside the parallel stage loop. Fix: sample `ts` once in `NonceGen::new`, store as a field, return `seed.wrapping_add(counter.fetch_add)`.
- `commit.rs:298-322` — `recover_sweep` walks with `hidden(false).ignore(false).git_ignore(false)`, so `.git/` and `target/` are traversed on every recover; only the planner-visible subset needs scanning. Fix: re-use the project's `WalkOptions` (same filters as the planner) so the recovery sweep does not descend ignored trees.
- `commit.rs:253-263` — `best_effort_fsync_parents` opens and `sync_all`s each unique parent serially after a potentially-large commit batch. Fix: dedupe in a `HashSet<PathBuf>` collected during commit, then fan out across rayon to overlap parent-dir fsyncs.

**Correctness (5)**
- `commit.rs:117-127` — `stage_all` first-error-wins on a `par_iter().collect()`; every subsequent stage failure is silently dropped. User explicitly flagged this. Fix: at minimum `tracing::warn!` each suppressed error with its path before returning the first; better, aggregate into a multi-error variant.
- `commit.rs:225-228` — `commit_one`'s inner rollback discards the `fs::rename(backup → target)` result; if the restore itself fails the target is gone, only the original rename error reaches the caller, and the orphaned backup path is never reported. Fix: on restore failure, `error!` with both paths so the user can recover by hand.
- `commit.rs:233-238` — `rollback_committed` swallows every `remove_file` and `rename` result; a rollback that partially fails leaves originals deleted with no signal whatsoever. Fix: `warn!` per failed path inside the reverse walk; do not silently return `()`.
- `commit.rs:247-251` — `best_effort_cleanup_backups` discards every `remove_file` error; stale `.recast.bak.*` siblings accumulate undetected on permission/ENOSPC. Fix: log at `debug!` per failure with path so `recover_sweep` consumers know why leftovers exist.
- `commit.rs:343-348` — `remove_nonced` aborts on first `remove_file` failure with `?`, but `RecoverySummary` counts only the successful removals already taken; caller sees an error plus a partially-mutated tree with no record of what got cleaned. Fix: continue past failures, collect them, return both summary and a `Vec<(PathBuf, io::Error)>` (or accumulate into the summary).

**Durability/ordering (3)**
- `commit.rs:72-79` — success path runs `best_effort_cleanup_backups` *before* `best_effort_fsync_parents`; on crash between the two, the rename batch may revert and the backups it needed are already unlinked. Fix: swap order — fsync parents first, then unlink backups.
- `commit.rs:137-163` — `stage_one` fsyncs the temp file but never fsyncs the parent directory before phase B begins, so a crash between stage and commit can lose the temp entry entirely. Fix: fsync each unique parent at the end of `stage_all` (dedup + parallel) before returning.
- `commit.rs:218-231` — `commit_one` issues two renames without fsyncing the parent between/after them; on crash mid-batch a partially-renamed directory may not be observable, defeating rollback. Fix: at minimum fsync the parent after each successful commit, or batch-fsync after each per-directory group.

**Concurrency (1)**
- `commit.rs:110-114` — `par_iter()` uses the global rayon pool, so `--threads N` (installed elsewhere as a scoped pool around the planner) does not bound stage concurrency unless the apply path also runs inside that scope. Fix: pass the `ThreadPool` down and `pool.install(|| changes.par_iter()…)` so the user's `--threads` flag actually constrains the stage phase.

**Correctness — recovery semantics (1)**
- `commit.rs:326, 333` — `recover_sweep` sorts backups by the scrambled nonce (`ts.wrapping_mul(0x9E37...).wrapping_add(n)`) and pops the largest, calling it "newest". The multiplicative mix means a later wall-clock does not yield a larger nonce, so the "newest backup" pick is effectively arbitrary across interrupted applies. Fix: pick by `fs::metadata(p)?.modified()` instead, or change the nonce to `(ts << 20) | counter` so high bits stay monotonic.

**Complexity (1)**
- `commit.rs:178-216` — `commit_all` and `commit_all_with_hook` are byte-for-byte identical except for the test-only `between_commits` callback, duplicating the `CommitFailure` construction logic. Fix: collapse to one `commit_all_inner(staged, nonces, hook: Option<&dyn Fn>)` and have the `cfg(test)` wrapper pass `Some(&f)`.

**Top targets**
1. `commit.rs:72-79` — swap cleanup/fsync ordering on the success path; canonical durability bug.
2. `commit.rs:425-428` — hoist `SystemTime::now()` out of `NonceGen::next`; per-element syscall in the parallel hot path.
3. `commit.rs:326, 333` — replace scrambled-nonce sort with mtime-based "newest backup" pick in `recover_sweep`; current logic restores an arbitrary backup, not the latest.
4. `commit.rs:233-238` + `commit.rs:225-228` — surface rollback failures (originals lost silently today); `warn!`/`error!` per path inside the reverse walk and on the inner commit-rename failure.
5. `commit.rs:137-163` — fsync each unique parent dir at the end of `stage_all` before phase B; closes the stage-durability gap that defeats rollback if the host crashes between phases.
