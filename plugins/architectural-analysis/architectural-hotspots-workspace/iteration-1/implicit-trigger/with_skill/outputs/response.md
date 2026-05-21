Ran a hotspot analysis on the mcshell repo (122 `.qml` files, 357 internal coupling edges). Four files stand out, and the picture is clearer than I expected — this is a fairly healthy QML tree with two genuine god-modules and one borderline one.

## Files worth breaking apart

1. **`Bar/StatusBar.qml`** — LOC 791 (largest file), fan-out 33, fan-in 1.
   This is the single most obvious refactor target. It hits **both** the god-modules table and the top of the tangles table, and almost nothing depends on it (fan-in 1). That combination — huge, reaches into everything, depended on by nothing — is the textbook profile of a coordination layer that has absorbed responsibilities it should be delegating. Concretely: it appears to be orchestrating every bar segment (clock, weather, media, sys info, tray, workspaces, volume, battery, ...) inline. Worth splitting into a thin `StatusBar` shell plus per-segment composers, or pulling the segment wiring into a registry the bar iterates over.

2. **`Launcher/AppLauncher.qml`** — LOC 629, fan-out 14, fan-in 0.
   Second god module, same shape as StatusBar but smaller: a tangling root with no incoming edges. Reaches into the various `Settings*`, `Category*`, and `Carousel*` files. Likely doing tab/mode dispatch, animation, and category wiring all in one place. Candidate for extraction of a launcher-state controller + a thin view file.

3. **`Config/Theme.qml`** — LOC 674, fan-in 90.
   Massive fan-in, but this is a `pragma Singleton` — so the 90 dependents are *global access to theme tokens*, not real coupling. The size is the only concern here. If it is genuinely 674 lines of token definitions, that is fine and even desirable in one place. If it has *logic* (computed palettes, runtime theme switching, derived values) mixed in with tokens, that logic wants its own file (`ThemeRuntime.qml`) so the token file can stay a flat reference. Worth a 5-minute eyeball before deciding.

4. **`shell.qml`** — LOC 297, fan-out 9.
   Not over-sized, but it is the top-level wiring file and imports nearly every `qs.*` module. That is structurally appropriate for a shell entry point, so flag it only if you find yourself constantly editing it to plumb new modules through; if so, an event-bus / `ShellActions` pattern (which the repo already has a stub for in `Core/ShellActions.qml`) would let new modules self-register instead of being threaded through `shell.qml`.

## Things that are *fine*, despite looking suspicious

- **`Config/Theme.qml`** fan-in 90 — singleton, expected.
- **`Config/UserSettings.qml`** fan-in 35, LOC 376 — also a settings hub; large but focused. Not a refactor target unless you're already in there.
- **`Widgets/SkewRect.qml`**, **`Widgets/Separator.qml`**, **`Core/OverlayWindow.qml`**, **`Core/SafeProcess.qml`** — all small (15–60 LOC), high-ish fan-in, focused names. Healthy hubs; leave alone.

## What's *not* in the report

- **No dependency cycles.** Tarjan found zero strongly-connected components of size > 1 in the import graph. The module layering is clean.
- No grab-bag `utils.qml` / `helpers.qml` / `common.qml` file. Naming discipline is good across the tree.

## Caveats on these numbers

- The skill's bundled analyzer doesn't recognise `.qml` extensions, so it reported 0 files. I ran a QML-aware variant of the same four-dimension analysis (hubs / tangles / god modules / cycles) — same scoring approach but applied to QML's import + component-instantiation model. Code lives at the raw-report path below.
- QML coupling is fuzzier than e.g. Python imports: components are referenced by capitalised identifier, scoped by `qs.<Module>` imports. The resolver scopes references to imported directories + same-directory siblings — so a reference to a component in a *non*-imported module can be missed, and identical stems in different modules can produce false positives. Treat the numbers as directional.
- LOC is non-blank lines, not de-commented.

Raw analyzer output (full hub/tangle/god tables) is at:
`/home/mcs/Documents/git/claude-skills/plugins/architectural-analysis/architectural-hotspots-workspace/iteration-1/implicit-trigger/with_skill/outputs/raw_report.md`

If you want a deeper look at any of the four files above (specifically what to extract from `StatusBar.qml` or `AppLauncher.qml`), say the word and I'll read through them and propose concrete split lines.
