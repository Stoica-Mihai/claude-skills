# Audit: `crates/recast-core/src/commit.rs`

Scope: correctness and perf of the two-phase atomic-commit path, with extra attention to per-file syscalls in the parallel stage loop and silent failure modes on the rollback / recover paths.

Findings are ordered roughly by severity. Line numbers refer to `commit.rs` at `f9fc5d8`.

---

## H1. Durability ordering bug — backups deleted before parent dir is fsynced

`apply_changes` finalises a successful commit at `finalize_apply` (lines 71–80):

```rust
Ok(committed) => {
    debug!(files = committed.len(), "apply: commit phase complete");
    best_effort_cleanup_backups(&committed);   // deletes *.recast.bak.*
    best_effort_fsync_parents(&committed);     // fsync(parent)
    Ok(ApplyOutcome { ... })
}
```

The intended durability story (per the module-level docstring, lines 1–8) is: "On success, backups are removed and parent dirs are fsynced so the rename batch is durable." That ordering is the wrong way round.

What actually lands on disk:

1. `rename(original → backup)` and `rename(temp → original)` — durable only after a parent-dir fsync.
2. `unlink(backup)` — also only durable after a parent-dir fsync.
3. `fsync(parent)` — flushes the directory entry changes from steps 1 and 2 together.

If the process or machine crashes between step 2 and step 3, the kernel can replay the unlink of the backup without replaying the rename pair that put new content into place. Result: the new content is gone, the backup is gone, the original is gone — pure data loss on a successful-looking commit.

Fix:

```rust
best_effort_fsync_parents(&committed);     // make the rename pair durable first
best_effort_cleanup_backups(&committed);   // then we can safely retire the backups
best_effort_fsync_parents(&committed);     // (optional) make the unlinks durable too
```

The first fsync is the load-bearing one. The second is nice-to-have so the directory doesn't contain ghost `.recast.bak.*` entries after a crash; `recover_sweep` will tidy those on the next run regardless.

Severity: high. This is the canonical mistake atomic-rename code makes and the one the docstring explicitly claims to avoid.

---

## H2. `commit_one` rollback can silently lose a file

`commit_one` (lines 218–231):

```rust
fs::rename(&staged.target, &backup_path).io_ctx(&staged.target)?;

if let Err(e) = fs::rename(&staged.temp_path, &staged.target) {
    let _ = fs::rename(&backup_path, &staged.target);
    return Err(Error::Io { path: staged.target.clone(), source: e });
}
```

If the second rename (temp → target) fails after the first one moved the original aside, the code attempts to restore the backup with `let _ = …`. If *that* rename also fails (full disk, EACCES on a now-different inode owner after a permission race, EXDEV across a bind-mount boundary, NFS hiccup), then:

- the original file is gone from `target`,
- the temp is still sitting at `staged.temp_path`,
- the `Committed` record for this file is never pushed, so the outer `rollback_committed` will not touch it,
- the only signal returned to the caller is the *original* error from the temp→target rename — the rollback failure is silently discarded.

`recover_sweep` will fix the next run because the backup is still on disk. But the per-invocation contract ("either fully rewritten or bit-identical to the pre-image") is violated and the user is not told about it.

Minimum fix: chain the recovery error onto the primary error, or at minimum emit a `tracing::error!` so it isn't completely silent. Better: bubble a distinct `RollbackFailed { primary, secondary }` variant so the binary can exit with a louder code and tell the user to run `--recover`.

Severity: high (in the rare failure path) — silent data-loss-shaped behaviour in the disaster path.

---

## H3. `rollback_committed` performs an unnecessary unlink that widens the loss window

`rollback_committed` (lines 233–238):

```rust
for c in committed.iter().rev() {
    let _ = fs::remove_file(&c.target);
    let _ = fs::rename(&c.backup_path, &c.target);
}
```

On Unix, `rename(src, dst)` is atomic and overwrites `dst` unconditionally. The `remove_file` is therefore redundant. It is also actively harmful:

- Between the `remove_file` and the `rename`, `target` does not exist. A concurrent reader (another tool, an editor, an indexer) will see EEXIST → ENOENT → present-with-old-content, which is a flicker the atomic-rename idiom is supposed to make impossible.
- If `remove_file` succeeds but `rename` then fails, the file is gone and the backup is still sitting at `c.backup_path`. The user only sees the original Phase B error; the rename failure during rollback is `let _ =`-discarded (same problem as H2).

Fix: drop the `remove_file`. Rely on `fs::rename` to overwrite. If a rename-back fails, surface it.

Severity: medium-high. Today it papers over a non-issue (`rename` already overwrites), but the asymmetry creates the very failure window the module is designed to eliminate.

---

## M1. Stage phase silently drops all errors after the first

`stage_all` (lines 110–134):

```rust
let results: Vec<Result<Staged>> = changes.par_iter().map(...).collect();

let mut staged: Vec<Staged> = Vec::with_capacity(results.len());
let mut first_error: Option<Error> = None;
for r in results {
    match r {
        Ok(s) => staged.push(s),
        Err(e) => {
            if first_error.is_none() {
                first_error = Some(e);
            }
        }
    }
}
```

If three workers fail simultaneously, the user sees one of them (whichever sorted first in `changes` order). The other two are dropped on the floor with no trace. For a debug `RUST_LOG=debug` user trying to diagnose a permissions misconfiguration spanning multiple paths, this is unhelpful.

Suggestion: at minimum `tracing::warn!` each additional error before discarding. Or aggregate into a single `Error::StageFailed { first, others: Vec<Error> }` — but that's a bigger change and probably not worth it given the binary surfaces only the first.

Severity: medium. Information leak from the failure path, not a correctness bug.

---

## M2. Module docstring claims a stage-phase parent-dir fsync that doesn't happen

Lines 42–45:

> Phase A (stage): for every change, write the new content to a sibling temp file, fsync the temp, copy the original's permissions across, **and fsync the parent directory so the entry is durable**.

`stage_one` (lines 137–163) does not fsync the parent directory. The only parent-dir fsync is `best_effort_fsync_parents`, run after a successful commit phase.

That has two consequences:

1. If the process crashes between the end of stage and the start of commit, the `.recast.tmp.*` directory entries may not yet be on disk. `recover_sweep` handles missing temps gracefully (`target exists, no temps → no-op`), so this is not a *correctness* bug, but it does mean the on-disk state can diverge from what the code thinks it staged.
2. The docstring overstates what the code guarantees. Either implement the staged parent-dir fsync (one fsync per unique parent at the end of `stage_all`, deduped exactly like `best_effort_fsync_parents`) or correct the doc.

If you implement it, dedupe like H1's fsync — there's no point fsyncing the same parent N times for N files in one directory.

Severity: medium. Doc/code drift in a module whose entire job is durability semantics.

---

## M3. `apply_changes` ignores the user-configured rayon pool

`stage_all` does `changes.par_iter()` (line 114) on whatever ambient pool is active. In `crates/recast/src/main.rs` the `--threads N` pool is only installed around `plan_rewrite` (line 343):

```rust
let pool = build_pool(cli.threads).context(...)?;
pool.install(|| plan_rewrite(pattern, replacement, &paths, &opts))
```

`apply_changes(plan)` is called later, *outside* `pool.install` (line 362). So `--threads 1` will still parallelise the stage phase on `num_cpus()` workers. This is at minimum a surprise for users intentionally serialising for diagnosis (or for filesystem types — NFS, FUSE — where fanned-out fsync hurts).

Fix is in `main.rs`, not `commit.rs`: build the pool once and `pool.install(|| { plan; apply })` over both. But `commit.rs` could defend itself by accepting a `&ThreadPool` (or doing the work synchronously when `changes.len() == 1`).

Severity: medium. Bug in the binary, surfaced by the library's design.

---

## L1. Per-call `SystemTime::now()` in `NonceGen::next`

`NonceGen::next` (lines 422–429) calls `SystemTime::now()` on every nonce. The hot path stages one nonce per file (plus one per file in the commit phase, plus one per `recover_sweep` group). For a 10k-file run that's 20k clock-reads. `clock_gettime(CLOCK_REALTIME)` is a vDSO call on Linux so it's cheap (~20ns), but it's pointless work — the timestamp only needs to be sampled once per `NonceGen` to guarantee non-collision across runs.

Suggestion:

```rust
struct NonceGen {
    base: u64,           // sampled once at ::new
    counter: AtomicU64,
}

fn next(&self) -> u64 {
    let n = self.counter.fetch_add(1, Ordering::Relaxed);
    self.base.wrapping_add(n)
}
```

Severity: low. Perf-only, and the win is small.

---

## L2. Redundant `flush()` before `sync_all()`

`stage_one` (lines 150–152):

```rust
file.write_all(change.after.as_bytes()).io_ctx(&temp_path)?;
file.flush().io_ctx(&temp_path)?;
file.sync_all().io_ctx(&temp_path)?;
```

`std::fs::File::flush` is a no-op (the impl is `Ok(())`); `sync_all` calls `fsync(2)` which inherently flushes any kernel-side buffers. The `flush` line can go.

Severity: trivial. One syscall-free call per file.

---

## L3. `best_effort_cleanup_backups` and `best_effort_fsync_parents` log nothing on failure

Lines 247–263 discard every `Result` with `let _ =`. The names are honest about it being best-effort, but the only operator-visible signal that a backup couldn't be cleaned up (or a directory couldn't be fsynced) is that `recover_sweep` will list "removed N stale backup(s)" on the next run. Adding `tracing::debug!` (or `warn!`) lines makes those silent failures investigable.

Severity: low. Diagnostic.

---

## L4. `recover_sweep` is brittle against attacker-controlled filenames

`parse_sibling_name` (lines 383–396) trusts any file matching `.{stem}.recast.{bak|tmp}.{u64}` as a recast sibling. The `recover_sweep` walker is configured with `hidden(false).ignore(false).git_ignore(false).git_global(false).git_exclude(false)` (line 294), so it will pick up *any* file in the tree with that shape — including a planted file. In the target-missing case (line 333):

```rust
if let Some((_, newest)) = group.backups.pop() {
    fs::rename(&newest, &target).io_ctx(&newest)?;
    ...
}
```

A user with write access to the tree could plant `.foo.recast.bak.999` to make `recover_sweep` materialise `foo` from arbitrary content on the next sweep. This is mitigated in practice by the workspace lock around `--apply` / `--recover`, and the user could just create `foo` directly anyway, so the impact is mostly "surprising recovery behaviour" rather than a real escalation.

Severity: low. Worth a one-line note in the recover docstring.

---

## L5. `cleanup_remaining_staged` slicing is correct but unobvious

```rust
fn cleanup_remaining_staged(staged: &[Staged], remaining_count: usize) {
    let start = staged.len().saturating_sub(remaining_count);
    for s in &staged[start..] {
        let _ = fs::remove_file(&s.temp_path);
    }
}
```

The `saturating_sub` defends against the obvious off-by-one, and `commit_all` only ever sets `remaining_staged = staged.len() - i` (with `i ∈ 0..staged.len()`), so the saturation is dead. But the relationship is implicit. Passing the index of the failed file directly (instead of the remaining count) would make this self-evident and remove the saturating math. Style nit only.

Severity: trivial.

---

## L6. `Option<Permissions>` is dead in production

`stage_one` (line 155) handles `permissions: None` by skipping `set_permissions`. The planner (`plan.rs::process_one`, line 284) always sets `Some(permissions)`. So in any real run, the None branch never fires — and if it ever did fire, the temp would silently inherit the umask-default mode instead of the original's. Two options:

- Tighten the type to `Permissions` (not `Option<Permissions>`) in `FileChange` to make the invariant compile-checked.
- Or leave the type but `Error::Io { … "no permissions captured" }` in the None branch so a future bug surfaces instead of silently corrupting modes.

Severity: low. Latent.

---

## Perf summary (parallel stage hot path)

Per file, `stage_one` performs:

1. `parent_dir` — pure pointer arithmetic on the path.
2. `OpenOptions::open(create_new)` — 1 syscall (`openat` with `O_CREAT|O_EXCL`).
3. `write_all` — 1 syscall for small files, multiple for large; bounded by file size.
4. `flush` — 0 syscalls (no-op, see L2).
5. `sync_all` — 1 syscall (`fsync`), the dominant cost.
6. `drop(file)` — 1 syscall (`close`).
7. `set_permissions` — 1 syscall (`fchmodat`), only if `Some(perm)`.

That's roughly 4 syscalls + the fsync on the common path, per file, per worker. The kernel can overlap fsyncs across workers, so wall time scales with disk queue depth, not file count. Nothing pathological here. The biggest wins from the perf angle are not in `commit.rs` at all — they are:

- letting `--threads N` actually constrain the stage pool (M3),
- and (much smaller) the `flush`/`now()` micro-cleanups (L1, L2).

The commit phase is intentionally serial (line 113 comment), which is fine: rename is cheap and the determinism buys you the simple `rollback_committed` walk.

---

## Quick wins, ranked

1. **H1**: swap the order of `best_effort_cleanup_backups` and `best_effort_fsync_parents`. One-line fix that closes the worst correctness gap.
2. **H3**: drop the `fs::remove_file` in `rollback_committed`. Lets the atomic `rename` do its job.
3. **H2**: don't silently swallow the rollback `rename` failures in `commit_one` and `rollback_committed`. At minimum `tracing::error!`; better, a typed error.
4. **M2**: implement the stage-phase parent-dir fsync the docstring already promises, or correct the doc.
5. **M3**: `pool.install` around `apply_changes` in `crates/recast/src/main.rs` so `--threads` is honoured end-to-end.
6. **M1** + L3: log dropped errors in `stage_all` and the best-effort helpers.
7. **L1** + L2: micro-cleanups in `NonceGen::next` and `stage_one`.

---

## Things I checked and that look fine

- Nonce uniqueness across parallel stage workers: `AtomicU64::fetch_add` + monotonic counter is collision-free per `NonceGen`; cross-process collisions are made effectively impossible by mixing the start-of-apply nanosecond timestamp.
- `commit_all` is single-threaded; rollback ordering is deterministic by construction.
- `HashSet<&Path>` in `best_effort_fsync_parents` borrows from the committed entries' `target.parent()`, which lives as long as the `committed` slice — no lifetime hazard.
- `recover_sweep` is invoked from `crates/recast/src/main.rs` *after* `acquire_workspace_lock_for(&cli)`, so concurrent `--recover` is fenced by the same lockfile that fences `--apply`.
- `RecoverySummary::backups_restored` is incremented after the rename succeeds (line 335), so a mid-recovery error doesn't over-count. Counters are non-atomic because `recover_sweep` itself is serial.
- `parse_sibling_name` correctly handles edge cases: empty target name → None, missing `.recast.` separator → None, non-numeric nonce → None, missing leading `.` → None.
