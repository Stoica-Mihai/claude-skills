**Perf (5)**
- `commit.rs:426` — `NonceGen::next` calls `SystemTime::now()` per nonce, fired inside the `par_iter` stage loop and again per commit. Fix: capture `ts` once in `NonceGen::new`, store as field, combine with counter only.
- `commit.rs:114` — `par_iter().map(...).collect::<Vec<Result>>()` materializes every per-file stage result before checking for errors; a failing first file still does N-1 fsyncs of doomed temps. Fix: use `try_fold` / `try_reduce` (or an `AtomicBool` abort flag checked inside `stage_one`) to short-circuit on first error.
- `commit.rs:151` — `file.flush()` before `sync_all()` on a raw `std::fs::File`; `File` is unbuffered, so `flush` is a no-op syscall per staged file. Fix: drop the `flush` call.
- `commit.rs:328` — `recover_sweep` does a `target.exists()` syscall per recovery group instead of recording target presence during the single `WalkBuilder` pass that already visited every file. Fix: insert non-recast filenames into a `HashSet` during the walk and look up instead of calling `exists`.
- `commit.rs:143` — `change.permissions.clone()` clones the `Option<Permissions>` per file inside the parallel stage; immediately followed by passing it by value to `set_permissions`. Fix: drop the binding and pass `change.permissions.as_ref().cloned()` only at the `set_permissions` site, or borrow via `&change.permissions`.

**Correctness (7)**
- `commit.rs:233` — `rollback_committed` does `remove_file(target)` then `rename(backup, target)`; if `remove_file` fails the subsequent rename fails because target still exists, both errors swallowed by `let _ =`, leaving the file in committed (new) state while the caller is told "rolled back". Fix: do a single `fs::rename(backup, target)` (atomic replace on POSIX) and at minimum collect the per-step errors into the returned `Error`.
- `commit.rs:253` — `best_effort_fsync_parents` ignores every `sync_all` and `File::open` error with `let _ =`, yet the module docstring promises "parent dirs are fsynced so the rename batch is durable". A silent EIO here returns `Ok(ApplyOutcome)` with a non-durable batch. Fix: aggregate fsync errors and surface them as a distinct `Error::DurabilityWarning` (or at minimum log at warn level, not trace).
- `commit.rs:225` — when the second rename in `commit_one` fails, the rollback `fs::rename(backup_path, target)` is `let _ =`'d; if recovery fails the original file is now only at `backup_path`, but the returned `Error::Io` reports just the second rename's error, not the catastrophic "original is at .recast.bak.N, target is missing" state. Fix: on recovery-rename failure, return a richer error variant that carries `backup_path` so the caller can warn the user / point them at `--recover`.
- `commit.rs:233` — `rollback_committed` performs no parent-dir fsync after the restore renames; a crash immediately after rollback can leave the tree in the committed-new state on next boot. Fix: dedupe parents and `sync_all` each one after the rollback walk.
- `commit.rs:329` — `recover_sweep` aborts the whole sweep on the first `fs::remove_file` failure via `?`; one stuck leftover prevents recovery of every later target. Fix: collect per-group errors into the `RecoverySummary` (or a `Vec<Error>`) and only fail hard at the end.
- `commit.rs:117` — `stage_all` keeps only the first error and silently drops every other parallel-stage failure; if file A fails EPERM and file B fails ENOSPC, the user sees only one. Fix: aggregate into `Vec<Error>` and return a multi-error variant, or at minimum log the discarded ones at warn level.
- `commit.rs:334` — `recover_sweep` selects the "newest backup" by sorting on the nonce value, but nonces are `ts.wrapping_mul(GOLDEN).wrapping_add(counter)` — multiplying by the golden-ratio constant permutes timestamp ordering, so the sort does not actually pick the most recent backup. Fix: parse the nonce as a tuple of (ts, counter) by storing them separately in the filename, or use file mtime as the tiebreaker.

**Memory (1)**
- `commit.rs:114` — `stage_all` collects `Vec<Result<Staged>>` of length N then re-iterates to split successes from failures, holding two vectors transiently. Fix: fold directly into `(Vec<Staged>, Option<Error>)` inside the rayon reducer.

**Complexity (2)**
- `commit.rs:178 + commit.rs:194` — `commit_all` and `commit_all_with_hook` differ only by the post-commit hook call; near-identical loops, near-identical `CommitFailure` construction. Fix: collapse into one function that takes `Option<&dyn Fn(usize) -> Result<()>>` (or always pass a no-op hook in production).
- `commit.rs:283` — `recover_sweep` does walker setup, sibling-name parsing, group bucketing, target-existence check, restore, and cleanup in one ~60-line function. Fix: extract `collect_groups(roots) -> HashMap<...>` and `reconcile_group(target, group) -> Result<...>` so the policy is testable in isolation.

**Coupling (1)**
- `commit.rs:143 + plan.rs:67-80` — `commit.rs` reaches into `FileChange.permissions` (an `Option<Permissions>`) specifically to avoid a second `fs::metadata` syscall, which is documented in `plan.rs`. The optimization is shared between the two modules via a public struct field that the commit phase mutates the meaning of. Fix: encapsulate as `FileChange::stage_permissions(&self) -> Option<&Permissions>` so the contract is one-sided, not "commit knows what planner stuffed in".

**Top targets**
1. `commit.rs:426` — hoist `SystemTime::now()` out of `NonceGen::next`; biggest perf win, called once per stage + once per backup name per file.
2. `commit.rs:233` — rewrite `rollback_committed` to use a single atomic `fs::rename` and stop swallowing errors; this is the worst silent-failure path in the file.
3. `commit.rs:253` — surface (or at least warn-log) fsync errors in `best_effort_fsync_parents` so the documented durability guarantee is not silently violated.
4. `commit.rs:114` — short-circuit `stage_all` on first error to stop doing N-1 wasted fsyncs after a stage failure.
