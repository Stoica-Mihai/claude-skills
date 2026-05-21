# mcshell — architectural hotspots / tangling modules

Quick read of `/home/mcs/Documents/git/mcshell` (Quickshell QML config, 122 .qml files, ~16.5K LOC). Ranked by "doing too much AND pulling the rest of the codebase in with it."

## Tier 1 — strongest candidates to break apart

### 1. `Config/Theme.qml` — the god singleton (739 LOC, imported by 91/122 files)
Single `pragma Singleton` holding **13 different concern blocks** in one file:
- Hard-coded **palettes table** (12 themes inlined, lines 11–173, ~165 LOC of data)
- Wallpaper auto-theming `Connections` + lifecycle
- **Wallpaper colorisation strategies** (lines 245–336)
- Mutable color properties (Tokyo Night defaults)
- Opacity, surface alphas, animation durations, notification timeouts
- Screenshot config
- Layout constants
- Typography
- **Icons (Nerd Font codepoints)** — ~100 LOC block
- **"Legend hint" building blocks** — ~100 LOC at the tail, clearly a different domain (KeybindHints)

Why it tangles: 91 files depend on `Theme.*`, so the singleton is a chokepoint. The mix of "design tokens" (colors/spacing/typography) with **behavior** (wallpaper-derived palette strategies, color extraction connections to `UserSettings`) means every UI file transitively pulls in wallpaper-theming logic.

**Break apart into:** `Tokens.qml` (colors+spacing+typography+anim), `Palettes.qml` (data only), `WallpaperTheming.qml` (strategies + auto-theming connections), `Icons.qml` (nerd-font glyphs), `KeybindLegend.qml` (move to `KeybindHints/`). Theme stays as a thin façade or is dissolved.

### 2. `Config/UserSettings.qml` — the bag-of-everything settings singleton (432 LOC, 34 dependents, **108 properties**, 19 functions)
Aliases for every setting in the shell — DnD, night-light, wallpaper folder/fill/rotate, theme name, idle timeout, power profile, border animation, blur, weather (lat/lon/country/name), clock format, **sysInfo with 9+ flags**, audio rate, **WiFi card field visibility (7 toggles)**, **Bluetooth card field visibility (6 toggles)**, hidden-GPUs JSON…

Why it tangles: it's the canonical example of "central registry every feature reaches into." Sysinfo files touch it 16×, settings panels touch it 15–34× each (`SettingsDisplay.qml` 34×). Adding any new feature module means amending this file.

**Break apart into:** per-domain settings groups (`SettingsSysInfo`, `SettingsWeather`, `SettingsWallpaper`, `SettingsCardFields`, `SettingsClock`), all backed by the same adapter — but each domain owned by its feature directory rather than `Config/`.

### 3. `Bar/StatusBar.qml` — the bar god-object (892 LOC, the largest file)
Mixes:
- Per-screen Wayland surface setup (exclusive zone, fullscreen surface, dismiss area)
- Left / center / right segment **layout**
- **Panel dispatch table `_barPanels`** mapping 10+ panel names → owner-dropdown + height callbacks (volume, media, sysinfo, sysInfoSettings, wifiSettings, bluetoothSettings, clockSettings, calendar, weather, notifications, trayicons, keybinds…)
- 3 separate dropdown owners (`leftDropdown`, `centerDropdown`, `sharedDropdown`) — 79 internal references
- 9 inline `Loader { … }` blocks for each panel's content
- WiFi state + Bluetooth state observation
- 7 outbound signals re-routing into shell.qml

Why it tangles: it's both the visual bar **and** the panel/dropdown router. Every new bar panel touches StatusBar.qml.

**Break apart into:** `BarSurface.qml` (Wayland surface + segments), `BarPanelRouter.qml` (the `_barPanels` dispatch + 3 dropdowns), and per-panel content components living next to their feature (most already do — StatusBar just glues them).

## Tier 2 — clear secondary hotspots

### 4. `shell.qml` — the root orchestrator (328 LOC)
Imports **15 subsystems** and personally wires:
- StatusBar Variants per screen (with 9 signal hookups)
- LockScreen / Polkit / BluetoothPairing / ScreenCastPicker / WallpaperRenderer / WallpaperRotator / ScreenshotOverlay
- IdleMonitor dynamically created via `Qt.createQmlObject` (workaround)
- **Screenshot portal bridge** (`Connections` to `ScreenshotPortal` + `screenshot` — ~30 LOC of glue)
- **Window-screenshot SafeProcess** (lines 239–252) — feature logic, not orchestration
- `_mediaPlaying` MPRIS aggregator inline
- **Two near-duplicate IPC surfaces**: `DBusIpcHandler` (lines 259–281) and `IpcHandler` (lines 284–327). Both wrap the same `_dispatchPanel` / `_dispatchLauncher` calls. ~70 LOC of duplicated dispatch.

**Break apart:** extract `IpcSurface.qml` (both handlers in one file, deduped), `ScreenshotPortalBridge.qml`, `MediaInhibitor.qml`. Leave shell.qml as a 100-LOC top-level composition.

### 5. `Launcher/AppLauncher.qml` (700 LOC, 21 functions)
Combines tab/category state, carousel layout maths (`calcRowX`, `_snapToTab`, `animateTo`, `_lineLeft/_lineRight`), open/close NumberAnimations on `_animProgress`, search field focus management, level/mode dispatch — and the entire UI tree. The carousel/underline animation logic and the open/close transition are two separable sub-features inside one component.

**Break apart:** `LauncherTabBar.qml` (tab underline animator), `LauncherCarousel.qml` (snap + animateTo + calcRowX), `LauncherOpenAnim.qml` (transitions). AppLauncher becomes a composition root.

## Tier 3 — worth watching, not urgent

- `Bar/SysInfoPanel.qml` (424) + `SysHistory` + `SysWaveform` + `SysInfoSettingsPopup` = **923 LOC** in one feature, but it's already split by file. The settings popup duplicates a lot of UserSettings binding boilerplate — likely a DRY problem more than a tangling one.
- `Bar/Weather*.qml` cluster = **948 LOC** across 6 files — well-factored already, just large.
- `Config/UserSettings.qml`'s `sysInfoHiddenGpusJson` + `primaryGpu()` etc. is GPU concern leaking into general settings.

## Cross-cutting observation

The two singletons in `Config/` (Theme + UserSettings) are the **gravity wells**. Almost every coupling complaint in the codebase ultimately routes through them: Theme is read by 75% of files, UserSettings is read by 28% and is the only place feature toggles land. Splitting them domain-wise would unlock the largest reduction in tangling.

## Files referenced (absolute paths)
- `/home/mcs/Documents/git/mcshell/Config/Theme.qml`
- `/home/mcs/Documents/git/mcshell/Config/UserSettings.qml`
- `/home/mcs/Documents/git/mcshell/Bar/StatusBar.qml`
- `/home/mcs/Documents/git/mcshell/shell.qml`
- `/home/mcs/Documents/git/mcshell/Launcher/AppLauncher.qml`
