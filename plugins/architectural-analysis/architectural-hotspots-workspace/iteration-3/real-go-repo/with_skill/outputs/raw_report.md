# Architectural Hotspots — `/home/mcs/Documents/git/ghyll`

Analyzed **59** source files, **53** internal import edges. Edges count file-to-file imports inside the repo only; external/unresolved imports are dropped.

## Hubs — high fan-in
Many files depend on these. Hubs are often legitimate (core libraries, shared types). They become interesting when paired with god-size, grab-bag naming (`utils`, `helpers`, `common`), or high churn in git history.

| File | Fan-in | LOC |
|------|-------:|----:|
| `pkg/stream/stream.go` | 13 | 43 |
| `pkg/stream/hls/hls.go` | 9 | 584 |
| `pkg/plugin/plugin.go` | 9 | 75 |
| `pkg/session/session.go` | 4 | 181 |
| `plugins/twitch/twitch.go` | 3 | 452 |
| `plugins/youtube/youtube.go` | 3 | 271 |
| `plugins/kick/kick.go` | 3 | 216 |
| `plugins/twitch/errors.go` | 3 | 24 |
| `pkg/ui/picker.go` | 2 | 1520 |
| `pkg/notify/notify.go` | 2 | 115 |
| `pkg/output/player.go` | 1 | 129 |
| `pkg/plugin/errors.go` | 1 | 7 |

## Tangles — high fan-out
These files reach into many corners of the repo. Often a sign of weak single-responsibility — the file is doing too many things, or is a coordination layer that should be split.

| File | Fan-out | LOC |
|------|--------:|----:|
| `cmd/ghyll/main.go` | 9 | 1581 |
| `cmd/ghyll/check_test.go` | 4 | 837 |
| `plugins/twitch/twitch.go` | 4 | 452 |
| `plugins/kick/kick.go` | 4 | 216 |
| `cmd/ghyll/check.go` | 4 | 214 |
| `plugins/youtube/youtube_test.go` | 3 | 650 |
| `plugins/youtube/youtube.go` | 3 | 271 |
| `cmd/ghyll/integration_test.go` | 3 | 250 |
| `cmd/ghyll/main_test.go` | 2 | 1458 |
| `plugins/kick/kick_test.go` | 2 | 748 |
| `plugins/twitch/api.go` | 2 | 390 |
| `pkg/session/session.go` | 2 | 181 |
| `pkg/plugin/plugin_test.go` | 2 | 107 |
| `plugins/twitch/api_test.go` | 1 | 799 |
| `pkg/stream/hls/hls.go` | 1 | 584 |

## God modules — LOC ≥ 400
Large files concentrate too much responsibility in one place. Cross-reference with the Hubs table — a file that is both god-sized *and* a hub is a refactor priority.

| File | LOC | Fan-in | Fan-out |
|------|----:|-------:|--------:|
| `pkg/ui/picker_test.go` | 3021 | 0 | 0 |
| `cmd/ghyll/main.go` | 1581 | 0 | 9 |
| `pkg/ui/picker.go` | 1520 | 2 | 0 |
| `cmd/ghyll/main_test.go` | 1458 | 0 | 2 |
| `pkg/stream/hls/hls_test.go` | 1063 | 0 | 0 |
| `plugins/youtube/api_test.go` | 951 | 0 | 0 |
| `cmd/ghyll/check_test.go` | 837 | 0 | 4 |
| `plugins/twitch/api_test.go` | 799 | 0 | 1 |
| `plugins/kick/kick_test.go` | 748 | 0 | 2 |
| `plugins/youtube/youtube_test.go` | 650 | 0 | 3 |
| `pkg/stream/hls/hls.go` | 584 | 9 | 1 |
| `pkg/stream/hls/m3u8_test.go` | 554 | 0 | 0 |
| `plugins/youtube/api.go` | 547 | 0 | 0 |
| `pkg/stream/hls/m3u8.go` | 497 | 0 | 0 |
| `plugins/twitch/twitch.go` | 452 | 3 | 4 |

## Cycles — strongly-connected components
Files inside a cycle cannot be understood, tested, or deployed independently. Cycles of size 2 often mean a missing seam (extract a third module both depend on); larger cycles usually signal a layering violation.

_No cycles detected._

## Limitations
- Imports resolved by relative path (where possible) and basename match across the repo. Path aliases, dynamic imports, re-exports, and codegen are likely missed.
- LOC counts non-blank lines; comments are not stripped.
- External / third-party imports are not counted — only intra-repo coupling.
- Treats each file as a node. Class- or function-level coupling is invisible here.
