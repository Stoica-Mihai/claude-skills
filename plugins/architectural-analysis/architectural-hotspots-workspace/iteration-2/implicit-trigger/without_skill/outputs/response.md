# mcshell — architectural hotspots

Quick read of `/home/mcs/Documents/git/mcshell` (122 QML files, ~16.5k LOC). Looked at file sizes, section markers (`// ── …`), imports/fan-in across `qs.*`, and the structural primitives (`Loader`, `Timer`, `Process`, `FileView`, `Connections`) inside the biggest files.

## Coupling overview

Fan-in on the `qs.*` singletons / module exports (number of files importing each):

| Module      | Imported by |
| ----------- | ----------- |
| `qs.Config` | 99          |
| `qs.Widgets`| 41          |
| `qs.Core`   | 23          |
| everyone else | 1–2       |

Plus direct symbol references:
- `Theme.*` referenced in **91** QML files
- `UserSettings.*` referenced in **34** files
- `ShellActions.*` referenced in 3 files

So `qs.Config` (which exports `Theme` + `UserSettings` + `Namespaces`) is the spine of the codebase, and almost everything reaches into it. That's the single biggest source of "tangling" — any change to those two files ripples broadly.

## Top hotspots, ranked by "doing too much"

### 1. `Config/UserSettings.qml` — 432 lines, ~138 properties/functions
File: `/home/mcs/Documents/git/mcshell/Config/UserSettings.qml`

This is the clearest god-object in the repo. It is nominally a persisted-settings singleton, but it has absorbed at least six unrelated responsibilities:

- JSON adapter for `~/.config/mcshell/settings.json` (FileView + debounce Timer + mkdir SafeProcess) — lines ~215–315
- **Night-light gamma scheduling** — sunrise/sunset math, `_nightFactor`, auto-phase timer, `_setGammaTemp` (lines ~317–414). This is a runtime service, not a setting.
- **Wallpaper path/folder logic** — `_splitPath`, `setWallpaper`, `setWallpaperForScreen`, `setWallpapersForScreens`, per-screen JSON cache (lines ~152–210)
- **Wallpaper folder auto-detection** — another `SafeProcess` shelling out to bash (lines ~418–431)
- **SysInfo / GPU filtering** — `sysInfoHiddenGpus`, `primaryGpu()` scanning `SysInfo.gpus[].connectedDisplay` (lines ~104–135)
- **Clock format composition** — `clockTimeFormatString`, `clockFormatString` (lines ~140–147)
- Static option tables that belong to the UI (wallpaperRotateOptions, wallpaperFillModes) — lines ~34–50

Why this matters for tangling: 34 files import `UserSettings.*`, so every one of those responsibilities is wired to consumers. Touching night-light scheduling forces editing the same file that 34 UI sites pull from for unrelated settings. The JsonAdapter block at lines 226–282 already lists ~60 raw properties — adding any setting means editing both the adapter block and the alias block above it.

Suggested splits:
- `Core/NightLight.qml` — owns mode, schedule, gamma, timer (UserSettings keeps only the persisted strings)
- `Core/WallpaperPaths.qml` — `setWallpaper*`, `_splitPath`, per-screen map, default-folder detection
- `Core/SysInfoGpus.qml` — hidden-GPU list, `primaryGpu()`
- Leave `UserSettings` as a thin facade over the JsonAdapter

### 2. `Config/Theme.qml` — 739 lines
File: `/home/mcs/Documents/git/mcshell/Config/Theme.qml`

Section headers tell the story — this single singleton holds: palette tables, wallpaper auto-theming (`onWallpaperPathChanged`, `onThemeNameChanged`, `onWallpaperStrategyChanged` Connections), **wallpaper-color-extraction strategies** (`_strategyParams`, `_buildStrategy`, `_applyWallpaperHue` — pulling from `Qs.VibrantColor`), then ~20 writable color properties, opacity scale, surface alphas, animation durations, notification timeouts, screenshot constants, layout constants, typography, ~100 Nerd-Font icon codepoints, and "legend hint building blocks".

Concretely: design tokens (colors/spacing/typography/animation) are mixed with runtime behavior (wallpaper hue extraction + signal handlers + strategy registry). Since 91 files import Theme, any change to the strategy code recompiles the binding graph for nearly every QML component in the shell.

Suggested splits:
- `Theme.qml` keeps just tokens (colors, sizes, animations, icons)
- `Core/Palette.qml` for palettes + applyPalette
- `Core/WallpaperTheming.qml` for strategies + Connections (already adjacent to existing `Qs.VibrantColor` integration)

### 3. `Bar/StatusBar.qml` — 892 lines (largest file in the repo)
File: `/home/mcs/Documents/git/mcshell/Bar/StatusBar.qml`

Imports 7 different `qs.*` / `Quickshell.*` namespaces (Wayland, Bluetooth, Networking, SystemTray, Config, Core, Widgets, NotificationHistory, KeybindHints — basically all of the shell). What it actually contains in one file:

- Exclusive-zone reservation surface
- Fullscreen click-dismiss surface
- Left / center / right bar segments with their layouts
- **A "shared dropdown" right-segment popup** that internally Loader-gates 8 different panels: volume, tray icons, sysinfo, sysinfo settings, wifi settings, bluetooth settings, notifications, media (lines 614–768)
- A center dropdown for calendar / weather / clock settings (lines 777–817)
- A left dropdown for keybind hints (lines 820–845)
- WiFi state derivation walking `Networking.devices.values` (lines 863–879)
- Bluetooth state derivation walking `Bluetooth.defaultAdapter.devices.values` (lines 881–891)
- Recording state proxy
- Hidden Volume + Battery instances kept at root for accessibility

The `sharedDropdown` is effectively a switch-statement-as-QML — it's the routing fabric for every right-segment panel, and right now both the routing and the panel composition live inline. Each `activePanel === "…"` string is a string contract repeated in `togglePanel` calls scattered through the bar's left/center/right capsules.

Suggested splits:
- Extract `Bar/RightDropdown.qml` (the AnimatedPopup + its 8 Loaders), `Bar/CenterDropdown.qml`, `Bar/LeftDropdown.qml`. StatusBar then just composes three dropdowns.
- Move the WiFi/Bluetooth state derivation into `Core/NetworkState.qml` + `Core/BluetoothState.qml` — those derivations also appear (or are duplicated) in the settings popups, so consolidating gives multiple call sites a single source of truth.
- The panel-id strings ("volume", "trayicons", "sysinfo", "sysInfoSettings", "wifiSettings", "bluetoothSettings", "notifications", "media") should be a named enum/constants object so the bar capsules and the dropdown agree by symbol, not string.

### 4. `shell.qml` — 328 lines (root entry)
File: `/home/mcs/Documents/git/mcshell/shell.qml`

Imports **15 `qs.*` / `Quickshell.*` modules** directly — this is the natural choke-point so big fan-out is expected, but it has also accumulated:

- Panel-toggle dispatcher (`_togglePanel`, `_toggleMode`, `_dispatchPanel`, `_resolveMode`) — lines ~28–91
- AppLauncher lifecycle (Loader gating, `_toggleLauncher`, `_dispatchLauncher`) — lines ~92–109, 217–220
- Recording lifecycle (Loader + `_toggleRecording`) — lines 218–222
- xdg-desktop-portal screencast wiring (`_portalRequest`, Connections) — lines ~171–185
- Screenshot orchestration (`screenshotFull`, `screenshotArea`, `screenshotWindow`, `_windowScreenshotPath`) — lines ~186–242
- Two DBus services exposing the same toggleLauncher / lock / toggleDnd / toggleBluetooth / toggleWifi / toggleVolume / toggleNotifications / toggleSysInfo / toggleKeybinds — lines ~265–297

The DBus surface in particular looks duplicated (both services expose `toggleLauncher` and `lock`). And the "dispatch a panel by name with a mode" pattern is implemented inline here on top of being implemented inline in StatusBar — same string-keyed routing in two places.

Suggested splits:
- `Core/PanelRouter.qml` — single source of truth for panel ids, mode resolution, and dispatch. Both `shell.qml` and `StatusBar.qml` consume it; the `activePanel === "x"` strings become enum-like constants.
- `Core/ScreenshotController.qml` — the three capture flows + window-screenshot path bookkeeping
- `Core/DBusFacade.qml` — the two `DBusService` blocks (likely collapsible into one once the duplication is visible side-by-side)

### 5. `Launcher/AppLauncher.qml` — 700 lines
File: `/home/mcs/Documents/git/mcshell/Launcher/AppLauncher.qml`

Less egregious than the above but still mixes a lot: public API (`open/close/toggle/openTab`), focused-output-aware open flow, open/close transition state machine, window setup, category registry, tab-state machine, **carousel geometry math + snap/animate state machine** (lines ~183–390), tab-switching, search-bar custom Canvas paint with two `Connections` re-paint hooks, plus the giant UI tree.

The carousel/tab animation engine (200+ lines around 183–390) is self-contained and could move to `Launcher/TabCarousel.qml`. The "_requestOpen → focused-output → transition" sequencing could move to a small controller so `AppLauncher.qml` is just the UI shell.

## Cross-cutting observation: the `Config` package is the bottleneck

The most useful change here isn't any single split — it's recognizing that `qs.Config` has become the "everything" module. `Theme` (91 importers) and `UserSettings` (34 importers) collectively touch most of the codebase, and both files have absorbed runtime behavior (gamma scheduling, wallpaper hue extraction, GPU filtering, wallpaper path math, default-folder probing) that has no business in a config singleton.

If you only do one round of breaking-apart, the highest-leverage move is:

1. Carve runtime services out of `Config/UserSettings.qml` and `Config/Theme.qml` into new `Core/` singletons (NightLight, WallpaperPaths, WallpaperTheming, Palette, SysInfoGpus).
2. Leave `Config/` holding only persisted-settings aliases and static design tokens.
3. Then extract the right-segment dropdown out of `StatusBar.qml` and introduce a `PanelRouter` shared by `shell.qml` and `StatusBar.qml` so panel-id strings stop being duplicated routing keys in two places.

Those changes should drop the per-file import surface on the bar/launcher significantly and make config edits stop ricocheting through the binding graph of 91 files.
