**Perf (3)**
- `commit.rs:425-426` — `SystemTime::now()` called per nonce. Fix: capture once in `NonceGen::new()`, mix counter only in `next()`.
- `commit.rs:328` — `target.exists()` stat per recovery group. Fix: record live targets in a `HashSet` during the walk and probe that.
- `commit.rs:114` — `par_iter().map(...).collect()` materializes a `Vec<Result<Staged>>` only to fold it. Fix: stream-fold with `try_fold` + `reduce`, or use `Mutex<Vec<Staged>>` so failures short-circuit without allocating the intermediate vec.

**Correctness (6)**
- `commit.rs:226` — restore rename in `commit_one` failure path uses `let _ =`. Fix: log at warn and surface a richer error wrapping both the temp-rename and restore failures.
- `commit.rs:233-237` — `rollback_committed` swallows every `remove_file` / `rename` failure with `let _ =`. Fix: collect failures and attach them to the returned error (or at minimum `warn!` each).
- `commit.rs:260` — `let _ = dir.sync_all()` defeats the durability claim in the module doc. Fix: `warn!` on failure so silent data loss is observable in logs.
- `commit.rs:117-127` — `stage_all` keeps only `first_error`; other parallel stage errors are dropped without trace. Fix: log each dropped error at debug/warn before discarding.
- `commit.rs:130` — `let _ = fs::remove_file(&s.temp_path)` in stage-error cleanup. Fix: `trace!`/`warn!` failures so leaked temps that bypass `recover_sweep` are diagnosable.
- `commit.rs:333-334` — `group.backups.pop()` + `rename` restores the newest backup, but `parse_sibling_name` accepts arbitrary attacker-controlled `.recast.bak.N` siblings; recover may resurrect a file the user never wrote. Fix: only act on backup groups where the target was missing AND the parent dir was emitted by the walk under a `--recover` root the user explicitly asked for (and gate restoration behind a `--yes`-style flag, or restrict to a recast-owned marker).

**Complexity (3)**
- `commit.rs:178-216` — `commit_all` and `commit_all_with_hook` are near-duplicates differing only by the test hook. Fix: collapse to one function taking `Option<&dyn Fn(usize) -> Result<()>>` (or `()` no-op default), drop the cfg(test) twin.
- `commit.rs:52-108` — `apply_changes` and `apply_inner` duplicate the empty-plan check and stage pipeline. Fix: have `apply_changes` delegate to `apply_inner` with a no-op hook.
- `commit.rs:283-341` — `recover_sweep` does walker config + parse + grouping + restore + cleanup in one 60-line body. Fix: split into `collect_recovery_groups` and `reconcile_group` so each step is unit-testable in isolation.

**Coupling (1)**
- `commit.rs:143 + plan.rs:80` — `commit::stage_one` reads `FileChange.permissions` while `plan::process_one` writes them solely to feed the commit phase; the field exists only to ferry data between the two modules. Fix: keep as-is but document the contract on `FileChange.permissions`, or introduce a thin `StagedInput` type owned by `commit.rs` so the coupling is explicit instead of implicit through a shared struct.

**Top targets**
1. `commit.rs:425-426` — hoist `SystemTime::now()` out of `NonceGen::next`; capture once in `new()`, increment counter only.
2. `commit.rs:226 + 233-237` — stop swallowing rollback / restore-rename errors; aggregate or `warn!` so partial-state failures are observable instead of silent.
3. `commit.rs:260` — make `best_effort_fsync_parents` log on failure so the module doc's "durable" claim is enforceable.
4. `commit.rs:178-216 + 98-108` — collapse the `commit_all` / `commit_all_with_hook` and `apply_changes` / `apply_inner` duplications behind an optional hook parameter.
