# ghyll — architectural hotspots, refactor shortlist

Ran the hotspot analyzer over the 59 Go files (53 internal edges, no
cycles). Skipping the test-file noise in the god-modules table, four
files stand out as actually worth your time, plus one resolver caveat
that changes how the report should be read.

## Refactor shortlist

1. **`cmd/ghyll/main.go`** — **1581 LOC, fan-out 9, 25 top-level funcs.**
   The clearest god module in the repo. It's the CLI entry point but it
   has also absorbed: viper config loading, a first-run config-format
   picker (`renderFormatPicker`, `promptConfigFormat`,
   `generateConfigFile`), per-format theme writers (`writeThemeTOML`,
   `writeThemeYAML`, `writeThemeJSON`), avatar downloading, the entire
   playback pipeline (`runPlayback`, `setupSession`), and stream-quality
   selection logic (`selectStream`, `streamWeight`, `sortedStreamNames`).
   Most of these have no business in `main` — they're libraries.
   *Suggestion:* extract three packages — `internal/cli/config` (loader
   + format prompt + theme writers), `internal/cli/playback` (session
   setup + run + avatar fetch), `internal/cli/quality` (selectStream +
   streamWeight). Leaves `main.go` as wiring only.

2. **`pkg/ui/picker.go`** — **1520 LOC, 36 funcs, all hung off one
   `model` struct.** Single-file Bubble Tea TUI that owns the main
   table, plus four overlays (help, quality, streams, theme), plus
   layout, plus scroll, plus title-scroll animation, plus an `Update`
   method that starts at line 517 (so roughly 500 lines of one
   function). Not a hub problem — fan-in is only 2 — but a
   single-responsibility one. Every overlay added to the picker
   widens this file further.
   *Suggestion:* split overlays into their own files
   (`picker_quality.go`, `picker_streams.go`, `picker_theme.go`,
   `picker_help.go`), each owning its render + key-handling slice. The
   shared `model` stays in `picker.go`; the giant `Update` switch
   becomes a dispatcher.

3. **`plugins/youtube/api.go`** — **547 LOC, fan-in 3, 18 funcs.**
   Wraps three InnerTube endpoints (player / browse / resolve_url) with
   three rotating client configs (ANDROID_VR / ANDROID / WEB), all in
   one file. Touches HTTP, JSON, multiple bot-detection workarounds.
   It's a real coordination layer — but it's also the kind of file that
   silently grows whenever YouTube changes anything.
   *Suggestion:* lower-priority than 1–2, but worth keeping an eye on.
   If a fourth client config gets added, split per-client into
   `client_androidvr.go` / `client_android.go` / `client_web.go`.

4. **`pkg/stream/hls/hls.go`** — **584 LOC, hub for every plugin that
   does HLS (twitch, youtube, kick).** Genuinely load-bearing, not a
   grab-bag — so the *size* matters more than the fan-in. Every
   streaming plugin depends on its behaviour; a bug here ripples
   everywhere. Treat it as well-placed but worth keeping under change
   discipline (good test coverage, careful PRs, no opportunistic
   features). The 1063-LOC `hls_test.go` shows you already feel this.

## What is *not* a problem despite scoring high

- **`pkg/stream/filtered.go`** (fan-in 13, 59 LOC) and
  **`pkg/plugin/args.go`** (fan-in 9, 8 LOC) — both legitimate hubs:
  one is a focused stream wrapper, the other is a 9-line type
  definition. High fan-in here is exactly what shared primitives
  should look like. Leave alone.
- **`plugins/twitch/hls.go`** (reported fan-in 8) — this is the
  resolver caveat below biting; nothing actually imports it as a
  package. The hits belong to `pkg/stream/hls/hls.go`.

## Caveat on the numbers

The analyzer resolves Go imports by basename match across the repo
with a directory-proximity tie-breaker. ghyll has two files named
`hls.go` (`pkg/stream/hls/hls.go` and `plugins/twitch/hls.go`), so
imports of `pkg/stream/hls` from within `plugins/twitch/` got
attributed to the local `plugins/twitch/hls.go` instead of the real
target. The shape of the report (which files are large, which are
glue) is still correct; just don't trust the fan-in number on
`plugins/twitch/hls.go` specifically.

Raw report (full tables) at:
`/home/mcs/Documents/git/claude-skills/plugins/architectural-analysis/architectural-hotspots-workspace/iteration-2/real-go-repo/with_skill/outputs/raw_report.md`
