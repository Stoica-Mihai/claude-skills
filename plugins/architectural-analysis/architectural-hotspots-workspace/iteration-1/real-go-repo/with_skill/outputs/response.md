Ran the hotspot analyzer on `/home/mcs/Documents/git/ghyll` (59 source files, 37 internal edges). Here's the refactor shortlist — four files, in priority order.

## Refactor shortlist

1. **`pkg/ui/picker.go`** (LOC 1520 by the analyzer, 1651 on disk) — **god module, top priority.**
   By far the largest non-test file in the repo and it's a UI picker. A 1.5k-LOC view component is almost certainly multiple concerns fused: model, update/reducer, table layout, key handling, theme glue. The natural split for a Bubble Tea program is one file per state/screen plus a thin root model — look for the `Update`/`View` switch arms and peel them off first. The companion test (`pkg/ui/picker_test.go`, 3021 LOC) is a tell that you're already paying for the size.

2. **`cmd/ghyll/main.go`** (LOC 1581 / 1744 on disk) — **god module in the entrypoint.**
   `main.go` should be wiring, not logic. At 1.5k+ LOC this is doing command parsing, dispatch, and probably most of the check/run flows itself (`check_test.go` at 837 LOC backs that up). Move the subcommand bodies into `cmd/ghyll/check.go`, `cmd/ghyll/run.go`, etc., or into a `pkg/cli` package, and leave `main.go` as flag parsing + dispatch. This also unblocks unit-testing the subcommands without driving the full binary.

3. **`pkg/stream/http.go`** (LOC 164, fan-in 21) — **the real hub.**
   It is the single most depended-on file in the repo by a wide margin (21 importers vs. ~10 for the next one, which is a false positive — see caveat). At 164 LOC it's not god-sized, so it's a *healthy* hub today. Flagging it because that means it is your de-facto stream HTTP contract: any breaking change ripples to 21 files. Treat its public surface as load-bearing — narrow the exported API if you can, and resist adding unrelated helpers to it. No refactor needed now; just protect it.

4. **`pkg/stream/hls/hls.go`** (LOC 584) **and `plugins/youtube/api.go`** (LOC 547), **`plugins/twitch/api.go`** (LOC 390), **`plugins/twitch/twitch.go`** (LOC 452) — **plugin-shaped god modules.**
   Each plugin has one fat file doing parsing + API calls + dispatch. They aren't hubs (nobody imports across plugin boundaries, which is correct), so the blast radius is contained — but they're individually overloaded. The HLS file in particular pairs with a 1063-LOC test, which usually means several distinct behaviours are tangled in one file. Split each plugin into `api.go` (HTTP/GQL calls), `parse.go` (response → entry types), and `dispatch.go` (URL matching + plugin entry points).

## What I am *not* recommending

- The analyzer reports a cycle between `pkg/plugin/errors.go` and `plugins/twitch/errors.go`. **This is a false positive** — I opened both files and neither imports the other; they just share the basename `errors.go`, which the resolver's basename-match path tied together. Ignore.
- The high fan-out entries are all `_test.go` files importing one or two packages. That's normal for Go table-driven tests; not a coupling problem.
- `plugins/twitch/errors.go` showing fan-in 10 is the same basename-collision artefact as the cycle. The real twitch coupling is normal package-internal use.

## Caveat on the numbers

The resolver matches Go imports by basename across the repo, which works for most of this codebase but produces the `errors.go` false positives above and probably undercounts a few edges where multiple files share a stem. The fan-in on `pkg/stream/http.go` (21) is high enough that I trust the *signal* even if the exact count is +/- a couple. LOC counts are non-blank lines without comment stripping, so treat them as rough size rather than precise.

Full raw report: `plugins/architectural-analysis/architectural-hotspots-workspace/iteration-1/real-go-repo/with_skill/outputs/raw_report.md`.
