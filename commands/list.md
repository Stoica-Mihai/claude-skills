# cli-anything-go:list Command

Discover installed and generated Go CLI harnesses on the current system.

## CRITICAL: Read HARNESS-GO.md First

**Before doing anything else, you MUST read `./HARNESS-GO.md`.** It defines the expected directory layout and binary naming conventions used to locate harnesses.

## Usage

```bash
/cli-anything-go:list [--path <directory>] [--depth <n>] [--json]
```

## Options

- `--path <directory>` - Directory to search for generated harnesses (default: current directory)
- `--depth <n>` - Maximum recursion depth for directory scanning (default: unlimited). Use `0` for the current directory only, `1` for one level deep, etc.
- `--json` - Output in JSON format for machine parsing

## What This Command Does

Displays all cli-anything-go harnesses available on the system, combining installed binaries and locally generated (not yet installed) harnesses.

### 1. Installed Binaries

Scans `$GOPATH/bin` and `$HOME/go/bin` for binaries matching the `*-cli` naming pattern:

- Lists each binary found
- Invokes `<binary> --version` to confirm it is a cli-anything-go harness (look for the cli-anything-go signature in the version output)
- Extracts: binary name, version string, full path
- Status: `installed`

If `$GOPATH` is not set, default to `$HOME/go`.

### 2. Generated Harnesses

Scans for locally generated harnesses that have not yet been installed:

- Search pattern: find `agent-harness/go.mod` files under the search path
- For each match, read `go.mod` to extract the module path and derive the software name
- Read `go.mod` for the module version if present, otherwise mark version as `(local)`
- Status: `generated`

To respect the `--depth` option, build glob patterns for each depth level from 0 to `--depth`. Use recursive `**` glob when depth is unlimited.

Example depth patterns (suffix: `agent-harness/go.mod`):
- depth 0: `<base>/agent-harness/go.mod`
- depth 1: `<base>/*/agent-harness/go.mod`
- depth 2: `<base>/*/agent-harness/go.mod`, `<base>/*/*/agent-harness/go.mod`
- unlimited: `<base>/**/agent-harness/go.mod`

### 3. Merge Results

- Deduplicate by software name (binary name or derived from module path)
- If a harness appears in both installed binaries and generated directories: show status `installed` with both the binary path and the source path
- Generated-only entries show status `generated` with source path

## Output Formats

### Table Format (default)

```
cli-anything-go Harnesses (found 5)

Name          Status       Version    Path
────────────────────────────────────────────────────────────────
gimp-cli      installed    v1.2.0     /home/user/go/bin/gimp-cli
blender-cli   installed    v0.9.1     /home/user/go/bin/blender-cli
inkscape-cli  generated    (local)    ./inkscape/agent-harness
audacity-cli  generated    (local)    ./audacity/agent-harness
shotcut-cli   installed    v1.0.0     /home/user/go/bin/shotcut-cli
```

### JSON Format (--json)

```json
{
  "harnesses": [
    {
      "name": "gimp-cli",
      "status": "installed",
      "version": "v1.2.0",
      "binary": "/home/user/go/bin/gimp-cli",
      "source": "./gimp/agent-harness"
    },
    {
      "name": "inkscape-cli",
      "status": "generated",
      "version": "(local)",
      "binary": null,
      "source": "./inkscape/agent-harness"
    }
  ],
  "total": 2,
  "installed": 1,
  "generated_only": 1
}
```

## Implementation Steps

When this command is invoked, the agent should:

1. **Parse arguments**
   - Extract `--path` value (default: `.`)
   - Extract `--depth` value (default: `nil` for unlimited)
   - Extract `--json` flag (default: false)

2. **Validate path**
   - If `--path` is specified and the directory does not exist, show an error and stop

3. **Scan installed binaries**
   - Determine `$GOPATH` (fall back to `$HOME/go` if unset)
   - List files in `$GOPATH/bin` matching `*-cli`
   - For each binary, run `<binary> --version` and check for a cli-anything-go signature
   - Collect name, version, binary path

4. **Scan generated harnesses**
   - Build glob patterns based on `--depth`
   - For each `agent-harness/go.mod` found:
     - Read `go.mod` to extract module path
     - Derive software name from module path (last path segment, strip `-cli` suffix if present)
     - Record source path (the `agent-harness/` directory)
   - Calculate paths relative to the current working directory for readability

5. **Merge results**
   - Key by software name
   - Prefer installed binary data when both exist; retain source path from generated entry

6. **Format and print**
   - If `--json`: emit JSON to stdout
   - Otherwise: print aligned table with summary line

## Error Handling

| Scenario | Action |
|---|---|
| No harnesses found | Print: "No cli-anything-go harnesses found" |
| Invalid `--path` | Print error: "Path not found: <path>" and exit |
| Permission denied on a directory | Skip the directory, continue scanning, print a warning |
| Binary found but `--version` fails | Include in results with version `(unknown)` |
| `go.mod` unreadable | Skip the entry, print a warning |

## Examples

```bash
# List all harnesses (installed + generated, unlimited depth)
/cli-anything-go:list

# Limit scan to 2 directory levels deep
/cli-anything-go:list --depth 2

# Scan current directory only (no recursion)
/cli-anything-go:list --depth 0

# JSON output
/cli-anything-go:list --json

# Scan a specific directory
/cli-anything-go:list --path /projects/go-clis --depth 3

# Combined options
/cli-anything-go:list --path ./output --depth 2 --json
```

## Notes

- Binary names follow the `<software>-cli` convention defined in HARNESS-GO.md
- The `--version` check distinguishes cli-anything-go binaries from unrelated `*-cli` tools in `$GOPATH/bin`
- Default depth is unlimited; generated harnesses are typically 2–4 levels below the search root
- Relative paths are preferred over absolute paths in table output for readability
- The command works with no external dependencies — only filesystem access and subprocess invocation of discovered binaries
