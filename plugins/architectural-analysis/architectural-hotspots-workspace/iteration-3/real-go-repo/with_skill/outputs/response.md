# Architectural hotspots in `ghyll` — refactor shortlist

Ran the hotspot analyzer over the repo (59 Go source files, 53 internal edges, no import cycles). Four files stand out — the rest of the report is mostly noise from large test files that nothing imports.

## The shortlist

1. **`cmd/ghyll/main.go` — 1581 LOC, fan-out 9, 25 top-level funcs.**
   This is the worst offender by a wide margin. It's both god-sized *and* the highest-fan-out file in the repo: the CLI entrypoint is reaching directly into `pkg/stream`, `pkg/stream/hls`, `pkg/plugin`, `pkg/session`, `pkg/ui`, `pkg/notify`, `pkg/output`, and all three plugin packages. Nothing imports it (it's `package main`), so the blast radius is contained — but the file itself is doing config loading, plugin dispatch, stream selection, session handling, output wiring, and signal handling all in one place.
   Suggested split: extract a `cmd/ghyll/app` (or `internal/cli`) package with one file per concern — `config.go`, `dispatch.go`, `run.go`, `output.go` — and leave `main.go` as a ~50-line wiring shim. The companion `main_test.go` (1458 LOC) and `check_test.go` (837 LOC) will get easier to split along the same seams.

2. **`pkg/ui/picker.go` — 1520 LOC, fan-in 2, 36 top-level funcs.**
   Second-largest file in the codebase, with a 3021-LOC test file sitting beside it. Low fan-in/out means it's well-encapsulated at the package boundary, so this is a *single-responsibility* problem inside the package rather than a coupling problem. 36 funcs in one file is the smell — likely view + state + key handling + rendering all interleaved. Split internally by concern (model, update, view, keymap) within the same package; no import changes needed downstream.

3. **`pkg/stream/hls/hls.go` — 584 LOC, fan-in 9, fan-out 1.**
   The only file in the repo that hits *both* the god-modules and the hubs tables. Nine files depend on it, so any change ripples — and at 584 LOC with 19 funcs it's collecting too much. Worth pulling stable types/interfaces into a thin `hls/types.go` (so dependents import that, not the implementation) and moving the heavier playlist/segment logic into siblings of `m3u8.go`. This reduces the blast radius for the next change.

4. **`plugins/twitch/twitch.go` — 452 LOC, fan-in 3, fan-out 4.**
   Smaller, but it's the only plugin file appearing in *three* tables (hub, tangle, god). Compare with `youtube.go` (271 LOC) and `kick.go` (216 LOC) — Twitch has roughly twice the surface area, suggesting plugin-specific logic that hasn't been generalized back into `pkg/plugin`. If the other two plugins were factored from this one, the shared pieces probably want to move up; if they were written independently, this one is overdue for a similar trim.

## What's *not* a problem

- **`pkg/stream/stream.go`** is the top hub (fan-in 13) but it's a 43-LOC interface file. That's exactly what a healthy hub looks like — leave it alone.
- **`pkg/plugin/plugin.go`** (fan-in 9, 75 LOC) — same story, healthy seam.
- **No import cycles.** The package layering is clean; this is a size/responsibility problem, not a structural-tangle problem.
- The big test files (`picker_test.go` 3021, `main_test.go` 1458, `hls_test.go` 1063, etc.) inflate the god-modules table but have zero fan-in/fan-out. They'll naturally shrink once the production files are split.

## Caveats

The analyzer resolves Go imports by basename matching, so anything imported via `go.mod` replace-directives or build tags could be undercounted. It's also file-level — a god-struct hiding inside a 300-LOC file is invisible. Treat the shortlist as candidates; the LOC + fan-out combination on `main.go` and `hls.go` is the strongest signal here.

Raw report: `/home/mcs/Documents/git/claude-skills/plugins/architectural-analysis/architectural-hotspots-workspace/iteration-3/real-go-repo/with_skill/outputs/raw_report.md`
