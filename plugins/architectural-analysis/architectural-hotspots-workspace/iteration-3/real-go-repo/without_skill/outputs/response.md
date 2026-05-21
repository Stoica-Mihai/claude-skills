# ghyll — architectural hotspots & refactor shortlist

Scope: 21 non-test Go files, ~6.7k LOC. Plugin dirs and tests excluded. Findings come from
file-size scan, top-level decl listing, function-span measurement, and import-graph trace.

## The two hotspots (everything else is secondary)

### 1. `cmd/ghyll/main.go` — 1744 LOC, the universal junction box
Path: `/home/mcs/Documents/git/ghyll/cmd/ghyll/main.go`

This single file imports nine of the project's own packages plus all three platform plugins
(`kick`, `twitch`, `youtube`), and is the only file in the whole repo that touches `notify`,
`output`, and `ui` simultaneously. That makes it the de facto orchestration layer — but it's
shaped as a script, not as a layer.

Concrete concentrations of responsibility inside one file:

- `buildRootCmd` is **396 lines**. It declares ~25 CLI flags grouped into five concern-clusters
  (config / general / HTTP / HLS / playback), wires Viper, builds the cobra command, and
  embeds `PersistentPreRunE` + `RunE` closures that do real work (config loading, channel-list
  refresh wiring, playback dispatch). Flag declaration, config binding, and runtime behavior
  are all glued together in one closure.
- `runPlayback` is **266 lines** and mixes: stream resolution, metadata fetch, stream
  selection, player launch, notification dispatch, recording fan-out, status callbacks,
  reconnect/fallback loop. Six concerns, one function.
- Three giant config-template string constants (`configTemplateTOML/YAML/JSON`, lines 158–267)
  live next to runtime logic. Plus three near-duplicate writers `writeThemeTOML/YAML/JSON`
  (lines 528–648) — format-dispatch copy-paste.
- An interactive **format picker** (`renderFormatPicker`, `promptConfigFormat`,
  `formatPickerLines`, lines 287–387) lives inside `cmd/ghyll`, while a full Bubble Tea
  picker already lives in `pkg/ui`. Two parallel TUI implementations in one binary.
- Package-level mutable globals: `configPrompted`, `configGeneratedPath`, and the
  `avatarPaths` struct (line 1116) act as cross-function state — classic sign that this file
  has outgrown a single conceptual unit.

Smell summary: god-file. `main.go` is currently doing the job of `cmd/ghyll/config`,
`cmd/ghyll/flags`, `cmd/ghyll/playback`, and an avatar/notify coordinator.

### 2. `pkg/ui/picker.go` — 1651 LOC, the god-model
Path: `/home/mcs/Documents/git/ghyll/pkg/ui/picker.go`

The Bubble Tea model has degenerated into one type doing five UIs:

- `model` struct (lines 251–298) has **~40 fields**. Roughly four mutually exclusive overlay
  state machines share one struct: help (`showHelp`), quality picker (`showQuality`,
  `qualityLoading`, `qualityEntries`, `qualityCursor`, `qualityErr`, `qualityChannel`,
  `qualityEntry`, `qualityFromStreams`), stream picker (`showStreams`, `streamsLoading`,
  `streamEntries`, `streamsCursor`, `streamsErr`, `streamsChannel`, `streamsFn`), theme
  picker (`showTheme`, `themeCursor`, `savedStyles`, `savedThemeName`, `currentTheme`,
  `themeWriteFn`). Each overlay duplicates the same shape (`show*` + `*Cursor` + `*Loading`
  + `*Err` + `*Entries`) — there is no `overlay` interface.
- `Update` (line 517) is **494 lines** — almost a third of the file. It dispatches every key
  for every overlay mode in one switch. The `qualityFromStreams` boolean (quality picker
  knows it was opened by the stream picker so Esc returns there) is exactly the kind of flag
  that proves the overlays should be a stack, not boolean siblings.
- `NewPicker` / `newModel` / `Picker.Run` take **9 functional arguments** each
  (`RefreshFunc`, `LaunchFunc`, `QualityFunc`, `StreamsFn`, `defaultQuality`, `theme`,
  `themeName`, `themeWriteFn`, `interval`). Constructor-as-DI-container signal.
- Layout/format helpers (`computeLayout`, `padRight`, `truncate`, `formatViewerCount`,
  `formatUptime`, `renderEntry`, `clampScroll`, `sortEntries`, `refilter`, `liveCount`)
  belong in a `pkg/ui/table` sub-package.

Smell summary: god-object + parallel-state-machines-in-one-struct.

## Tight coupling worth calling out

- **`cmd/ghyll/main.go` → `plugins/{kick,twitch,youtube}`.** The CLI binary statically imports
  every platform plugin (also in `cmd/ghyll/check.go`). `session.Plugins.Resolve` already
  exists, so plugins should be registered in one place (an `init()` in a `plugins/all`
  aggregator) and the CLI should depend only on `session`/`plugin`. Today, every new
  platform requires editing `main.go`.
- **`runPlayback` reaches across four packages mid-function** (`session`, `plugin`, `stream`,
  `output`, plus calls back into `ui.Status` via `cfg.onStatusChange`). There is no
  `playback` package — the playback pipeline is implemented as a function literal in
  `cmd/ghyll`. That's why this function is 266 lines: it's a missing module.
- **`pkg/ui/picker.go` holds business callbacks** (`LaunchFunc` runs playback, `QualityFunc`
  fetches qualities, `StreamsFn` fetches metadata, `themeWriteFn` writes config to disk).
  The picker is supposed to be a view; it currently owns wiring that belongs in
  `cmd/ghyll`. The `themeWriteFn` callback in particular makes a UI package transitively
  responsible for config-file format dispatch.
- **`pkg/stream/hls/hls.go` (672 LOC)** is a single struct (`HLSStream`) with 14 methods
  covering: playlist fetch, reload-sleep policy, key cache, AES-128 decrypt, segment
  fetch/discard/write, map handling, worker/writer goroutines. Less alarming than the two
  giants above (it's one cohesive subsystem), but `decryptAES128CBC` and the `keyCache`
  type are clearly separable, and `worker` + `writer` + `fetchAndWriteSegment` together are
  most of the file's complexity.

## Refactor shortlist (ranked, do top-down)

1. **Split `cmd/ghyll/main.go`.** Pull out four files in `cmd/ghyll/`:
   `config.go` (templates + `loadViperConfig` + `ensureConfig` + `promptConfigFormat` +
   `writeTheme*` — collapse the three format writers behind a `configFormat` interface),
   `flags.go` (`buildRootCmd` flag block), `playback.go` (`runPlayback`, `selectStream`,
   `streamWeight`, `sortedStreamNames`, `splitPlayerArgs`), and keep `main.go` as a thin
   `run()` + cobra wire-up. Target: no file over ~400 LOC.

2. **Extract a `pkg/playback` package.** `runPlayback` is a missing module. It should own
   stream resolution, selection, player launch, notify/record fan-out, and reconnect loop —
   exposing one `Run(ctx, sess, Request) error`. Removes `cmd/ghyll` ↔ `stream`/`output`/
   `notify` coupling.

3. **Decompose `pkg/ui/picker.go` into an overlay stack.** Introduce an `overlay` interface
   (`Update`, `View`, `Key`) and concrete `helpOverlay`, `qualityOverlay`, `streamsOverlay`,
   `themeOverlay`. Replace `showHelp/showQuality/showStreams/showTheme` + the
   `qualityFromStreams` re-entry flag with a `[]overlay` stack on `model`. Move table/render
   helpers into `pkg/ui/table`. Target: `model` ≤ 10 fields, `Update` ≤ 100 LOC.

4. **Plugin registration aggregator.** Add `plugins/all` (or `plugins/register`) with an
   `init()` that registers Kick/Twitch/YouTube into a default registry. Remove direct
   plugin imports from `cmd/ghyll/main.go` and `check.go`.

5. **(Lower priority) Split `pkg/stream/hls/hls.go`.** Move `keyCache` + `getKey` +
   `decryptAES128CBC` into `crypto.go`; move `worker`/`sleepReload`/`fetchPlaylist` into
   `playlist_loop.go`; keep `HLSStream` + `Open` in `hls.go`. Cohesion is already OK, this
   is just file-size hygiene.

## Not hotspots (verified, don't churn them)

`pkg/session/*`, `pkg/plugin/*`, `pkg/stream/{stream,filtered,http,muxed}.go`,
`pkg/output/player.go`, `pkg/notify/notify.go`, `pkg/ui/theme.go`, `pkg/ui/status.go` —
all ≤ ~280 LOC with clean single-purpose responsibilities and minimal cross-imports
(`session` is the only one importing other internal pkgs, which is correct). Leave alone.
