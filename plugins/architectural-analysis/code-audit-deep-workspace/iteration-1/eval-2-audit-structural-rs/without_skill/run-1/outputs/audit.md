# Audit: `crates/recast-core/src/structural.rs`

Scope: file-internal complexity, unbounded-recursion risk on parser input, and coupling against `plan.rs`. Grounded in the source at the time of audit (commit `f9fc5d8`).

---

## 1. At-a-glance

`structural.rs` is ~650 lines covering five distinct concerns wedged into one module:

| Concern | Functions / types | Approx. lines |
|---|---|---|
| Language registry | `Language` + `ts_language` | 30–100 |
| Compiled job + per-file apply | `CompiledStructural`, `Hit`, `TemplatePart` | 100–250 |
| Template parser (`$NAME`, `${NAME}`) | `parse_template`, `push_capture`, `flush_literal` | 248–311 |
| Multi-file pipeline | `structural_rewrite`, `plan_structural_rewrite`, `plan_one` | 313–408 |
| `--ast` friendly-pattern compiler | `structural_rewrite_friendly`, `compile_friendly_query`, `substitute_metavars`, `emit_node`, `metavar_at`, `subtree_ellipsis_capture`, `escape_query_string`, `format_query_error` | 410–648 |

The first four concerns mirror `plan.rs` cleanly. The fifth (the `--ast` friendly compiler) is a meaningful chunk of new logic with its own recursion, its own tree-sitter parser instance, and its own metavar conventions. That is where the bulk of the complexity and risk lives.

---

## 2. Function-level complexity

### 2.1 `CompiledStructural::apply` (168–216)
- Two passes over `hits` (sort + size-hint sum + splice). Reasonable.
- Two awkward parts:
  - Lines 180–188: picking the "primary" capture. When `@root` is absent, it picks the **highest-numbered capture index that any iter call produced** — *not* a stable named capture and *not* the outermost node. With queries like `((identifier) @id (#eq? @id "x"))` the only capture is `@id` so the behavior is fine, but with a multi-capture query the choice is order-dependent and surprising. This deserves either an explicit doc note or a deterministic "first declared" / "outermost node" rule. The match-on-failure error message ("match did not bind primary capture index N") would also be useless to a CLI user — they want a capture *name*, not an index.
  - Lines 200–202: `saturating_sub` for the capacity hint is correct in spirit but `replacement.len() - (end - start)` can be negative when the rewrite *shrinks* text; the saturating arm hides the over-allocation but the capacity is still a best-effort hint and that's fine.
- Cyclomatic complexity is moderate (~6 branches). Splitting into `collect_hits` and `splice_hits` would let each fit on a screen and would let `plan_one` reuse hit collection if a future caller wants raw hits without splicing.

### 2.2 `compile_friendly_query` (440–480)
- Five concerns in one function: substitute metavars, build a parser, parse, error-format, unwrap `source_file`, walk + format query.
- Magic string `"source_file"` is grammar-dependent. Most tree-sitter grammars use that name, but not all — `tree-sitter-md`, for example, exposes `document`. Today the code would fail-open (skip the unwrap and emit a `(document …)` pattern that probably won't match anything useful) rather than misbehave, but the silent disagreement is a future foot-gun. Worth a per-language root-kind table.
- The "no predicates → bare pattern, predicates → wrap in extra parens" branching at the end (475–479) produces subtly different surface syntax. If the inner pattern is a leaf that ends up rendered as e.g. `(identifier) @__lit0 @root`, the wrapping in `({trimmed} @root …)` produces `((identifier) @__lit0 @root @root …)` — note the duplicate `@root`. Worth a snapshot test for the predicate path with a single-leaf pattern (no current test seems to cover it; `friendly_pattern_renames_function` uses `fn old_one() {}` which has children).

### 2.3 `emit_node` (513–561) — **recursion site, see §3**
- Mixed responsibility: kind dispatch (ellipsis / metavar / leaf-with-literal / interior), buffer mutation, predicate accumulation, counter mutation. Five parameters threaded through every recursive call.
- The leaf-as-literal branch hard-codes `(#eq? @__litN "…")`. That is fine for identifiers/integers; for any leaf whose text contains arbitrary user content it relies on `escape_query_string`, which only escapes `"`, `\\`, `\n`. A literal containing a CR, tab, or any other control byte will produce a query string that's technically valid but may be re-parsed differently by tree-sitter's query parser depending on grammar — low likelihood, but worth at least a test for `\t` and `\r`.

### 2.4 `subtree_ellipsis_capture` (619–648) — **recursion-free via explicit stack, good**
- The function name suggests "walk *the* ellipsis". The actual semantics are: *if the subtree contains exactly one ellipsis identifier and nothing else of substance, collapse to one wildcard*. The "nothing else of substance" rule means `other_leaves > 0` aborts. Consider renaming to `subtree_collapses_to_ellipsis` or `ellipsis_dominates_subtree` for the call site at line 523 to read true.
- The `?` on `n.utf8_text(src).ok()?` (line 628) silently propagates `None` from a UTF-8 failure on a leaf. Tree-sitter never emits non-UTF-8 spans for source we just verified parses, so this is safe in practice, but the early return swallows a *partial* traversal — if the offending leaf is the third of ten siblings, the seven remaining siblings are never inspected. Behaviorally fine (we abort to "no ellipsis"), but worth a `debug_assert!` or a comment.

### 2.5 `parse_template`, `substitute_metavars`
- Near-mirror byte walkers. Both use `template_scan` helpers, both fall through to `out.push(b as char)` on the no-match path. The two could share a single "scan token" helper if you wanted (`tokenize_metavars(bytes, on_meta, on_ellipsis, on_braced)`), though at ~30 lines apiece they're already short.
- `parse_template` at 281: `literal.push(b as char)` is a **latent UTF-8 bug**. Casting a raw `u8` to `char` produces the Latin-1 codepoint, which is wrong for any multi-byte UTF-8 sequence: `"é"` (bytes `c3 a9`) becomes `"Ã©"` in the output literal. This will silently corrupt non-ASCII template literals. Same bug in `substitute_metavars` at line 507. Fix: iterate with `template.chars()` over a `(byte_idx, char)` cursor (e.g. `char_indices`), or push the slice between scan boundaries with `out.push_str(&template[lit_start..i])` and a `lit_start` cursor.

### 2.6 `plan_structural_rewrite` (341–382)
- 99% mechanical duplication of `plan_rewrite` in `plan.rs` (see §4). The non-mechanical differences are:
  - No convergence check (correct — tree-sitter rewrites aren't probed against their own output).
  - `Plan` short-circuit at `total_matches == 0` returns `AlreadyApplied` **without consulting `opts.at_least`** (line 372). `plan.rs::finalize_plan` does the same thing but only when `convergent_or_scripted` is true. Behaviorally aligned, but the duplicated short-circuit logic guarantees these two paths will drift.
- The compiled query is built before the file walk runs. Fine, but reorder so a `TooManyFiles` error surfaces before tree-sitter is invoked at all — saves grammar startup cost on accidental scans of a huge tree.

### 2.7 `format_query_error` (567–586)
- Self-contained, well-tested (lines 55–71 of the tests). One thing: `caret_col` is computed in *byte* columns from tree-sitter, but a `" ".repeat(caret_col)` assumes one column = one display cell. With non-ASCII source the caret will land too far left. Low priority — error messages — but worth a comment.

---

## 3. Unbounded recursion on parser input

This is the audit's most consequential finding.

### 3.1 `emit_node` is the only true recursion site

```rust
fn emit_node(buf, predicates, lit_counter, node, src) {
    …
    for child in node.named_children(&mut cursor) {
        emit_node(buf, predicates, lit_counter, child, src);   // line 558
    }
    …
}
```

`emit_node` recurses once per named child, with no depth budget. Tree-sitter does not impose a depth limit on parse trees; you can construct a syntactically valid source whose AST has arbitrary depth. Two realistic inputs that defeat this:

1. **Deeply nested expressions.** A pattern like `((((((((((x))))))))))` with thousands of parens parses into a chain of `parenthesized_expression` nodes. Each adds one stack frame.
2. **Deeply nested blocks / function calls.** `{ { { { … } } } }` or `f(f(f(f(...))))` — same shape.

Stack-frame size for `emit_node` is dominated by:
- 5 function args
- a local `tree_sitter::TreeCursor` (`node.walk()`, ~24 bytes plus the FFI-managed cursor)
- the for-loop's iterator state

Conservatively ~200 bytes per frame. Rust's default thread stack is 8 MiB on Linux (and `rayon` workers default to 2 MiB or smaller depending on version). A pattern with ~10k nested parens — easily within a normal source file's character budget — would overflow a rayon worker. The result is a process abort, not a recoverable error: the planner short-circuits and the user sees a SIGABRT/SIGSEGV with no diagnostic.

The risk vector here is **pattern input**, not source input — `emit_node` walks the *parsed pattern*, which comes from `--ast` on the CLI. So the practical attacker is whoever supplies the pattern: an LLM agent or a CI job feeding a generated pattern. The same input through `--query` skips `emit_node` entirely.

**Recommendation.** Either:

- Convert `emit_node` to an explicit stack/work-queue (same shape as `subtree_ellipsis_capture` already uses), OR
- Add a depth-cap guard at the top of `emit_node` (e.g. `MAX_PATTERN_DEPTH = 256`) and surface a typed `StructuralQuery` error when exceeded.

The explicit-stack rewrite is preferable because it removes the failure mode entirely and matches the codebase's existing pattern at line 622.

### 3.2 `subtree_ellipsis_capture` is already iterative — good

Uses an explicit `Vec<Node>` stack. No recursion. Memory is bounded by the subtree's node count, which is bounded by the pattern's parsed-tree size.

### 3.3 The tree-sitter parser itself

Tree-sitter is a GLR-style parser implemented in C, with its own stack management. `parser.parse(source, None)` can return `None` on extreme inputs but does not stack-overflow the host process in normal use. Not a `recast` concern, but worth noting: tree-sitter's C-side recursion is independent of Rust's stack.

### 3.4 `apply` and `render` — no recursion

Both are loops over `Vec`s. Capacity is bounded by `Query` match count, which is bounded by parsed-tree size, which is bounded by `source.len()`. Memory growth is `O(source.len() + Σ replacement.len())` — fine.

### 3.5 `--max-bytes` does not gate the stdin path

`run_structural` in `crates/recast/src/main.rs` at line 386 reads stdin into a `String` with no length cap, then calls `structural_rewrite` on the entire buffer. The `--max-bytes` knob in `PlanOptions` only applies to walk-discovered files. An LLM agent piping multi-GB content into `recast --lang rust --ast '…' --apply` via stdin will be OOM'd by the read, not by `recast`. Worth either applying `max_bytes` to the stdin read or documenting that stdin mode is unbounded.

---

## 4. Coupling vs. `plan.rs`

Both files are "orchestrator" files in the same crate, and they pull in the same primitives:

| Shared primitive | Used by `plan.rs` | Used by `structural.rs` |
|---|---|---|
| `walk_paths` | yes (via `scan`) | yes (inline, line 348) |
| `read_text_or_skip_binary` | yes | yes (line 391) |
| `unified_diff` / `label_for_path` | yes | yes (line 400) |
| `check_match_counts` | yes (in `finalize_plan`) | yes (line 380) |
| `rayon::par_iter().map_init` | yes (scripted path) | yes (line 358) |
| `FileChange` / `Plan` / `PlanOutcome` | defined here | imported from plan |

### 4.1 The clear coupling problem: `plan_structural_rewrite` duplicates the pipeline shape

Compare `plan.rs::plan_rewrite_scripted` (151–181) and `structural.rs::plan_structural_rewrite` (341–382). Modulo the rewriter type, they are the same six steps:

1. compile (`CompiledPattern` vs `CompiledStructural`)
2. `scan(roots, opts)` (inlined in structural — see §4.3)
3. `par_iter().map_init` worker spin-up
4. `collect_changes`
5. `total_matches` fold + zero-match short-circuit
6. `check_match_counts` + final `Plan` assembly

Steps 4, 5, and 6 are factored into helpers (`collect_changes`, `finalize_plan`) in `plan.rs`. `structural.rs` re-implements all three inline. That's the actual smell: not the duplication of the worker harness (which is parametric over `Pattern`/`Rewriter` and reasonably hard to unify cleanly with rayon's trait bounds), but the duplication of the **post-processing** that's already factored.

Concrete refactor:

- Re-export `collect_changes` and `finalize_plan` from `plan.rs` (currently private), or move them to a `plan::pipeline` submodule with `pub(crate)` visibility.
- Have `plan_structural_rewrite` call `collect_changes(results)?` and `finalize_plan(changes, /* convergent_or_scripted: */ true, files_scanned, opts)`. The "structural is always treated as convergent" intent then lives in one call site instead of two duplicated branches.
- Replace the inlined `if files.len() > opts.max_files` with a `scan` call (currently `pub(crate)` would suffice; it's `fn scan` private to `plan.rs`).

### 4.2 The `read_text_or_skip_binary` story is healthy

`plan.rs` already exposes `read_text_or_skip_binary` as `pub(crate)` (line 293) precisely so `structural.rs` can reuse it. That pattern — exposing exactly what's needed across the orchestrators and nothing more — is the model the post-processing helpers above should follow.

### 4.3 `scan` should also be `pub(crate)`

`plan.rs::scan` (183–190) is identical to `structural.rs::plan_structural_rewrite` lines 348–351. Lifting it to `pub(crate)` and using it from `structural.rs` removes nine lines and centralizes the `TooManyFiles` error wording.

### 4.4 Wrong-direction coupling concern

`structural.rs` imports from `plan.rs` (line 14): `FileChange`, `Plan`, `PlanOptions`, `PlanOutcome`, `check_match_counts`, `read_text_or_skip_binary`. Six items. That's a lot, but every one of them is genuinely shared domain — the cleaner fix is to extract a `pipeline` module with these types and shared helpers, then have both `plan.rs` and `structural.rs` consume *that* module:

```
crates/recast-core/src/
  pipeline/
    mod.rs            # PlanOptions, Plan, PlanOutcome, FileChange, check_match_counts
    io.rs             # read_text_or_skip_binary
    finalize.rs       # collect_changes, finalize_plan, scan
  plan.rs             # regex/scripted-specific entry points
  structural.rs       # tree-sitter-specific entry points
```

This makes the dependency graph `plan ← pipeline → structural` instead of `plan ← structural`. The current arrangement is fine for now (recast is alpha), but the moment you add a third pipeline mode the duplication doubles.

### 4.5 `PlanOptions` has fields that don't apply to structural

`allow_non_convergent`, `pattern_options` are meaningless in structural mode. `plan_structural_rewrite` silently ignores them. That's a category of "agent foot-gun" — the kind `recast` is explicitly designed to avoid. Two options:

- Split into `PlanOptions { common, mode: ModeOpts }` where `ModeOpts` is `Regex { … } | Structural`.
- Or, accept the simplicity tax and document the ignored fields on `PlanOptions::pattern_options` / `allow_non_convergent` with `// ignored in structural mode`.

The first option is the right one before a 1.0; the project's AGENTS.md explicitly says no backwards-compat shims pre-1.0, so the cost is just the refactor itself.

---

## 5. Smaller findings

- **Line 164**: `let _ = parser.set_language(&self.ts_lang);` discards a `Result` whose failure was promised infallible by the `compile()`-time probe. The comment correctly explains why, and `parser.parse(...)` returning `None` on an unset parser is mapped to `Error::StructuralParse` at line 174 — defensible. Consider tightening to `parser.set_language(&self.ts_lang).expect("ABI validated in compile()")` only if you trust the invariant; the silent-ignore is actually the safer choice here.

- **Line 281 / 507 — UTF-8 corruption** (already noted in §2.5): `literal.push(b as char)` lossily reinterprets multibyte UTF-8 sequences as Latin-1 codepoints. Existing tests don't exercise non-ASCII template literals. Add a regression test like:
  ```rust
  let out = structural_rewrite_friendly(Language::Rust, "fn α() {}", "fn $NAME() {}", "// α: $NAME\nfn $NAME() {}").unwrap();
  ```
  and watch it fail on the comment line.

- **Line 467**: `root.named_child(0).ok_or_else(...)` after `root.named_child_count() >= 1` — the precondition makes this unreachable, but the error message ("empty pattern") would mislead if reachable. Either drop the bound check on `named_child_count` and rely on `ok_or_else`, or downgrade to `unreachable!()` with an invariant comment.

- **Line 542 / 544**: the `let _ = write!(...)` pattern correctly silences the `Result` from `Write` impl for `String` (which never errors). Idiomatic. But the format-string assembly via `write!` into a fresh `String` for each predicate (line 543) is mildly wasteful — push into a shared scratch buffer or use `format!` directly. Micro.

- **`Hit` struct (121–125)**: `replacement: String` per hit means each match allocates a fresh `String`. For huge files with thousands of matches, an arena or `&str` slicing into a shared bump would win. Not urgent.

- **No fuzzing surface**: `parse_template`, `substitute_metavars`, and `compile_friendly_query` are pure string-in/string-out transforms with no panics on the happy path but a meaningful surface for malformed input. `proptests.rs` exists in the crate; adding `proptest!` cases over these three would be cheap insurance.

- **`Language::ts_language` panics if the feature flag set produces an empty enum** — impossible today because `lib.rs:21-27` only compiles the module when at least one `lang-*` feature is enabled. Worth a `#[allow(dead_code)]` comment or matching `#[cfg]` on the impl block, but not a real bug.

---

## 6. Priority queue (what to fix first)

1. **Bound recursion in `emit_node`** (§3.1). Either explicit stack or depth cap. Without this, `--ast` is a process-stability risk under adversarial or LLM-generated patterns.
2. **Fix UTF-8 corruption** in `parse_template` (line 281) and `substitute_metavars` (line 507). One-line fix per site (use `char_indices` or slice-based literal accumulation), plus a regression test.
3. **Apply `max_bytes` to the stdin path** in `run_structural` (caller side), or document the unbounded read. Two-line fix.
4. **Lift `scan`, `collect_changes`, `finalize_plan`** to `pub(crate)` in `plan.rs` and use them from `structural.rs`. Removes ~25 lines of duplication and centralizes the zero-match / `at_least` / `TooManyFiles` semantics.
5. **Replace `primary_idx = max(index)`** in `apply` (line 182) with a deterministic rule (first declared capture, or outermost-node by start byte), and improve the error message to use the capture *name*.
6. **Split `PlanOptions`** along regex / structural lines, or annotate the ignored fields. Pre-1.0 is the cheap moment.
7. **Snapshot test for the friendly-pattern `predicates.is_empty() == false` branch** (line 478) to lock down query-string shape.

Items 1–3 are correctness/safety; 4–7 are maintainability and ergonomics.

---

## 7. What the file gets right

- Clear separation of "compile once / apply per-file" — `CompiledStructural` is the right abstraction.
- Per-thread `Parser` + `QueryCursor` via `map_init` matches what `plan.rs` does for scripted rewrites; the rayon shape is consistent.
- `format_query_error` (§2.7) is genuinely user-friendly, and it's tested.
- `subtree_ellipsis_capture` uses an explicit stack — the pattern to apply to `emit_node`.
- `read_text_or_skip_binary` is correctly shared from `plan.rs` rather than re-implemented. That's exactly the coupling discipline the rest of the file should follow.
- The feature-flag matrix on `Language` variants is mechanical but correct, and the `from_name` mapping covers the common aliases (`rs`, `py`, `sh`, `golang`, `md`).

---

## Files referenced

- `/home/mcs/Documents/git/recast/crates/recast-core/src/structural.rs`
- `/home/mcs/Documents/git/recast/crates/recast-core/src/plan.rs`
- `/home/mcs/Documents/git/recast/crates/recast-core/src/template_scan.rs`
- `/home/mcs/Documents/git/recast/crates/recast-core/src/rewrite.rs`
- `/home/mcs/Documents/git/recast/crates/recast-core/src/error.rs`
- `/home/mcs/Documents/git/recast/crates/recast-core/src/lib.rs`
- `/home/mcs/Documents/git/recast/crates/recast-core/src/structural_tests.rs`
- `/home/mcs/Documents/git/recast/crates/recast/src/main.rs` (stdin path for `run_structural`)
