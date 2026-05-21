# ghyll architectural hotspots — refactor shortlist

Two files are doing far too much, and a third has a coupling problem hiding under a "subclass hook" pattern. That's basically the whole story.

## 1. `cmd/ghyll/main.go` — the god file (1744 LOC)

This single file is not really `main`. It contains, in order:

- `main`, `run`, `buildRootCmd` (the Cobra wiring)
- Viper config loading, key mapping, debug logging of applied keys (`loadViperConfig`, `viperConfigKeys`)
- First-run config-file generation including **three** full TOML/YAML/JSON template constants (`configTemplateTOML/YAML/JSON`, `ensureConfig`, `promptConfigFormat`, `generateConfigFile`)
- An inline interactive picker for the config format with its own ANSI rendering (`renderFormatPicker`, `formatOptions`, `formatPickerLines`) — a mini-TUI built into the entrypoint
- Theme persistence with **three** parallel writers (`writeThemeTOML`, `writeThemeYAML`, `writeThemeJSON`) — duplicated format dispatch logic
- Channel input parsing (`readChannelInputs`)
- Avatar download + caching (`avatarPaths`, `downloadAvatar`)
- Session/plugin assembly (`setupSession`)
- Playback orchestration (`runPlayback` runs ~270 lines and owns ad-break wiring, notification gating with `sync.Once` + `atomic.Bool`, player construction, reconnect pipe, drop callbacks, stable-threshold reconnect counter)
- Stream selection (`selectStream`, `streamWeight`, `sortedStreamNames`)
- Misc parsers (`parseRefreshInterval`, `parseLogLevel`, `parseKeyValuePairs`, `splitPlayerArgs`, `generateOutputPath`)

It imports every internal package (`notify`, `output`, `plugin`, `session`, `stream`, `ui`, and all three platform plugins `kick`/`twitch`/`youtube`) — so it's also the single point where everything fans in.

**Refactor moves:**
- `cmd/ghyll/config_init.go` — move `ensureConfig`, all three template constants, `promptConfigFormat`, `generateConfigFile`, `renderFormatPicker` (and `formatOption[s]`, `formatPickerLines`). Better: collapse the per-format writers behind one `configWriter` interface keyed by extension; the TOML/YAML/JSON branches in `writeThemeToConfig` are crying out for it.
- `cmd/ghyll/config_load.go` — `loadViperConfig`, `viperConfigKeys`, `parseRefreshInterval`, `parseLogLevel`, `parseKeyValuePairs`.
- `pkg/playback/` (new package) — `runPlayback` + `selectStream` + `streamWeight` + `sortedStreamNames` + the `playbackConfig` struct. This is genuine domain logic, not CLI glue, and it's the function I'd most expect to grow further.
- `pkg/avatar/` (new package) — `downloadAvatar` and the `avatarPaths` singleton (which is currently a process-global `struct{ sync.Mutex; ... }` — also a refactor smell).
- Leave only Cobra flag wiring and `main`/`run` in `main.go`. That alone drops it to maybe 400 LOC.

## 2. `pkg/ui/picker.go` — Bubble Tea kitchen sink (1651 LOC)

One `model` struct with ~40 fields managing **five** concurrent overlay state machines: help, quality, streams, theme, and filter. `model.Update` is ~840 lines containing 65 `case` branches.

The structural smell:
- Each overlay has its own group of fields prefixed `show*`, `*Loading`, `*Entries`, `*Cursor`, `*Err`, sometimes `*Channel`, `saved*`, etc. The fact that the prefixes are mechanically parallel proves the abstraction is missing.
- `Update` opens with global keys, then a cascade of `if m.showHelp / showTheme / showStreams / showQuality / filterActive { ... return }` blocks. That's a manually-implemented mode stack.
- The file also owns: layout math (`computeLayout`, `tableLayout`, `padRight`, `truncate`), all rendering (`render*Overlay`, `renderMainTable`, `renderEntry`, `View`, `compositeOverlay`), formatting helpers (`formatViewerCount`, `formatUptime`), filter/sort logic (`sortEntries`, `refilter`, `filteredEntries`, `preserveCursor`, `clampScroll`, `liveCount`), the playback-session map, and the public `Picker` / `Run` entrypoint.

**Refactor moves:**
- Extract an `overlay` interface (`Update(tea.Msg) (overlay, tea.Cmd)`, `View() string`, `Active() bool`) and one file per overlay: `overlay_help.go`, `overlay_quality.go`, `overlay_streams.go`, `overlay_theme.go`. The main `model` just routes to the topmost active overlay. That single move probably halves `Update`.
- Split rendering out to `picker_render.go` (everything from `renderHelpOverlay` through `View`, `renderEntry`, `compositeOverlay`, plus `computeLayout`/`padRight`/`truncate`).
- Split formatting helpers (`formatViewerCount`, `formatUptime`) into `pkg/ui/format.go`. `PrintChannelList` looks like it belongs there too — it's a non-TUI utility currently living inside the TUI file.
- Filter/sort/cursor helpers (`refilter`, `preserveCursor`, `clampScroll`, `sortEntries`, `filteredEntries`) into `picker_filter.go`.

After this, `picker.go` should be just the `Picker` type, `Run`, `newModel`, `Init`, and the top-level `Update` dispatch.

## 3. `pkg/stream/hls/hls.go` — open extension via mutable struct fields (672 LOC)

The smell isn't size, it's the coupling pattern. `HLSStream` exposes **callback fields as part of its public struct** to let other plugins customise behaviour:

```go
// Hooks for subclass override (e.g. Twitch)
ProcessSegments  func(segments []Segment, isFirst bool) []Segment
ShouldFilter     func(seg Segment) bool
OnOpen           func()
OnPlaylistParsed func(playlist *MediaPlaylist)
```

The comment explicitly names `twitch` — and indeed `plugins/twitch/twitch.go` and `plugins/twitch/hls.go` reach into these fields. That's compile-time coupling masquerading as a hook system: any change to ad-filtering semantics ripples back into `HLSStream`'s public surface. `Filtered` is also exposed for "subclass use (e.g. ad filtering pause/resume)", and the comment admits it.

Also in the same file: a `keyCache` (AES key cache), the AES-128-CBC decrypt routine, `retryDelay` with `parseRetryAfter`, the 200-line `worker` goroutine, `fetchPlaylist` with retries, `fetchAndWriteMap` / `fetchAndWriteSegment` / `fetchAndDiscard`, and an `hlsReadCloser` wrapper. That's three or four jobs.

**Refactor moves:**
- Define a small `SegmentProcessor` interface (e.g. `Process([]Segment, first bool) []Segment`, `Filter(Segment) bool`, `OnPlaylistParsed(*MediaPlaylist)`) and let `TwitchPlugin` pass an implementation in via constructor. Drop the exposed function fields. This breaks the "subclass" anti-pattern and lets `HLSStream` go back to being a value type.
- Move retry helpers (`parseRetryAfter`, `retryDelay`) to `pkg/stream/hls/retry.go` (there's already a `retry_test.go`, so the helpers belong in their own file).
- Move `keyCache` + `getKey` + `decryptAES128CBC` to `pkg/stream/hls/crypto.go`. Crypto + key caching is an isolated concern, currently inlined inside the segment fetcher.
- That leaves `hls.go` with `HLSStream`, `Open`, `worker`, and the fetch/write methods — still big but cohesive.

## Smaller things worth flagging while you're in there

- **`plugins/twitch/twitch.go` (513 LOC)** — `TwitchPlugin` mixes plugin-protocol methods (`Matchers`, `Streams`, `Metadata`, `Arguments`), the actual API logic (`liveStreams`, `acquireAccessToken`, `fetchMasterPlaylist`, `buildStreams`), an HLS factory (`newHLSStream`, `validatePlaylistURL`), and a custom `twitchTransport` `http.RoundTripper`. The transport and the `annotatedStream` wrapper at the bottom are both natural extractions to `transport.go` / `stream.go`.
- **`plugins/youtube/api.go` (600 LOC)** — three InnerTube client variants (web/VR/android) inlined as code-generated context maps and per-client retry logic in `Player`/`playerRaw`/`playerWithClient`. The "try each client until one doesn't reject" pattern in `Player` would read better as a slice of client configs iterated in a loop, killing the duplicate `looksLikeRejection` plumbing.
- **`pkg/stream/hls/m3u8.go` (538 LOC)** — parser is one file but has two top-level entrypoints (`ParseMaster`, `ParseMedia`) plus a pile of `attrString`/`attrQuoted`/`attrInt`/`attrFloat`/`findAttr`/`parseXAttributes` helpers. Probably fine to leave, but if you ever touch it, `attrs.go` is the obvious split.

## Coupling map (most important takeaway)

`pkg/stream` is the trunk — 13 importers, everything depends on its interfaces (`Stream`, `Droppable`, `AdBreakNotifier`, `AdEndNotifier`, `PreRollNotifier`, `StreamInfoProvider`). That's healthy and expected.

The unhealthy concentration is at the leaves:
- `cmd/ghyll/main.go` is the only file importing **all eight** internal packages, and it does substantive work in each of those domains rather than just wiring.
- `plugins/twitch/twitch.go` is the only file outside `pkg/stream/hls` that knows about `HLSStream`'s "hook" fields — making it the de-facto subclass and giving you a coupling you can't see from the package graph.

## TL;DR shortlist (in priority order)

1. **Split `cmd/ghyll/main.go`** into config-init, config-load, playback, and avatar — kill the god file. Highest payoff because every future feature lands here.
2. **Decompose the picker `model`** into per-overlay state objects behind an `overlay` interface. This is the riskiest file to touch next given the 40-field struct + 840-line `Update`.
3. **Replace `HLSStream`'s exposed function-field hooks** with a `SegmentProcessor` interface; extract `crypto.go` and `retry.go` alongside.
4. (Lower) clean up Twitch transport + annotated-stream and the YouTube InnerTube client cascade.
