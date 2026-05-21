# mcshell — modules that are doing too much

I ran the hotspot analyzer (`find_hotspots.py`) on the repo and then cross-checked it by hand, because QML's coupling model is largely invisible to a pure import-graph: `import qs.Config` is a one-line edge that grants access to every singleton in that module, so the fan-in numbers in the raw report are dramatically understated. The raw report sits at `outputs/raw_report.md` for reference, but you should treat it as a floor, not the truth.

## Big-picture caveat

The analyzer reports 122 source files and only **11 internal import edges** — a hub like `Theme` shows fan-in = 0 in the report because nothing imports the *file*, but `Theme.` is referenced in **91 of 122 QML files** and `UserSettings.` in 34. So the four sections below combine the analyzer's signal with a manual pass over the largest files. Take all of this as "candidates to look at," not a verdict.

## Top refactor candidates

### 1. `Bar/StatusBar.qml` — 892 LOC, structurally the worst offender
The biggest file in the repo and the most tangled in responsibilities. In a single root `Scope`:

- Owns three separate dropdown surfaces (`sharedDropdown`, `centerDropdown`, `leftDropdown`) plus the bar's exclusion-zone and main `PanelWindow`.
- Hosts a hand-maintained `_barPanels` dispatch table for 13 different panel kinds (keybinds, calendar, weather, clockSettings, volume, notifications, media, sysinfo, sysInfoSettings, wifiSettings, bluetoothSettings, trayicons, tray) — each entry is `{ owner, fullHeight }`.
- Implements weather's two-mode (`view`/`edit`) special-case dispatch separately from the generic path.
- Hand-rolled keyboard nav routing (`_activeNav`) that hardcodes four specific panels.
- Bar geometry math (parallelogram polygons for left/center/right) co-located with the panel orchestration.
- Three bar segments laid out inline with their `BarSegment` polygons.

The smell: this is a **god coordination layer** masquerading as a view. The panel registry, the focused-output gating logic, the multi-monitor dropdown coordination, and the bar layout shouldn't all live in one file.

Suggested split:
- Extract a `PanelRouter` (or move `_barPanels` + `_panelHeightFor` + `panelToggleTrigger` handling into one) — a single owner of "which panel is open where".
- Extract `BarLayout.qml` for the three segments + their polygon definitions.
- Push the special-case `_toggleWeather` into a per-panel adapter or just promote weather's "modes" to first-class behaviour in the dispatch table so it stops being a branch.

File: `/home/mcs/Documents/git/mcshell/Bar/StatusBar.qml`

### 2. `Config/Theme.qml` — 739 LOC, a global grab-bag singleton
Hits both god-module (size) and de-facto hub (91 files reference `Theme.`). What's inside:

- 12 named colour palettes inline (Tokyo Night, Catppuccin Mocha, Gruvbox, Nord, Dracula, Rosé Pine, …) as object literals.
- A "wallpaper-derived" Material-Tonal-style palette with strategy params.
- Animated `Behavior on color` declarations for every surface colour.
- Layout/spacing/radius scales (`spacingMicro`/`Tiny`/`Small`/…, `radiusTiny`/`Small`/…).
- Animation durations (13 of them, each named for what they're used for: `animCarousel`, `animLockShake`, `animMarquee`).
- ~80 Nerd-Font icon glyph constants (volume, media, network, system, battery, weather, power, clipboard, …).
- Helper functions: `withAlpha`, `glassSurface`, `glassBg`, `urgencyColor`, `volumeIcon`, `batteryIcon`, `legend`, `centerAnchorX`.
- Hint-string fragments for keyboard legends.

A change to *any* icon constant or spacing token invalidates Theme for the whole shell. The blast radius is the entire codebase.

Suggested split:
- `Config/Palettes.qml` — the 12 palette literals + the wallpaper-derived strategy.
- `Config/Icons.qml` — the Nerd Font codepoints (and `volumeIcon`, `batteryIcon` helpers that live on top of them).
- `Config/Metrics.qml` (or `Layout.qml`) — spacing/radius/animation scales.
- Keep `Theme.qml` as a thin facade that re-exports / proxies, so the 91 call sites don't all have to change at once.

File: `/home/mcs/Documents/git/mcshell/Config/Theme.qml`

### 3. `Launcher/AppLauncher.qml` — 700 LOC, the overlay god-controller
21 functions on one component. Inside the same file it owns: the open/close transitions, surface-screen swap for multi-monitor portal handling, tab indexing (`_tabIndex`, `switchTab`, `supportedModesFor`), carousel state and animations (`_snapToTab`, `_applySnap`, `animateTo`), keyboard navigation (`navigate`, `activate`), the search field, and per-tab lifecycle callbacks (`onTabEnter`/`onTabLeave`/`onSearch`/`onOpenTarget`).

Plus a `Canvas`-paint signal coupling to two specific Theme properties (`onSurfaceContainerChanged`, `onOutlineVariantChanged`, `onBlurEnabledChanged`) — Theme leakage into the launcher's rendering path.

Suggested split:
- `LauncherCarousel.qml` — `_snapToTab`/`_applySnap`/`animateTo`/`calcRowX` + the carousel model wiring.
- `LauncherNav.qml` (or controller object) — `navigate`/`activate`/`switchTab`/`_tabIndex`/`supportedModesFor`.
- Keep `AppLauncher.qml` as the surface + transition orchestrator.

File: `/home/mcs/Documents/git/mcshell/Launcher/AppLauncher.qml`

### 4. `shell.qml` — 328 LOC, fan-out 11 (the only file the analyzer flagged as a tangle)
Not god-sized, but it's the single point that touches every subsystem. It hosts: the IPC handlers (D-Bus + native), panel/launcher dispatch logic, screenshot orchestration (full/area/window), portal request/response routing, lazy-loader management, idle-monitor dynamic creation, MPRIS playback-state aggregation, and a hand-rolled mode-validation function (`_resolveMode`).

The IPC surface alone is ~70 lines of repetitive `function toggleX(mode): void { shell._dispatchPanel("x", mode); }` declarations across two handlers (D-Bus and native IPC) that mostly mirror each other.

Suggested split:
- Move the two `IpcHandler`/`DBusIpcHandler` blocks into `Ipc/ShellIpc.qml` and `Ipc/ShellDBus.qml`. The duplication between them is the giveaway — they're a single command table expressed twice.
- Extract `ScreenshotController.qml` for the three screenshot paths + the portal bridge (currently three `Connections` blocks + `_windowScreenshotProc` + the portal request state machine all live inline).
- Leave `shell.qml` as the composition root.

File: `/home/mcs/Documents/git/mcshell/shell.qml`

## Other things worth noting (not top priority but in the queue)

- `Config/UserSettings.qml` — 432 LOC, 131 property/function declarations. Another god-singleton, same shape as Theme. Same fix applies if you ever want to split it: facade re-exports while the storage lives in per-domain JSON adapters.
- `Notifications/NotificationCard.qml` (380 LOC) and `Screenshot/ScreenshotScreenOverlay.qml` (378 LOC) are large but each is doing one job — flag for later, not now.
- `Launcher/CategoryWallpaper.qml` (400 LOC), `Bar/SysInfoPanel.qml` (424 LOC), `Bar/CalendarPopup.qml` (363 LOC) — each handles one panel/category, so the size reflects feature surface, not tangle. Lower priority.
- **No cycles detected.** The graph has no strongly-connected components — coupling is hub-shaped (everyone depends on Config + Core), not cyclic. That's actually a good sign.

## How to read this

The four candidates above stack-rank by "concentration of unrelated responsibilities × number of things that depend on them". If you want one to start with: **Theme.qml**, because the split is mechanical (move palettes / icons / metrics into separate singletons behind a facade) and reduces risk for every later refactor. **StatusBar.qml** is the highest-impact but most architectural change. **shell.qml** is the easiest win in lines-of-code terms — the two IPC handlers are ~70 lines of dispatch boilerplate that wants to be a table.

### Caveats

- QML coupling is mostly through singleton-references and component-instantiation, neither of which the file-level import resolver sees. So treat the analyzer's "fan-in = 0" verdict for Theme, UserSettings, ShellActions, NotificationDispatcher, FocusedOutput etc. as a known false negative — those are real hubs.
- LOC is non-blank lines including comments; some of the larger files are well-commented and the "dense" LOC is lower than the raw number suggests. Theme in particular has lots of one-line `Behavior on …` declarations.
- I haven't looked at git churn — if you have a sense of which of these files actually change often or break often in merges, that's the strongest tiebreaker for "which one to start with".
