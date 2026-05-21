# Hotspots in mcshell — what's doing too much

I walked the repo (122 QML files, ~16.5k LoC) looking at: file size, fan-in (who imports/references it), fan-out (what it pulls in), and how mixed its responsibilities are. Four modules stand out as "doing too much and tangling the codebase." A fifth is a structural smell worth flagging.

## 1. `Bar/StatusBar.qml` — 892 LoC, the worst offender

The single biggest file in the repo, and it's a god-component:

- Imports five sibling modules (`qs.Config`, `qs.Core`, `qs.Widgets`, `qs.NotificationHistory`, `qs.KeybindHints`) — more than any other file in `Bar/`.
- Owns `launcherOpen` state, `unreadNotifications`, `hasPopup` aggregation across three dropdowns (`sharedDropdown`, `centerDropdown`, `leftDropdown`), `_panelHeightFor`, `_isFocusedScreen`, `_toggleWeather`, `dismissPopups`, plus the entire bar layout with ~20 distinct child component types (Loader x8, CapsuleItem x4, BarSegment x3, Workspaces, Weather, Volume, SysTray, VolumeWaveform, VolumeSlider, Separator, ThemedTooltip…).
- Acts as a hub: 7 sibling `Bar/*.qml` files reference `StatusBar` (Battery, ActiveWindow, CapsuleItem, Media, Volume, MediaPopupContent), plus `Core/NiriAppsCache.qml` and `shell.qml` — so changes here ripple everywhere.

**Break it apart:** extract a `BarPopupController` (dropdown/popup state + `dismissPopups`), a `BarLayout` (the visual row composition), and a `BarFocus` (focused-screen + launcher-coordination glue). The current file is mixing layout, controller, and cross-module coordination in one place.

File: `/home/mcs/Documents/git/mcshell/Bar/StatusBar.qml`

## 2. `Config/Theme.qml` — 739 LoC, 91 files depend on it

This is the most-imported module in the repo (91 inbound dependents, 1378 `Theme.` references). That alone is fine for a theme singleton — but it's not just a theme:

- Holds palette definitions for multiple named themes ("Tokyo Night", …).
- Computes wallpaper-derived colors (`_applyWallpaperHue`, `_strategyParams`, `_buildStrategy`, `_strategyIndex`, `wallpaperStrategies`).
- Listens to `UserSettings` changes (`onWallpaperPathChanged`, `onThemeNameChanged`, `onWallpaperStrategyChanged`, `onSettingsLoaded`) and reacts.
- Owns animation timings (`animFast/Normal/Smooth/Carousel/Slider/Crossfade`), spacing scale, font scale, opacity scale, and glass/alpha policies.
- Exposes 23 functions including `withAlpha`, `glassSurface`, `glassBg`, plus wallpaper-strategy machinery.

It's `Theme` + `DesignTokens` + `WallpaperColorEngine` + `Animations` glued together. Because *everything* imports it (the top usages are `Theme.fontFamily` x152, `Theme.accent` x129, `Theme.spacingMedium` x43 — pure design tokens), any churn in the wallpaper-color logic forces a re-evaluation of the world.

**Break it apart:** split into `Tokens` (colors, spacing, font scale, animation durations — the 90% everyone consumes), `Palette` (named palette dict + `applyPalette`), and `WallpaperColorStrategy` (the hue/strategy engine that currently lives inside Theme but only matters to one feature).

File: `/home/mcs/Documents/git/mcshell/Config/Theme.qml`

## 3. `Launcher/AppLauncher.qml` — 700 LoC

A single component carrying the entire launcher controller plus its window chrome:

- Public API: `open`, `close`, `toggle`, `openTab`, `navigate`, `switchTab`, `activate`, `refocusSearch`, `supportedModesFor`.
- Private state machine: `_initLauncher`, `_requestOpen`, `_openTransition`, `_closeTransition`, `_animProgress`, `_suppressCarouselAnim`, `_animEnableTimer`, `_suspendVisible`, plus Wayland-specific surface-remap workarounds documented in the header comment.
- Tab routing across apps / clipboard / wifi / bluetooth / wallpaper / settings categories.
- Search field, carousel geometry (`calcRowX`), keyboard nav.

It's a window + a state machine + a router + an animator. The Wayland blur-remap hack alone deserves its own component.

**Break it apart:** `LauncherWindow` (surface lifecycle + blur-remap workaround), `LauncherController` (open/close/tab routing, `_dispatchLauncher` already exists in `shell.qml`), `LauncherTransition` (the `_openTransition`/`_closeTransition`/`_animProgress` machinery).

File: `/home/mcs/Documents/git/mcshell/Launcher/AppLauncher.qml`

## 4. `Config/UserSettings.qml` — 432 LoC

A "settings singleton" that has quietly absorbed feature logic. Settings persistence is fine, but it also owns:

- Wallpaper assignment logic: `setWallpaper`, `setWallpaperForScreen`, `setWallpapersForScreens`, `_applyFolder`, `_splitPath`.
- SysInfo GPU visibility policy: `sysInfoGpuVisible`, `setSysInfoGpuHidden`, `primaryGpu`.
- Night-light mode constants (`modeOff/modeManual/modeAuto`, `defaultNightTemp`) — domain knowledge that doesn't belong to a generic settings store.
- Save debouncing via `_save` / `saveTimer`.

Pulls in `Quickshell.Services.SysInfo`, `Qs.NightLight`, and `qs.Core` — fan-out a config store shouldn't have. 34 files reference `UserSettings.x`.

**Break it apart:** keep `UserSettings` as a dumb JsonAdapter + save-debouncer. Move `setWallpaper*` / `_applyFolder` into `Wallpaper/WallpaperService`, move GPU visibility into a `SysInfoPolicy`, and put night-light constants on the night-light module.

File: `/home/mcs/Documents/git/mcshell/Config/UserSettings.qml`

## 5. Structural smell: `shell.qml` as IPC concentrator

`shell.qml` (328 LoC) imports 14 internal modules — by far the highest fan-out — and is doing two distinct jobs: composing the top-level scene tree *and* hosting two IpcHandler/DBusIpcHandler blocks with ~15 toggle/dispatch methods (`toggleLauncher`, `lock`, `toggleDnd`, `toggleVolume`, `toggleNotifications`, `toggleSysInfo`, `toggleBluetooth`, `toggleWifi`, `launcherApps/Clipboard/Wifi/Bluetooth/Wallpaper/Settings`, `toggleKeybinds`, screenshot dispatch…). The IPC surface should be its own file (`ShellIpc.qml` or `Core/IpcRouter.qml`) so the root stays a pure scene composer.

File: `/home/mcs/Documents/git/mcshell/shell.qml`

## Sanity check on the rest

- `Notifications/NotificationCard.qml` (380), `Screenshot/ScreenshotScreenOverlay.qml` (378), `Bar/SysInfoPanel.qml` (424), `Launcher/CategoryWallpaper.qml` (400) are all large but feature-local — high LoC, low fan-out, single responsibility. Not priority targets.
- `Bar/` has 36 files; the sub-component decomposition there is actually healthy *except* for StatusBar concentrating all the wiring.
- Cross-module coupling is currently clean (only `qs.Config` x99, `qs.Widgets` x41, `qs.Core` x23 are widely imported; every other module is imported exactly once, by `shell.qml`). The tangle is **inside** the hub files, not in the dependency graph between modules.

## Recommended order to break things apart

1. **StatusBar** — biggest single win, highest internal fan-in, will unblock cleaner Bar/* changes.
2. **Theme** — splitting tokens vs. wallpaper-color engine will isolate churn from 91 dependents.
3. **UserSettings** — pulling wallpaper/sysinfo/night-light logic out shrinks fan-out and lets the persistence layer be trivially testable.
4. **AppLauncher** — separate window/controller/transition.
5. **shell.qml IPC** — small, mechanical extraction; do it last as a tidy-up.
