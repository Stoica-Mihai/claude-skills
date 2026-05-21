**Perf (4)**
- `structural.rs:182` — `m.captures.iter().map(...).max()` linear scan per match when `@root` is absent. Fix: precompute max capture index once in `compile`.
- `structural.rs:184` — `captures.iter().find(|c| c.index == primary_idx)` re-scans captures per match after the `max()` walk just did it. Fix: track the primary capture in the same pass that selects the index.
- `structural.rs:225` — `captures.iter().find(...)` per template part per match → O(parts × captures) per hit. Fix: build a small `[Option<usize>; N]` capture-index → captures-slot lookup once per match, or precompute a per-template `Vec<usize>` of `captures` positions.
- `structural.rs:356-362` — `par_iter().map_init().collect()` materializes the full `Vec<Result<Option<FileChange>>>` before filtering. Fix: filter-map inside the rayon pipeline so empty results don't allocate `Result` slots.

**Correctness (5)**
- `structural.rs:552` — `field_name_for_child(child.id() as u32)`: `Node::id()` returns a pointer-derived `usize`, not a child index; the API wants the positional child index. Friendly-query field labels are essentially never correct. Fix: enumerate `named_children` and call `field_name_for_named_child(idx as u32)`.
- `structural.rs:181-183` — primary-capture heuristic picks the *highest capture index*, but capture indices reflect query definition order, not AST nesting; doc comment promises "outermost match node." Fix: drop the heuristic and require `@root`, or select primary by smallest `start_byte` / largest span.
- `structural.rs:188-194` — `Hit { start, end }` taken from the primary capture's node bytes ignores the match's outermost span when `@root` is absent; sibling captures outside the chosen "primary" are silently dropped from the replaced range. Fix: derive replacement range from the union of all capture nodes when no `@root` is set.
- `structural.rs:174` + `structural.rs:395` — `Error::StructuralParse` is path-less; `plan_one` doesn't wrap it, so per-file parse failures surface with no filename. Fix: have `plan_one` map the error to one that carries `path`.
- `structural.rs:281, 507` — `literal.push(b as char)` in `parse_template` and `substitute_metavars` casts raw bytes to `char`, corrupting any non-ASCII multibyte sequence in pattern/template. Fix: walk `template.chars()` (or `char_indices`) instead of bytes, or copy verified UTF-8 slices.
- `structural.rs:595` — `escape_query_string` escapes only `"`, `\`, `\n`; literal leaves containing `\r`, `\t`, or non-printable chars yield malformed tree-sitter query strings. Fix: escape `\r`, `\t`, and emit `\xNN` (or reject) for other controls.

**Complexity (3)**
- `structural.rs:513-561` — `emit_node` recurses on the user-supplied `--ast` pattern AST with no depth bound; pathological deeply-nested pattern → stack overflow. Source-file parsing is iterative inside tree-sitter's C runtime, so the real risk surface is *pattern depth*, not source depth. Fix: convert to an explicit stack like `subtree_ellipsis_capture`, or bound depth and return `StructuralQuery` past a cap.
- `structural.rs:440-480` — `compile_friendly_query` mixes substitution, parse, `source_file` unwrap, recursive emit, and prefix-formatting in one function. Fix: split into `substitute_metavars` (exists) + `parse_pattern_to_ast` + `ast_to_query_string` returning `(String, Vec<String>)`.
- `structural.rs:168-216` — `CompiledStructural::apply` does match collection, primary-capture selection, error rendering, sort, capacity math, and splice in one body. Fix: extract `collect_hits` and `splice_hits` as private helpers.

**Coupling (3)**
- `structural.rs:341-382 + plan.rs:112-224` — `plan_structural_rewrite` reimplements `scan` (walk + max-files), `collect_changes`, and the zero-match → `AlreadyApplied` finalization that already live in plan.rs. Fix: expose `pub(crate) fn scan`, `collect_changes`, and `finalize_plan` (or a `PlanFinalize` struct) and have the structural pipeline call them.
- `structural.rs:384-408 + plan.rs:248-286` — `plan_one` (structural) and `process_one` (regex) duplicate the read → rewrite → diff → `FileChange` construction shape; only the rewrite callback and the convergence check differ. Fix: lift one shared `build_file_change<R>(path, opts, rewrite)` helper that both modes call; structural passes a no-op convergence closure.
- `structural.rs:399-407 + plan.rs:277-285` — identical `label_for_path` + `unified_diff` + `FileChange { ... permissions: Some(...) }` construction inlined in two places; drift risk if `FileChange` gains a field. Fix: add `FileChange::from_rewrite(path, before, after, matches, permissions)` and have both pipelines call it.

**Top targets**
1. `structural.rs:552` — `field_name_for_child(child.id() as u32)` identifier/index conflation silently mislabels every field in friendly queries. Fix: enumerate named children and use `field_name_for_named_child`.
2. `structural.rs:181-194` — `max()`-by-capture-index "primary" heuristic + range-from-primary-only diverges from the doc-promised "outermost match node" and can drop captures from the replaced span. Fix: require `@root` or derive range from the union of capture spans.
3. `structural.rs:281,507` — `b as char` byte-to-char casts in `parse_template` and `substitute_metavars` corrupt non-ASCII patterns/templates. Fix: iterate by `char_indices`.
4. `structural.rs:341-382` vs `plan.rs:183-224` — duplicated walk/finalize/file-change pipeline; structural drifts from regex if either side changes. Fix: lift `scan`, `collect_changes`, `finalize_plan`, and `FileChange` construction into plan.rs helpers and call them from both modes.
5. `structural.rs:225` (+ `:182,:184`) — repeated `captures.iter().find(...)` per match and per template part. Fix: build a single capture-index lookup table per match, reuse across primary-pick and template render.
