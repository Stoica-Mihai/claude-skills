# ghyll — architectural hotspots & refactor shortlist

Quick orientation: 28 non-test `.go` files, ~9.7k LOC. Two files dominate the curve (1.7k and 1.65k LOC); the rest are healthy-sized. Hotspots cluster in two places — the CLI entrypoint and the TUI picker — with a secondary hotspot in the HLS base type and the Twitch plugin.

## Refactor shortlist (ranked)

### 1. `cmd/ghyll/main.go` — 1,744 LOC, god-package for the CLI
**Why it's a hotspot:** It is the integration seam for everything: imports `notify`, `output`, `plugin`, `session`, `stream`, `ui`, plus all three concrete plugin packages (`kick`, `twitch`, `youtube`) directly. Concrete plugin imports mean adding a plugin requires editing `main.go` — the plugin registry isn't actually pluggable from this seam.

Concrete smells:
- `buildRootCmd` is ~399 lines (lines 695-1093). It wires flags, viper config, signal handling, session setup, the picker, and playback all in one function.
- `runPlayback` is ~270 lines (1248-1517). It owns stream resolution, metadata fetch, quality selection, player spawn, notification dispatch, status callbacks, fallback logic, and ad-break wiring.
- Three local types live here that belong elsewhere: `formatOption`, `sessionConfig`, `playbackConfig`. Plus four `writeTheme*` helpers (TOML/YAML/JSON) that are config-file plumbing, not CLI code.
- Stream-ranking logic (`selectStream`, `streamWeight`, `sortedStreamNames`) is business logic stranded in `main`.

**Refactor moves:**
- Split `buildRootCmd` into per-subcommand builders (`buildPlayCmd`, `buildCheckCmd`, `buildConfigCmd`) in sibling files.
- Extract `runPlayback` into a new package `pkg/playback` with a `Runner` type — it has enough state (status callbacks, metadata cache, fallback policy) to deserve its own type.
- Move `selectStream`/`streamWeight`/`sortedStreamNames` into `pkg/stream` (probably `stream/selection.go`).
- Move theme-write helpers into `pkg/ui/theme.go` or a new `pkg/ui/themeio.go`.
- Replace direct `kick`/`twitch`/`youtube` imports with a registry pattern (slice of plugin constructors that each subpackage registers via `init()` or that `main.go` builds from a single list).

### 2. `pkg/ui/picker.go` — 1,651 LOC, god-component TUI model
**Why it's a hotspot:** A single `model` struct carries **41 fields** that span at least 6 distinct concerns:
- Table/list state (`entries`, `filteredIdx`, `cursor`, `offset`, `width`, `height`, `titleScroll*`)
- Refresh loop (`refresh`, `interval`, `countdown`, `refreshing`)
- Playback sessions (`launch`, `sessions`, `playbackGen`, `launchTimeout`)
- Quality overlay (8 `quality*` fields)
- Streams overlay (7 `streams*` fields)
- Theme overlay (`showTheme`, `themeCursor`, `savedStyles`, `savedThemeName`, `currentTheme`, `themeWriteFn`)
- Filter mode (`filterText`, `filterActive`)
- Help overlay (`showHelp`)

The `Update` method is **497 lines** (517-1013) — one switch that dispatches every key event across every overlay state. The four `show*` booleans (`showHelp`, `showQuality`, `showStreams`, `showTheme`) form an implicit mode enum that should be one `mode` field.

**Refactor moves:**
- Extract each overlay into its own sub-model (`qualityOverlay`, `streamsOverlay`, `themeOverlay`, `helpOverlay`) that satisfies a small `overlay` interface (`Init/Update/View`). The main `model` then holds one `current overlay` field instead of 22 overlay-related fields.
- Collapse `show*` booleans into a `viewMode` enum.
- Move `playbackSession`/`playbackState` tracking into a dedicated `playbackTracker` struct.
- Split file: `picker.go` (model + Update), `picker_render.go` (View + render helpers — `renderEntry`, `compositeOverlay`, etc.), `picker_layout.go` (`computeLayout`, `padRight`, `truncate`, `entryLineCount`).

### 3. `pkg/stream/hls/hls.go` — 672 LOC, leaky inheritance via public hooks
**Why it's a hotspot:** `HLSStream` exposes four exported callback fields meant for subclass-style override: `ProcessSegments`, `ShouldFilter`, `OnOpen`, `OnPlaylistParsed`. This is Go-flavored protected inheritance and creates tight coupling — the Twitch plugin reaches into these directly (see `plugins/twitch/twitch.go` `newHLSStream` and `buildStreams`). Any change to the segment lifecycle ripples into Twitch.

`HLSStream` also mixes: HTTP fetching, retry/backoff (`parseRetryAfter`, `retryDelay`), AES-128 decryption (`decryptAES128CBC`, `getKey`, `keyCache`), playlist reloading, segment scheduling (worker/writer goroutines), and an `io.PipeWriter` pipeline. That's at least three responsibilities.

**Refactor moves:**
- Replace the four override fields with a single `SegmentHandler` interface (one type, explicit methods). Twitch implements it.
- Extract `keyCache` + `getKey` + `decryptAES128CBC` into `pkg/stream/hls/crypto.go`.
- Extract retry helpers (`parseRetryAfter`, `retryDelay`) into `pkg/stream/hls/retry.go` (note: `retry_test.go` already exists, so the test file is ahead of the source split).

### 4. `plugins/twitch/twitch.go` (513 LOC) — does too many jobs
The plugin file mixes: URL matching, stream listing, metadata, HLS construction, transport mutation (`twitchTransport.RoundTrip` injects headers), restriction parsing, error parsing, and an `annotatedStream` wrapper. Split:
- `twitch_plugin.go` — plugin contract (`Matchers`/`Streams`/`Metadata`/`Arguments`)
- `twitch_playlist.go` — `fetchMasterPlaylist`/`buildStreams`/`validatePlaylistURL`/`variantName`
- `twitch_transport.go` — `twitchTransport` and header logic
- `twitch_stream.go` — `annotatedStream` + ad-break callback plumbing

### 5. `plugins/youtube/api.go` — 600 LOC, multi-client API soup
Two parallel InnerTube clients (VR + Android), four `extract*` walkers over untyped `any` trees, cookie injection, and channel-handle resolution all in one file. Split the extractors into `youtube/extractors.go` and isolate the two client paths.

## Cross-cutting coupling notes

- **`main.go` → every plugin (concrete imports):** breaks the "plugin" abstraction. The whole point of `pkg/plugin` is to keep `main` agnostic; right now it isn't.
- **`twitch` → `pkg/stream/hls` public callback fields:** the only real consumer of those hooks. Replace with an interface and the coupling becomes explicit/typed.
- **Picker model ↔ session/playback:** the picker owns `playbackSession` lifetime via raw channels and a generation counter. Extracting a `playbackTracker` (see hotspot 2) decouples UI from session bookkeeping.

## Files I'd touch first

If you only have time for two, do (1) and (2) — they're 35% of the codebase by line count, and both have giant functions that block readability. (3) is the highest-leverage architectural win because it removes inheritance-style coupling between core and plugins.

## Notes
- Excluded `_test.go` files from LOC ranking; some test files (`retry_test.go`) already imply a planned split that hasn't happened in source.
- Did not run static-analysis tools; ranking is based on file size, function size, struct-field count, import fan-out, and exported-hook coupling read directly from the source.
