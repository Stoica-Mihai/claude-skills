# Architectural Hotspots — `/home/mcs/Documents/git/mcshell`

Analyzed **122** source files, **11** internal import edges. Edges count file-to-file imports inside the repo only; external/unresolved imports are dropped.

## Hubs — high fan-in
Many files depend on these. Hubs are often legitimate (core libraries, shared types). They become interesting when paired with god-size, grab-bag naming (`utils`, `helpers`, `common`), or high churn in git history.

| File | Fan-in | LOC |
|------|-------:|----:|
| `Launcher/AppLauncher.qml` | 1 | 629 |
| `Notifications/NotificationCard.qml` | 1 | 335 |
| `LockScreen/LockScreen.qml` | 1 | 296 |
| `Screencast/ScreenCastPickerDialog.qml` | 1 | 294 |
| `Bluetooth/BluetoothPairingDialog.qml` | 1 | 187 |
| `Polkit/PolkitDialog.qml` | 1 | 168 |
| `Wallpaper/WallpaperRenderer.qml` | 1 | 115 |
| `Core/Brightness.qml` | 1 | 77 |
| `Screenshot/ScreenshotOverlay.qml` | 1 | 63 |
| `Bar/ActiveWindow.qml` | 1 | 26 |
| `Config/Namespaces.qml` | 1 | 17 |

## Tangles — high fan-out
These files reach into many corners of the repo. Often a sign of weak single-responsibility — the file is doing too many things, or is a coordination layer that should be split.

| File | Fan-out | LOC |
|------|--------:|----:|
| `shell.qml` | 11 | 297 |

## God modules — LOC ≥ 400
Large files concentrate too much responsibility in one place. Cross-reference with the Hubs table — a file that is both god-sized *and* a hub is a refactor priority.

| File | LOC | Fan-in | Fan-out |
|------|----:|-------:|--------:|
| `Bar/StatusBar.qml` | 791 | 0 | 0 |
| `Config/Theme.qml` | 674 | 0 | 0 |
| `Launcher/AppLauncher.qml` | 629 | 1 | 0 |

## Cycles — strongly-connected components
Files inside a cycle cannot be understood, tested, or deployed independently. Cycles of size 2 often mean a missing seam (extract a third module both depend on); larger cycles usually signal a layering violation.

_No cycles detected._

## Limitations
- Imports resolved by relative path (where possible) and basename match across the repo. Path aliases, dynamic imports, re-exports, and codegen are likely missed.
- LOC counts non-blank lines; comments are not stripped.
- External / third-party imports are not counted — only intra-repo coupling.
- Treats each file as a node. Class- or function-level coupling is invisible here.
