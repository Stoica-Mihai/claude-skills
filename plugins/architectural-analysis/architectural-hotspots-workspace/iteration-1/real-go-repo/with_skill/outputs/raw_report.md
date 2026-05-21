# Architectural Hotspots — `/home/mcs/Documents/git/ghyll`

Analyzed **59** source files, **37** internal import edges. Edges count file-to-file imports inside the repo only; external/unresolved imports are dropped.

## Hubs — high fan-in
Many files depend on these. Hubs are often legitimate (core libraries, shared types). They become interesting when paired with god-size, grab-bag naming (`utils`, `helpers`, `common`), or high churn in git history.

| File | Fan-in | LOC |
|------|-------:|----:|
| `pkg/stream/http.go` | 21 | 164 |
| `plugins/twitch/errors.go` | 10 | 24 |
| `pkg/plugin/errors.go` | 6 | 7 |

## Tangles — high fan-out
These files reach into many corners of the repo. Often a sign of weak single-responsibility — the file is doing too many things, or is a coordination layer that should be split.

| File | Fan-out | LOC |
|------|--------:|----:|
| `plugins/youtube/api_test.go` | 2 | 951 |
| `cmd/ghyll/check_test.go` | 2 | 837 |
| `plugins/twitch/api_test.go` | 2 | 799 |
| `plugins/kick/kick_test.go` | 2 | 748 |
| `plugins/twitch/api.go` | 2 | 390 |
| `plugins/youtube/youtube.go` | 2 | 271 |
| `plugins/kick/kick.go` | 2 | 216 |
| `plugins/twitch/dispatch_test.go` | 2 | 91 |
| `pkg/ui/picker_test.go` | 1 | 3021 |
| `cmd/ghyll/main.go` | 1 | 1581 |
| `cmd/ghyll/main_test.go` | 1 | 1458 |
| `pkg/stream/hls/hls_test.go` | 1 | 1063 |
| `plugins/youtube/youtube_test.go` | 1 | 650 |
| `pkg/stream/hls/hls.go` | 1 | 584 |
| `plugins/youtube/api.go` | 1 | 547 |

## God modules — LOC ≥ 400
Large files concentrate too much responsibility in one place. Cross-reference with the Hubs table — a file that is both god-sized *and* a hub is a refactor priority.

| File | LOC | Fan-in | Fan-out |
|------|----:|-------:|--------:|
| `pkg/ui/picker_test.go` | 3021 | 0 | 1 |
| `cmd/ghyll/main.go` | 1581 | 0 | 1 |
| `pkg/ui/picker.go` | 1520 | 0 | 0 |
| `cmd/ghyll/main_test.go` | 1458 | 0 | 1 |
| `pkg/stream/hls/hls_test.go` | 1063 | 0 | 1 |
| `plugins/youtube/api_test.go` | 951 | 0 | 2 |
| `cmd/ghyll/check_test.go` | 837 | 0 | 2 |
| `plugins/twitch/api_test.go` | 799 | 0 | 2 |
| `plugins/kick/kick_test.go` | 748 | 0 | 2 |
| `plugins/youtube/youtube_test.go` | 650 | 0 | 1 |
| `pkg/stream/hls/hls.go` | 584 | 0 | 1 |
| `pkg/stream/hls/m3u8_test.go` | 554 | 0 | 0 |
| `plugins/youtube/api.go` | 547 | 0 | 1 |
| `pkg/stream/hls/m3u8.go` | 497 | 0 | 0 |
| `plugins/twitch/twitch.go` | 452 | 0 | 1 |

## Cycles — strongly-connected components
Files inside a cycle cannot be understood, tested, or deployed independently. Cycles of size 2 often mean a missing seam (extract a third module both depend on); larger cycles usually signal a layering violation.

### Cycle 1 — 2 files
- `pkg/plugin/errors.go`
- `plugins/twitch/errors.go`

## Limitations
- Imports resolved by relative path (where possible) and basename match across the repo. Path aliases, dynamic imports, re-exports, and codegen are likely missed.
- LOC counts non-blank lines; comments are not stripped.
- External / third-party imports are not counted — only intra-repo coupling.
- Treats each file as a node. Class- or function-level coupling is invisible here.
