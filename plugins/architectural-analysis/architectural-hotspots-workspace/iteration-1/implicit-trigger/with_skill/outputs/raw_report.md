# Architectural Hotspots — `/home/mcs/Documents/git/mcshell`

QML project (Quickshell). Analyzed **122** `.qml` files, **357** internal coupling edges. Edges are file-to-file references via `qs.<Module>` imports + capitalised-identifier component instantiation, restricted to imported directories. External Quickshell/QtQuick imports are dropped.

> NOTE: The skill's bundled `find_hotspots.py` does NOT recognise `.qml` extensions, so it reported 0 files. This report was produced by a QML-aware variant of the same four-dimension analysis (hubs / tangles / god modules / cycles) using the same scoring approach.

## Hubs — high fan-in

| File | Fan-in | LOC |
|------|-------:|----:|
| `Config/Theme.qml` | 90 | 674 |
| `Config/UserSettings.qml` | 35 | 376 |
| `Widgets/SkewRect.qml` | 12 | 56 |
| `Config/Namespaces.qml` | 9 | 17 |
| `Widgets/Separator.qml` | 8 | 15 |
| `Widgets/CyclePicker.qml` | 7 | 110 |
| `Launcher/LauncherCategory.qml` | 7 | 92 |
| `Core/OverlayWindow.qml` | 6 | 33 |
| `Widgets/IconButton.qml` | 5 | 33 |
| `Bar/BarClickArea.qml` | 5 | 40 |
| `Core/SafeProcess.qml` | 5 | 35 |
| `Core/FocusedOutput.qml` | 5 | 30 |
| `Widgets/ThemedTooltip.qml` | 5 | 42 |
| `Launcher/CarouselStrip.qml` | 5 | 76 |
| `Launcher/SettingsRow.qml` | 5 | 44 |

## Tangles — high fan-out

| File | Fan-out | LOC |
|------|--------:|----:|
| `Bar/StatusBar.qml` | 33 | 791 |
| `Launcher/AppLauncher.qml` | 14 | 629 |
| `Launcher/SettingsAudio.qml` | 9 | 157 |
| `Launcher/SettingsDisplay.qml` | 9 | 241 |
| `shell.qml` | 9 | 297 |
| `Bar/SysInfoSettingsPopup.qml` | 8 | 274 |
| `Launcher/CategoryBluetooth.qml` | 8 | 260 |
| `Launcher/CategoryWifi.qml` | 8 | 251 |
| `Launcher/SettingsPower.qml` | 8 | 210 |
| `Bar/ClockSettingsPopup.qml` | 7 | 124 |
| `Bar/SysWaveform.qml` | 7 | 128 |
| `Launcher/CategoryWallpaper.qml` | 7 | 355 |
| `Bar/CalendarPopup.qml` | 6 | 313 |
| `Bar/MediaPopupContent.qml` | 6 | 285 |
| `Bar/Weather.qml` | 6 | 196 |

## God modules — LOC ≥ 400

| File | LOC | Fan-in | Fan-out |
|------|----:|-------:|--------:|
| `Bar/StatusBar.qml` | 791 | 1 | 33 |
| `Config/Theme.qml` | 674 | 90 | 1 |
| `Launcher/AppLauncher.qml` | 629 | 0 | 14 |

## Cycles — strongly-connected components

_No cycles detected._

## Limitations

- QML references are not declarative `import` statements at the file level — components are referenced by capitalised identifier. The resolver uses imported `qs.<Module>` directories plus same-directory siblings to scope references, which can under-count cross-directory usage and over-count when two components share a name.
- `Theme.qml` is a singleton (`pragma Singleton`) so every reference is legitimate global access, not coupling in the traditional refactor-sense.
- LOC counts non-blank lines; comments not stripped.
- External Quickshell/QtQuick imports are not counted.
