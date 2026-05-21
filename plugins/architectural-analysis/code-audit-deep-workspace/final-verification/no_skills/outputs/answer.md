# Architectural hotspots in `/home/mcs/Documents/git/recast`

`recast` is small (~4k LOC across 2 crates, 26 source files, no cycles). The dependency graph is a clean DAG with `error` at the leaf and `plan` / `commit` / `structural` at the top. There is no architectural rot to clean up — but there are five files that concentrate complexity, churn, or fan-in and are the right places to look first when something breaks or grows.

Ranked from most to least concerning.

## 1. `crates/recast-core/src/structural.rs` — god module (size + complexity)

`/home/mcs/Documents/git/recast/crates/recast-core/src/structural.rs`

- **652 lines, 22 items** (5 types, 17 functions). 2.8x the next-biggest core file.
- Owns four distinct responsibilities that should arguably be separate modules:
  1. `Language` enum + `ts_language()` grammar dispatch (lines 27–100) — feature-gated per language, 9 `#[cfg(feature = "lang-*")]` arms duplicated across `from_name` and `ts_language`.
  2. Rewrite-template parser (`parse_template`, `push_capture`, `flush_literal`, `TemplatePart`) (lines 113–311).
  3. Multi-file pipeline (`structural_rewrite`, `plan_structural_rewrite`, `plan_one`, `CompiledStructural`) (lines 132–408).
  4. Friendly `$NAME` → tree-sitter query compiler (`compile_friendly_query`, `substitute_metavars`, `emit_node`, `metavar_at`, `subtree_ellipsis_capture`, `format_query_error`, `escape_query_string`) (lines 427–648).
- Tied for top churn (5 commits in last 6 months, excluding tests/snapshots).
- Risk: every new tree-sitter grammar touches this file; the friendly-pattern compiler and the planner share no state but live in the same module.
- **Split candidate:** `structural/lang.rs` (Language registry), `structural/template.rs` (template parser), `structural/friendly.rs` (`--ast` compiler), `structural/plan.rs` (pipeline).

## 2. `crates/recast/src/main.rs` — CLI god file

`/home/mcs/Documents/git/recast/crates/recast/src/main.rs`

- **516 lines**, the only non-test file in the binary crate besides `completion.rs` (15 lines).
- Holds the entire CLI surface: 4 `clap` structs (`OutputOptions`, `GuardOptions`, `StructuralCli`, `Cli`), 11 functions, and every dispatch branch (`run`, `dispatch_plan`, `run_structural`, `run_stdin`, `emit_diff`, `emit_apply`, `handle_plan_error`, `acquire_workspace_lock_for`).
- Imports 14 symbols from `recast_core` (lines 10–15) — highest single-file fan-in to the library's public API.
- Three commits in 6 months, but every CLI feature lands here.
- Risk: new flags require touching both the struct and `Cli` accessor methods (`pattern_options`, `plan_options`, `min_matches`, `paths_as_pathbufs`, `recover_paths`) — easy to forget one wire-up.
- **Split candidate:** move the Args structs to `cli.rs`, the `emit_*` / `handle_plan_error` functions to `output.rs`, leave `main.rs` as the entry point + `run()` orchestrator.

## 3. `crates/recast-core/src/commit.rs` — high-churn safety-critical module

`/home/mcs/Documents/git/recast/crates/recast-core/src/commit.rs`

- **434 lines, 24 items** (the most items of any file). 6 commits in 6 months — **highest churn** in the codebase.
- Owns two-phase commit, rollback, recovery sweep, sibling-name parsing, and the per-apply `NonceGen`. Three of the recent commits are perf / refactor (per-apply NonceGen, planner-captured permissions, unix-only cfg).
- Safety-critical: this is the only place atomicity invariants live. The `apply_inner` test hook + `commit_all_with_hook` exist purely to exercise rollback paths — a smell that the code is hard to test through its public surface.
- Risk: any bug here corrupts user files. The high churn + the test-only hook duplication suggests the module is still finding its shape.
- **Worth watching:** the `parse_sibling_name` / `sibling_temp_name` / `SiblingKind` cluster is a mini-protocol for on-disk filenames; if it grows further it could move to `commit/sibling.rs`.

## 4. `crates/recast-core/src/plan.rs` — orchestration hub (high fan-out)

`/home/mcs/Documents/git/recast/crates/recast-core/src/plan.rs`

- **315 lines, 13 items.** Imports from **5 internal modules** (`error`, `pattern`, `rewrite`, `script`, `walker`) — tied with `structural.rs` for the highest internal fan-out. Re-exported by `lib.rs` as 7 public symbols.
- Fan-in: 5 other modules import from it (`commit`, `structural`, `json`, `proptests`, and the binary).
- Has both `plan_rewrite` and `plan_rewrite_scripted`, which share `scan`, `collect_changes`, `finalize_plan`, `process_one` — that abstraction is already paying off, but the two top-level functions still have visible structural duplication (compile, walk, par_iter, collect, finalize) around lines 112–181.
- **Hub status is intentional** (it's the pipeline assembly point), so the concern is keeping it from accreting a third `plan_*` variant. If a fourth mode is added (e.g. native LSP-aware), refactor to a `RewriteStrategy` trait instead of growing a parallel function.

## 5. `crates/recast-core/src/error.rs` — the universal sink (high fan-in)

`/home/mcs/Documents/git/recast/crates/recast-core/src/error.rs`

- **139 lines**, only 3 public items, but **14 internal use-sites** — by far the most-depended-on module in the workspace.
- This is healthy (it's the typed-error sink for the whole crate, exactly what `thiserror` is for), but it means any change to the `Error` enum touches everything. Adding a non-`#[non_exhaustive]` variant or renaming `IoCtx` is a workspace-wide edit.
- No action needed; flagged only because architectural-hotspot tooling would highlight it and the user should know it's load-bearing-but-fine.

---

## Quick reference

| File | LOC | Items | Fan-out | Fan-in | 6mo commits | Concern |
|---|---|---|---|---|---|---|
| `recast-core/src/structural.rs` | 652 | 22 | 4 | 0 | 5 | Size + 4 mixed responsibilities |
| `recast/src/main.rs` | 516 | 16 | (14 from core) | — | 3 | CLI god file |
| `recast-core/src/commit.rs` | 434 | 24 | 2 | 2 | **6** | Highest churn, safety-critical |
| `recast-core/src/plan.rs` | 315 | 13 | **5** | 5 | 3 | Pipeline hub, watch for 3rd variant |
| `recast-core/src/error.rs` | 139 | 3 | 0 | **14** | 1 | Universal sink (healthy, but load-bearing) |

## What is *not* a hotspot

- **No dependency cycles.** The internal `mod -> mod` graph is a clean DAG (verified by listing every `use crate::` edge).
- **No code duplication red flags.** Helpers like `label_for_path`, `unified_diff`, `read_text_or_skip_binary`, `check_match_counts`, and `template_scan::scan_*` are lifted into shared spots and reused by both the regex and structural pipelines — the DRY rule in `AGENTS.md` is being followed.
- `rewrite.rs`, `walker.rs`, `pattern.rs`, `json.rs`, `script.rs`, `lockfile.rs`, `parallel.rs`, `template_scan.rs` are all under 120 lines, single-purpose, low-churn. Leave them alone.

## Recommendation

If you only do one thing: **split `structural.rs`**. It's the biggest, mixes four responsibilities, and is the module most likely to grow (every new language adds two arms to it and the user-facing `--ast` compiler keeps gaining edge cases). The other four "hotspots" are doing their job; `structural.rs` is the only one whose shape is actively a liability.
