# mcshell — modules doing too much

Ran the hotspot analyzer on the repo, then read the biggest files directly
because the automated report has a major blind spot here (see caveat at the
end). What follows is the human reading; raw numbers are in `raw_report.md`.

## TL;DR — four real hotspots

1. **`Config/Theme.qml` (739 LOC)** — *the* tangling module in this repo.
   Referenced by **91 of ~120 QML files** as a singleton. It bundles
   palettes, color application, wallpaper-hue handling, strategy
   construction, font sizing, and persistence wiring all in one Singleton.
   The analyzer shows it with fan-in = 0 only because QML singleton
   coupling is invisible to import parsing — the *actual* fan-in is the
   highest in the codebase by a wide margin. Any change to Theme's surface
   ripples through nearly every widget.
   **Split it:** `ThemePalettes.qml` (data), `ThemeColors.qml` (currently
   active values), `WallpaperHueStrategy.qml` (the hue-derivation logic),
   `ThemePersistence.qml` (UserSettings wiring). Keep the Singleton facade
   thin and pure-property.

2. **`Bar/StatusBar.qml` (892 LOC, top of god-modules list)** — orchestrates
   weather, clock, sysinfo, systray, workspaces, media, calendar popups,
   waveforms, *and* dropdown coordination with the launcher. The `Bar/`
   directory already has 36 files (5,162 LOC); StatusBar is the assembler
   that knows about all of them and owns popup state for several. Multiple
   `_toggleWeather`, `_panelHeightFor`, `dismissPopups`, `_isFocusedScreen`
   functions point to a single Scope acting as both layout root and
   cross-cutting controller.
   **Split it:** extract a `BarPopupController.qml` (popup open/close +
   focused-screen logic) and let StatusBar.qml only declare the layout.

3. **`Launcher/AppLauncher.qml` (700 LOC, hub of `Launcher/`)** — the only
   file in `Launcher/` that other modules reach (fan-in 1 from `shell.qml`),
   but it pulls together Apps / Wallpaper / Bluetooth / Wifi / Clipboard /
   Power / Audio / Display category panes plus settings. The `Launcher/`
   directory is the second-largest (3,871 LOC across 16+ files) and
   AppLauncher is the single entry point gluing all categories together —
   classic coordinator that has grown into a god component.
   **Split it:** introduce a `LauncherCategoryRegistry.qml` (declarative
   list of categories + their delegates) so AppLauncher becomes a thin
   shell that iterates the registry instead of hard-coding every category.

4. **`shell.qml` (328 LOC, fan-out 11 — the only file in the Tangles
   table)** — imports every top-level directory (Bar, Notifications,
   Launcher, LockScreen, Polkit, Bluetooth, Screencast, Wallpaper,
   Screenshot, Core, Config). That's expected for a root, but combined
   with 23 in-line references to `Theme.` and one-off logic like
   `_windowScreenshotPath = Theme.screenshotPrefix + Date.now() + ".png"`
   it's accumulating glue that doesn't belong at the root. Worth a pass to
   move that screenshot-path composition into `Screenshot/` and let
   `shell.qml` just compose components.

## What the report missed (important)

The analyzer parsed 122 QML files but only resolved **11 internal import
edges**, and the entire `Hubs` table shows fan-in = 1. That is the
QML-coupling caveat the skill warns about: in QML the dominant coupling
mechanism isn't `import` statements — it's **singleton references**
(`Theme.foo`, `UserSettings.bar`) and **component instantiation by name**.
The analyzer can't see either.

Concretely:
- `Config/Theme.qml` is referenced by 91 files but appears with fan-in 0.
- `Config/UserSettings.qml` (432 LOC) is similarly invisible.
- The `Bar/*` and `Launcher/*` internal coupling (StatusBar instantiating
  dozens of sibling components) shows up as 0 edges because QML
  instantiates by component name from the same module's namespace.

So **treat the raw report's hub/cycle sections as not informative for this
codebase**. The god-modules section (which is pure LOC, no graph) and the
single Tangles entry (`shell.qml` — caught only because it has explicit
`import qs.*` statements) are the only mechanically-trustworthy parts. The
four findings above lean primarily on file-size signals plus a manual
grep of singleton references, not on the analyzer's graph.

## Suggested order of attack

`Theme.qml` first — it's the most-coupled module by far, and splitting it
unblocks safer refactors elsewhere because every other widget touches it.
Then `StatusBar.qml`, since extracting popup control there will reduce the
amount of state Theme needs to broadcast. `AppLauncher.qml` and
`shell.qml` are lower priority — they're large but contained.
