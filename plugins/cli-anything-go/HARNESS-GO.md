# cli-anything Go Harness Methodology

**Single Source of Truth for Building Go CLI Harnesses**

This document is the normative reference for building Go CLI harnesses using the cli-anything-go plugin. Every command reads this document first. It defines the philosophy, design principles, project structure, implementation patterns, and phase-by-phase workflow for wrapping any GUI application with a compiled Go CLI binary.

This is the Go edition of HARNESS.md, adapted for Go tooling: Cobra command framework, bubbletea TUI, os/exec backend integration, and Go module publishing.

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [Go-Specific Standards](#go-specific-standards)
3. [Phase 0: Source Acquisition](#phase-0-source-acquisition)
4. [Phase 1: Codebase Analysis](#phase-1-codebase-analysis)
5. [Phase 2: CLI Architecture Design](#phase-2-cli-architecture-design)
6. [Phase 3: Implementation](#phase-3-implementation)
7. [Phase 4: Test Planning](#phase-4-test-planning)
8. [Phase 5: Test Implementation](#phase-5-test-implementation)
9. [Phase 6: Test Documentation](#phase-6-test-documentation)
10. [Phase 7: Go Module Publishing & Installation](#phase-7-go-module-publishing--installation)

---

## Design Principles

These 10 principles are non-negotiable. Every harness built with this methodology must satisfy all of them.

| #  | Principle                    | Go Implementation                                                                                   |
|----|------------------------------|-----------------------------------------------------------------------------------------------------|
| 1  | Use the Real Software        | `internal/backend/` shells out via `os/exec`                                                        |
| 2  | Hard Dependency              | `exec.LookPath()` on startup, clear error with install instructions                                 |
| 3  | Manipulate Native Format     | Parse XML/JSON/binary project files in `internal/core/`                                             |
| 4  | Leverage Existing CLI Tools  | Wrap `gimp -i -b`, `blender --background`, `melt`, etc.                                             |
| 5  | Verify Rendering Output      | Check magic bytes, file size, format — never trust exit codes alone                                 |
| 6  | E2E Tests Produce Real Artifacts | Real files in `t.TempDir()`, paths printed                                                      |
| 7  | Fail Loudly & Clearly        | Structured errors with codes, actionable messages, `%w` wrapping                                    |
| 8  | Idempotent Operations        | Same command twice = safe                                                                            |
| 9  | Introspection Commands       | `info`, `list`, `status` in every command group                                                     |
| 10 | Structured Output Mode       | `--output json\|yaml\|table\|plain` on every command                                               |

### Principle Details

**Principle 1 — Use the Real Software**
The harness is not a reimplementation. It drives the actual installed application. `internal/backend/` contains one or more files that shell out to the real binary via `os/exec`. There is no simulation, no mock rendering in production code.

**Principle 2 — Hard Dependency**
At subcommand invocation time, call a backend check helper that uses `exec.LookPath()` to verify the required binary is present. If missing, return a structured error with the exact install command for the user's platform. The harness must never silently degrade.

**Principle 3 — Manipulate Native Format**
Understand the software's native project file format. If it is XML (e.g., Shotcut `.mlt`), parse it with `encoding/xml`. If JSON, use `encoding/json`. If binary, write a custom reader. The `internal/core/` package owns these data models. Never shell out just to read metadata that can be parsed directly.

**Principle 4 — Leverage Existing CLI Tools**
Before implementing any feature from scratch, check whether the application already exposes a CLI interface. GIMP has `-i -b`. Blender has `--background`. Shotcut uses `melt`. FFmpeg is a universal fallback for media operations. Use what exists.

**Principle 5 — Verify Rendering Output**
After any render operation completes, verify the output independently of the process exit code. Check:
- File exists on disk
- File size is above a reasonable minimum
- Magic bytes match the expected format (PNG: `\x89PNG`, JPEG: `\xFF\xD8`, etc.)
- For video/audio: use `ffprobe` or equivalent to confirm decodable content
Exit code 0 does not mean the render succeeded.

**Principle 6 — E2E Tests Produce Real Artifacts**
End-to-end tests must produce real output files. Use `t.TempDir()` for isolation. Print the path of every produced artifact so CI logs are inspectable. Never mock the backend in E2E tests.

**Principle 7 — Fail Loudly & Clearly**
All errors must be:
- Wrapped with context using `fmt.Errorf("context: %w", err)`
- Surfaced with a structured error type that carries an error code
- Printed with an actionable message: what went wrong, why, and how to fix it
Never swallow errors with `_` in production paths.

**Principle 8 — Idempotent Operations**
Running the same command twice must be safe. Creating a project that already exists should update or return an informative message, not corrupt state. Exporting to the same path should overwrite predictably.

**Principle 9 — Introspection Commands**
Every command group must expose:
- `info` — show metadata about the current target (project, session, file)
- `list` — enumerate available items
- `status` — show current state and health of the integration

These commands must work even when the target is in a degraded state, so the user can always diagnose the situation.

**Principle 10 — Structured Output Mode**
Every command must support `--output json|yaml|table|plain`. The `internal/output/formatter.go` package handles all formatting. Commands must never directly `fmt.Print` their data — they call the formatter. The `--no-color` flag must be respected globally (honoring the `NO_COLOR` env var per the no-color.org spec).

---

## Go-Specific Standards

These standards apply to every Go harness. They are enforced in Phase 7.

### Linting & Vetting

- `go vet ./...` must produce zero warnings
- `golangci-lint run ./...` must produce zero issues
- Phase 7 requires both to be clean before the harness is considered complete
- Recommended `.golangci.yml` linters: `errcheck`, `govet`, `staticcheck`, `unused`, `gofmt`, `goimports`

### CGO Policy

- `CGO_ENABLED=0` by default
- All harnesses must compile to fully static binaries with no shared library dependencies
- This ensures the binary can be distributed and installed via `go install` without platform-specific setup
- Exception: only permitted if the target software's Go SDK explicitly requires CGO (document this clearly in the SOP)

### Context Propagation

- `context.Context` is threaded through all backend calls
- Every function in `internal/backend/` that calls `os/exec` must accept a `context.Context` as its first parameter
- Default timeouts:
  - Metadata queries (`info`, `list`, `status`): 30 seconds
  - Rendering operations: no timeout unless the user explicitly passes `--timeout <duration>`
- Use `context.WithTimeout` at the call site in cmd/, not inside the backend

### Package Boundary

- `internal/` enforces Go's visibility rules — nothing inside `internal/` is importable by external packages
- The public API surface is only the Cobra commands in `cmd/`
- All business logic, data models, backend calls, and output formatting live inside `internal/`
- This boundary is structural documentation: it says "this is a tool, not a library"

### Error Wrapping

- All errors use `fmt.Errorf("context: %w", err)` for debuggable error chains
- Define a `HarnessError` type in `internal/core/errors.go` with fields: `Code string`, `Message string`, `Cause error`
- Error codes are uppercase snake-case strings: `BACKEND_NOT_FOUND`, `PROJECT_PARSE_ERROR`, `RENDER_VERIFICATION_FAILED`
- The root command's `Execute()` prints the full error chain when `--verbose` is passed

### Module Path Convention

- Module path: `github.com/<user>/<software>-cli`
- Binary name: `<software>-cli` (e.g., `shotcut-cli`, `gimp-cli`, `blender-cli`)
- The `go install github.com/<user>/<software>-cli@latest` command must work after Phase 7

---

## Phase 0: Source Acquisition

**Goal:** Obtain and verify the target software's source code locally.

### Steps

1. **Handle GitHub URLs**
   If the user provides a GitHub URL (e.g., `https://github.com/mltframework/shotcut`), clone it locally:
   ```bash
   git clone <url> /tmp/<software>-source
   ```
   Use the cloned directory as the analysis target.

2. **Verify the path**
   Confirm the provided or cloned path exists and contains recognizable source code:
   - Look for build files: `CMakeLists.txt`, `Makefile`, `*.pro` (Qt), `pom.xml`, `build.gradle`, `setup.py`, `Cargo.toml`
   - Look for source directories: `src/`, `lib/`, `app/`
   - If neither is found, report clearly: "Path does not appear to contain source code"

3. **Derive the software name**
   The software name is the directory basename in lowercase, with spaces replaced by hyphens:
   - `/home/user/Shotcut` → `shotcut`
   - `/home/user/GIMP-2.10` → `gimp-2.10` (normalize to `gimp`)
   - Use this name as the module name, binary name, and SOP filename

4. **Record the source path**
   Store the resolved absolute path. All subsequent phases reference it as `$SOURCE_PATH`.

---

## Phase 1: Codebase Analysis

**Goal:** Deeply understand how the application works internally and what CLI surface it already exposes.

### Steps

1. **Identify the backend engine**
   Determine what rendering or processing library the application uses at its core:
   - Shotcut → MLT Framework (`melt` CLI)
   - GIMP → Script-Fu, GEGL, libgimp (`gimp -i -b`)
   - Blender → Python API (`blender --background --python`)
   - Inkscape → Inkscape CLI (`inkscape --export-...`)
   - Document this in the SOP as the "Backend Engine" entry

2. **Map GUI actions to API calls**
   For 10-20 representative user actions (File > Export, Filter > Blur, etc.), trace the code path from the GUI event handler to the underlying API call. This reveals:
   - Which functions are safe to call headlessly
   - Which operations require a display (Xvfb workaround if needed)
   - The parameter names and types used internally

3. **Identify data models**
   Find and document the native project file format:
   - XML (most common): identify the root element, key child elements, attribute names
   - JSON: identify the schema, required fields, version fields
   - Binary: document the header, magic bytes, record structure
   - SQLite: identify the tables and their schemas
   This becomes the struct definitions in `internal/core/`

4. **Find existing CLI tools**
   Search for:
   - Official CLI flags (`--help` output of the main binary)
   - Bundled helper binaries in the install directory
   - Scripting interfaces (Script-Fu console, Python console, macro system)
   - Plugin or extension APIs that can be driven non-interactively

5. **Catalog the command/undo system**
   Understand how the application tracks operations:
   - Does it have an explicit command pattern? (`QUndoStack`, etc.)
   - What operations are reversible?
   - What operations mutate files in-place vs. produce new output files?
   This informs which harness operations need to be explicitly idempotent

6. **Document the architecture**
   Write a concise architecture summary in the SOP document (created in Phase 2). Include:
   - Component diagram (ASCII or Mermaid)
   - Data flow for the 3 most common operations
   - Known headless limitations and workarounds

---

## Phase 2: CLI Architecture Design

**Goal:** Design the harness before writing any code.

### Steps

1. **Design command groups**
   Map the application's domains to Cobra command groups. Each group gets its own file in `cmd/`. Typical groups:
   - `project` — create, open, save, info, list, close
   - `export` — render, status, formats
   - `session` — start, stop, status, attach (for REPL mode)
   - `config` — get, set, reset, list
   - Application-specific groups: `timeline`, `layer`, `node`, `scene`, etc.

   Every group must implement Principle 9 (introspection commands): `info`, `list`, `status`.

2. **Plan the state model**
   Determine what state the harness needs to track between commands:
   - Current open project (path, format, version)
   - Active session (for REPL mode)
   - User preferences (output format, color, verbosity)
   - Last render result (for status queries)
   State is persisted in `~/.config/<software>-cli/state.json` (using `os.UserConfigDir()`).

3. **Plan output formats**
   For each command, define what structured data it returns:
   - `info` → object with name, path, format, metadata fields
   - `list` → array of objects
   - `export` → object with output path, duration, file size, format
   All output goes through `internal/output/formatter.go`.

4. **Create the software-specific SOP document**
   Create `<SOFTWARE>.md` in the harness root (e.g., `GIMP.md`, `SHOTCUT.md`). This document covers:
   - Software overview and version requirements
   - Backend engine and how to invoke it
   - Native file format specification
   - Command group design rationale
   - Known limitations and workarounds
   - Platform-specific notes (Linux/macOS/Windows path differences)
   - Installation instructions for the backend binary
   This SOP is what a new developer reads to understand this specific harness.

5. **Interaction model**
   The interaction model is always **Both**: the harness supports both:
   - **Subcommand CLI** — `<software>-cli project info --output json`
   - **Stateful REPL** — `<software>-cli repl` launches an interactive bubbletea session
   The REPL is not optional. It is a first-class interface.

---

## Phase 3: Implementation

**Goal:** Build the harness according to the design, following Go conventions and the package boundary strictly.

### Project Scaffold

```
<software>-cli/
├── cmd/
│   ├── root.go          # Root Cobra command, global flags, Execute()
│   ├── project.go       # project subcommand group
│   ├── export.go        # export subcommand group
│   ├── session.go       # session subcommand group
│   └── config.go        # config subcommand group
├── internal/
│   ├── core/
│   │   ├── errors.go    # HarnessError type, error codes
│   │   ├── project.go   # Project struct, parse/serialize
│   │   ├── session.go   # Session struct, state management
│   │   └── export.go    # ExportSpec, ExportResult types
│   ├── backend/
│   │   └── <software>.go  # os/exec integration, LookPath check
│   ├── output/
│   │   └── formatter.go   # json/yaml/table/plain formatter
│   └── repl/
│       ├── repl.go      # bubbletea Model, Init/Update/View
│       └── skin.go      # lipgloss skin
├── e2e/
│   ├── e2e_test.go      # E2E tests (//go:build e2e)
│   └── subprocess_test.go  # Subprocess/installed binary tests (//go:build e2e)
├── HARNESS-GO.md        # Copied from plugin at scaffold time
├── <SOFTWARE>.md        # Software-specific SOP
├── TEST.md              # Test plan (Part 1) + results (Part 2)
├── go.mod
├── go.sum
└── main.go
```

### Step-by-Step Implementation Order

**Step 1: Scaffold go.mod**
```
module github.com/<user>/<software>-cli

go 1.23

require (
    github.com/spf13/cobra v1.8.0
    github.com/charmbracelet/bubbletea v0.26.0
    github.com/charmbracelet/lipgloss v0.10.0
    gopkg.in/yaml.v3 v3.0.1
)
```
Run `go mod tidy` immediately after creating go.mod to populate go.sum.

**Step 2: Copy HARNESS-GO.md**
Copy this file from the plugin into the generated harness root. This ensures the harness is self-documenting and the reference travels with the code.

**Step 3: Implement internal/core/**
Define data types first. No I/O yet.
- `errors.go`: `HarnessError` struct with `Code`, `Message`, `Cause`. Implement `Error() string` and `Unwrap() error`.
- `project.go`: `Project` struct matching the native format. `ParseProject(path string) (*Project, error)`. `SaveProject(p *Project, path string) error`.
- `session.go`: `Session` struct for REPL state. `LoadSession() (*Session, error)`. `SaveSession(s *Session) error`.
- `export.go`: `ExportSpec` (input parameters) and `ExportResult` (output metadata including verified file size and format).

**Step 4: Implement internal/backend/<software>.go**
```go
// CheckBackend verifies the required binary is installed.
// Call this at the start of any subcommand that needs the backend.
// Do NOT use PersistentPreRunE — that breaks --help and --version.
func CheckBackend() error {
    path, err := exec.LookPath("<binary>")
    if err != nil {
        return &core.HarnessError{
            Code:    "BACKEND_NOT_FOUND",
            Message: "<binary> is not installed or not in PATH.\nInstall with: <platform-specific instructions>",
            Cause:   err,
        }
    }
    _ = path
    return nil
}
```

All functions that invoke the backend accept `ctx context.Context` as the first parameter:
```go
func Render(ctx context.Context, spec core.ExportSpec) (*core.ExportResult, error) {
    if err := CheckBackend(); err != nil {
        return nil, err
    }
    cmd := exec.CommandContext(ctx, "<binary>", buildArgs(spec)...)
    // ...
}
```

**Step 5: Implement internal/output/formatter.go**
```go
type Format string

const (
    FormatJSON  Format = "json"
    FormatYAML  Format = "yaml"
    FormatTable Format = "table"
    FormatPlain Format = "plain"
)

// Print writes data to w in the requested format.
// Respects --no-color / NO_COLOR env var for table/plain formats.
func Print(w io.Writer, data any, format Format, noColor bool) error
```

**Step 6: Build cmd/ Cobra commands**

`root.go` defines:
- Global persistent flags: `--output` (default: `plain`), `--project`, `--no-color`, `--verbose`, `--timeout`
- `Execute()` function called from `main.go`
- Version set via `-ldflags "-X cmd.Version=..."`

Each subcommand file registers its group command and subcommands. Example:
```go
// cmd/project.go
var projectCmd = &cobra.Command{
    Use:   "project",
    Short: "Manage projects",
}

var projectInfoCmd = &cobra.Command{
    Use:   "info <path>",
    Short: "Show project metadata",
    RunE: func(cmd *cobra.Command, args []string) error {
        if err := backend.CheckBackend(); err != nil {
            return err
        }
        // ...
    },
}
```

**Step 7: Implement internal/repl/**

`repl.go` implements the bubbletea `tea.Model` interface:
- `Init()` returns an initial command (e.g., check backend, load last session)
- `Update(msg tea.Msg)` handles key events, command output, and state transitions
- `View()` renders the current state using lipgloss styles from `skin.go`

The REPL is launched by `<software>-cli repl` or `<software>-cli session start --interactive`. It provides the same operations as the CLI subcommands but in a persistent, stateful, visually rich session.

`skin.go` defines the lipgloss skin: colors, borders, padding for the REPL panels. Colors must be disabled when `NO_COLOR` is set or `--no-color` is passed.

**Step 8: Wire main.go**
```go
package main

import "github.com/<user>/<software>-cli/cmd"

func main() {
    cmd.Execute()
}
```

---

## Phase 4: Test Planning

**Goal:** Write TEST.md Part 1 before writing any test code.

### TEST.md Structure

TEST.md has two parts:
- **Part 1** (written in this phase): comprehensive test plan
- **Part 2** (written in Phase 6): actual test results appended after running

### Test Categories

**Unit Tests** (`//go:build unit`)
- Location: alongside source files as `internal/core/*_test.go`, `internal/output/formatter_test.go`
- Scope: pure functions with no I/O, no external processes
- Coverage targets: all parse/serialize functions, all formatter paths, all error type methods
- Run with: `go test -v -tags unit ./...`

**E2E Tests** (`//go:build e2e`)
- Location: `e2e/e2e_test.go`
- Scope: full workflow tests using the real backend binary
- Requirements: backend binary must be installed; test skips with `t.Skip()` if not found
- Each test uses `t.TempDir()` for isolation
- Every produced artifact path is printed to `t.Log()` for CI inspection
- Output verification: check magic bytes, file size, and format for every rendered file
- Run with: `go test -v -tags e2e ./e2e/`

**Subprocess Tests** (`//go:build e2e`)
- Location: `e2e/subprocess_test.go`
- Scope: tests that run the compiled CLI binary as a subprocess
- Use `resolveCLI()` helper to find the binary
- Supports `CLI_ANYTHING_FORCE_INSTALLED=1` env var to skip local build check
- Run with: `CLI_ANYTHING_FORCE_INSTALLED=1 go test -v -tags e2e ./e2e/`

### Workflow Scenarios

Plan at least 3 realistic end-to-end workflow scenarios. Each scenario covers a complete user journey:
- Scenario 1: Create project → add content → export → verify output
- Scenario 2: Open existing project → inspect metadata → modify → re-export
- Scenario 3: REPL session → interactive operations → session persistence

Document each scenario in TEST.md with:
- Preconditions (what files/state must exist)
- Steps (exact CLI commands)
- Expected output (what the user should see)
- Verification (what to check on disk)

---

## Phase 5: Test Implementation

**Goal:** Write the tests defined in Phase 4.

### Unit Tests

Write `internal/core/*_test.go` files with `//go:build unit` build tag at the top:
```go
//go:build unit

package core_test

import (
    "testing"
    "github.com/<user>/<software>-cli/internal/core"
)

func TestParseProject(t *testing.T) {
    // Use table-driven tests for multiple input cases
    // Use testdata/ subdirectory for fixture files
}
```

### E2E Tests

```go
//go:build e2e

package e2e_test

import (
    "os/exec"
    "testing"
)

func TestExportWorkflow(t *testing.T) {
    // Skip if backend not available
    if _, err := exec.LookPath("<binary>"); err != nil {
        t.Skip("<binary> not installed, skipping E2E test")
    }

    dir := t.TempDir()
    // ... test body ...
    t.Logf("Produced artifact: %s", outputPath)

    // Verify output
    verifyMagicBytes(t, outputPath, expectedMagic)
    verifyMinFileSize(t, outputPath, minBytes)
}
```

### resolveCLI() Helper

```go
// resolveCLI returns the path to the CLI binary for subprocess tests.
// If CLI_ANYTHING_FORCE_INSTALLED=1, it requires the binary to be in PATH.
// Otherwise, it looks for a locally built binary in the module root.
func resolveCLI(t *testing.T) string {
    t.Helper()
    if os.Getenv("CLI_ANYTHING_FORCE_INSTALLED") == "1" {
        path, err := exec.LookPath("<software>-cli")
        if err != nil {
            t.Fatalf("<software>-cli not found in PATH (CLI_ANYTHING_FORCE_INSTALLED=1): %v", err)
        }
        return path
    }
    // Fall back to local build
    // ...
}
```

### Output Verification Helpers

```go
// verifyMagicBytes checks that the file at path starts with expectedMagic.
func verifyMagicBytes(t *testing.T, path string, expectedMagic []byte) {
    t.Helper()
    f, err := os.Open(path)
    if err != nil {
        t.Fatalf("cannot open output file %s: %v", path, err)
    }
    defer f.Close()
    got := make([]byte, len(expectedMagic))
    if _, err := io.ReadFull(f, got); err != nil {
        t.Fatalf("cannot read magic bytes from %s: %v", path, err)
    }
    if !bytes.Equal(got, expectedMagic) {
        t.Errorf("wrong magic bytes in %s: got %x, want %x", path, got, expectedMagic)
    }
}

// Common magic byte constants
var (
    MagicPNG  = []byte{0x89, 0x50, 0x4E, 0x47}
    MagicJPEG = []byte{0xFF, 0xD8, 0xFF}
    MagicPDF  = []byte{0x25, 0x50, 0x44, 0x46}
    MagicMKV  = []byte{0x1A, 0x45, 0xDF, 0xA3}
    MagicMP4  = []byte{0x00, 0x00, 0x00, 0x18, 0x66, 0x74, 0x79, 0x70} // ftyp box (offset 4)
)
```

---

## Phase 6: Test Documentation

**Goal:** Run all tests and append results to TEST.md Part 2.

### Steps

1. **Run unit tests**
   ```bash
   go test -v -tags unit ./... 2>&1 | tee unit-test-results.txt
   ```

2. **Run E2E tests** (requires backend installed)
   ```bash
   go test -v -tags e2e ./e2e/ 2>&1 | tee e2e-test-results.txt
   ```

3. **Run subprocess tests** (requires binary installed via `go install`)
   ```bash
   CLI_ANYTHING_FORCE_INSTALLED=1 go test -v -tags e2e ./e2e/ -run Subprocess 2>&1 | tee subprocess-test-results.txt
   ```

4. **Append to TEST.md**
   Always append results regardless of pass/fail. Partial failure is expected during development. The test results section documents:
   - Date and Go version (`go version`)
   - Backend binary version (`<binary> --version`)
   - Pass/fail counts for each test category
   - Full output from failing tests
   - List of produced artifacts (paths printed by `t.Log`)
   - Coverage gaps: tests that were planned but not yet implemented

### TEST.md Part 2 Template

```markdown
## Part 2: Test Results

**Run date:** YYYY-MM-DD
**Go version:** go1.XX.X
**Backend version:** <software> X.Y.Z
**Platform:** linux/amd64

### Unit Tests
- Total: N
- Passed: N
- Failed: N
- Skipped: N

<details>
<summary>Full output</summary>

\```
<paste go test -v output>
\```
</details>

### E2E Tests
...

### Subprocess Tests
...

### Produced Artifacts
- `/tmp/TestExportWorkflow1234/output.png` (12,345 bytes, valid PNG)
- ...

### Coverage Gaps
- [ ] TestSomethingNotYetImplemented — planned but skipped
```

---

## Phase 7: Go Module Publishing & Installation

**Goal:** Ensure the harness is a proper Go module that can be installed via `go install`.

### Steps

1. **Verify go.mod**
   - Module path follows convention: `github.com/<user>/<software>-cli`
   - Go version specifies minimum: `go 1.23` (or higher as appropriate)
   - All `require` entries have pinned versions (no `v0.0.0-00010101000000-000000000000`)

2. **Verify go build**
   ```bash
   CGO_ENABLED=0 go build -v ./...
   ```
   Must succeed with zero errors. The binary must be statically linked.

3. **Verify go vet**
   ```bash
   go vet ./...
   ```
   Must produce zero output (zero warnings).

4. **Run golangci-lint**
   ```bash
   golangci-lint run ./...
   ```
   Must produce zero issues. If golangci-lint is not installed:
   ```bash
   go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
   ```
   Address every linter warning. Do not suppress with `//nolint` unless the suppression is documented with a reason.

5. **Test go install**
   ```bash
   go install .
   ```
   Verify the binary appears in `$GOPATH/bin` (or `$(go env GOPATH)/bin`):
   ```bash
   ls -la $(go env GOPATH)/bin/<software>-cli
   ```

6. **Verify CLI is in PATH**
   ```bash
   which <software>-cli
   <software>-cli --version
   <software>-cli --help
   ```
   All three must succeed.

7. **Run subprocess tests with installed binary**
   ```bash
   CLI_ANYTHING_FORCE_INSTALLED=1 go test -v -tags e2e ./e2e/ -run Subprocess
   ```
   These tests exercise the installed binary, not a locally built one. They are the final verification that the published module works correctly.

8. **Verify go mod tidy**
   ```bash
   go mod tidy
   git diff go.mod go.sum
   ```
   Must produce no diff. If there is a diff, apply it and re-run Phase 7 checks.

### Definition of Done for Phase 7

A harness passes Phase 7 when all of the following are true:
- [ ] `CGO_ENABLED=0 go build ./...` succeeds
- [ ] `go vet ./...` produces zero output
- [ ] `golangci-lint run ./...` produces zero issues
- [ ] `go install .` places the binary in `$GOPATH/bin`
- [ ] `<software>-cli --version` prints the version
- [ ] `CLI_ANYTHING_FORCE_INSTALLED=1 go test -v -tags e2e ./e2e/` passes
- [ ] `go mod tidy` leaves no diff in go.mod or go.sum
- [ ] TEST.md Part 2 has been written with actual results

---

*End of HARNESS-GO.md Part 1 — Methodology Overview & Phases*

*Part 2 covers: Project Structure Details, Cobra Patterns, bubbletea REPL Architecture, and Output Formatting.*
*Part 3 covers: Rendering Verification Patterns, Media-Specific Guidance, and Packaging.*

---

## Part 2: Project Structure, CLI Framework, and REPL

---

## Generated Project Structure

Every harness generated by the cli-anything-go plugin follows this directory layout. The tree below is the canonical reference. When in doubt about where a file belongs, consult this tree.

```
<software>/
└── agent-harness/
    ├── HARNESS-GO.md               # Go methodology spec (copied from plugin)
    ├── <SOFTWARE>.md               # Software-specific SOP
    ├── README.md                   # Installation and usage guide
    ├── go.mod                      # module github.com/<user>/<software>-cli
    ├── go.sum
    ├── main.go                     # Entry point
    ├── cmd/                        # Cobra command definitions
    │   ├── root.go                 # Root command + global flags + REPL default
    │   ├── project.go              # project new/open/save/close/info
    │   ├── export.go               # render/export pipeline
    │   ├── session.go              # undo/redo/history
    │   └── ...                     # Domain-specific command groups
    ├── internal/                    # Non-public implementation
    │   ├── core/                    # Core business logic
    │   │   ├── project.go
    │   │   ├── project_test.go     # Unit tests alongside code
    │   │   ├── session.go
    │   │   ├── session_test.go
    │   │   ├── export.go
    │   │   ├── export_test.go
    │   │   └── ...
    │   ├── backend/                 # Backend software integration
    │   │   ├── <software>.go
    │   │   └── <software>_test.go
    │   ├── output/                  # Output formatting
    │   │   ├── formatter.go        # json | yaml | table | plain
    │   │   └── formatter_test.go
    │   └── repl/                    # REPL implementation
    │       ├── repl.go             # bubbletea model
    │       └── skin.go             # lipgloss styling, branded banner
    ├── testdata/                    # Embedded test fixtures (//go:embed)
    │   └── ...
    ├── e2e/                        # Integration & subprocess tests
    │   ├── e2e_test.go             # E2E tests (//go:build e2e)
    │   └── subprocess_test.go      # Installed binary tests (//go:build e2e)
    └── TEST.md                     # Test plan + results (covers all tiers)
```

### Go-Idiomatic Rationale

**`internal/` keeps core logic unexported.**
The `internal/` directory enforces Go's package visibility rules at the module boundary. No external package can import `internal/core`, `internal/backend`, `internal/output`, or `internal/repl`. This is intentional: the harness is a tool, not a library. All public surface area is the compiled binary and its CLI flags.

**Unit test files alongside source (`*_test.go` next to `*.go`).**
Go convention places unit tests in the same directory as the code under test. `internal/core/project_test.go` lives beside `internal/core/project.go`. This makes it easy to see at a glance what has test coverage and what does not. Tests in `internal/` use build tag `//go:build unit`.

**E2E and subprocess tests in `e2e/` (outside `internal/`).**
The `e2e/` directory sits at the module root, outside `internal/`, so it tests the harness through its public interface — the Cobra commands and the compiled binary. Tests here use build tag `//go:build e2e`. This mirrors how pytest separates unit and integration tests using markers, with the difference that Go's build tags make tier separation structural rather than decorative.

**`testdata/` with `//go:embed` for fixtures.**
Go's embed package allows test fixture files to be baked into the test binary. Each package that needs fixtures embeds its own `testdata/` subdirectory. A shared fixtures package can re-export the embedded FS if needed across packages.

```go
import "embed"

//go:embed testdata/*
var testFixtures embed.FS

func loadFixture(name string) ([]byte, error) {
    return testFixtures.ReadFile("testdata/" + name)
}
```

**Build tags replace pytest markers.**
The Python harness methodology uses `@pytest.mark.unit` and `@pytest.mark.e2e` to categorize tests. Go uses build tags at the top of each test file. The equivalent mapping is:

| Python marker       | Go build tag        | Run command                              |
|---------------------|---------------------|------------------------------------------|
| `@pytest.mark.unit` | `//go:build unit`   | `go test -v -tags unit ./...`            |
| `@pytest.mark.e2e`  | `//go:build e2e`    | `go test -v -tags e2e ./e2e/`            |
| (no marker)         | `//go:build unit`   | same as unit                             |

---

## CLI Framework

### Root Command Design

The root command defines the binary name and global behavior. The binary is named `<software>-cli` (e.g., `gimp-cli`, `blender-cli`, `shotcut-cli`).

**Invoking with no subcommand enters the bubbletea REPL.** This is the default behavior. `<software>-cli` with no arguments launches the interactive session. `<software>-cli <subcommand>` executes the subcommand non-interactively and exits.

**Global flags (defined on root, inherited by all subcommands):**

| Flag          | Type             | Default  | Description                                          |
|---------------|------------------|----------|------------------------------------------------------|
| `--output`    | string           | `plain`  | Output format: `json`, `yaml`, `table`, or `plain`   |
| `--project`   | string           | `""`     | Path to the project file for non-REPL invocations    |
| `--no-color`  | bool             | `false`  | Disable color output (also honored via `NO_COLOR` env) |
| `--verbose`   | bool             | `false`  | Enable verbose logging to stderr                     |
| `--timeout`   | duration         | `30s`    | Timeout for metadata queries; rendering has no default timeout |
| `--version`   | bool             | `false`  | Print version and exit (set via ldflags at build time) |

### Backend Dependency Check

The backend check is performed by a helper function called from individual subcommands, **not** from `PersistentPreRunE`. This is a deliberate choice: using `PersistentPreRunE` would run the backend check before `--help` and `--version` are processed, causing those flags to fail with a confusing error if the backend binary is not installed.

Correct pattern:
```go
var projectInfoCmd = &cobra.Command{
    Use:   "info <path>",
    Short: "Show project metadata",
    RunE: func(cmd *cobra.Command, args []string) error {
        // Check backend at the start of RunE, not in PersistentPreRunE
        if err := backend.CheckBackend(); err != nil {
            return err
        }
        // ... rest of command
    },
}
```

Every subcommand that shells out to the backend must call `backend.CheckBackend()` as its first action in `RunE`. Commands that only read or parse project files locally (without invoking the backend process) may skip this check.

### Command Group Pattern

Commands are organized into groups, each in its own file in `cmd/`:

| Group      | File            | Subcommands                                    |
|------------|-----------------|------------------------------------------------|
| `project`  | `project.go`    | `new`, `open`, `save`, `close`, `info`, `list` |
| `export`   | `export.go`     | `render`, `status`, `formats`, `verify`        |
| `session`  | `session.go`    | `undo`, `redo`, `history`, `info`              |
| `config`   | `config.go`     | `get`, `set`, `reset`, `list`                  |
| (domain)   | `<domain>.go`   | Software-specific operations                   |

Every group implements Principle 9: `info`, `list`, and `status` subcommands.

### Output Formatter Design

All command output goes through `internal/output/formatter.go`. Commands never call `fmt.Print` directly on their data. The formatter handles four modes:

**`plain`** — Human-readable, colored with lipgloss. This is the default. Suitable for interactive terminal use. Key-value pairs are aligned, lists are bulleted, and errors are styled in red with hints.

**`table`** — Box-drawing aligned tables rendered with lipgloss and the Charm table component. Column headers are bold. Rows alternate in subtle background colors (disabled when `--no-color` is set).

**`json`** — Machine-parseable, one JSON object per result. Arrays are encoded as a JSON array. Suitable for piping to `jq`. Errors are encoded as `{"error": "message", "code": "ERROR_CODE"}`.

**`yaml`** — For config-heavy workflows where YAML is more readable than JSON. Uses `gopkg.in/yaml.v3` marshaling.

**Migration note — `--json` vs `--output json`:**
The Python harness used `--json` as a boolean flag to request JSON output. The Go harness uses `--output json|yaml|table|plain`. Agents and scripts that previously passed `--json` must be updated to pass `--output json`.

### Error Handling

**Structured errors in `--output json` mode:**
```json
{"error": "project file not found", "code": "NOT_FOUND", "path": "/tmp/missing.xcf"}
```

**Plain mode errors** are styled with lipgloss red and include an actionable hint:
```
Error: project file not found
  Path: /tmp/missing.xcf
  Hint: Run 'gimp-cli project new --path /tmp/portrait.xcf' to create a new project.
```

**Internal error wrapping** follows the standard Go pattern throughout:
```go
fmt.Errorf("parse project: %w", err)
fmt.Errorf("render export: invoke backend: %w", err)
```

This produces debuggable error chains. When `--verbose` is passed, the root command prints the full chain.

**Exit codes:**

| Code | Meaning                         | Notes                                              |
|------|---------------------------------|----------------------------------------------------|
| `0`  | Success                         |                                                    |
| `1`  | User error                      | Bad flags, file not found, invalid arguments       |
| `10` | Backend not found               | Backend binary missing from PATH                   |
| `11` | Backend failure                 | Backend process exited non-zero or produced bad output |

Exit code `2` is reserved for shell misuse (e.g., `bash` itself uses it for syntax errors) and is intentionally avoided.

---

## REPL Implementation

### bubbletea Model Pattern

The REPL is implemented as a bubbletea `tea.Model` in `internal/repl/repl.go`. The model follows the standard Elm architecture:

```
Init() → tea.Cmd         — initial setup: banner display, backend check, session load
Update(msg) → (Model, tea.Cmd) — event handling: keypresses, command results, errors
View() → string          — render: compose all panels using lipgloss
```

The REPL is launched by the root command when no subcommand is given, or explicitly by `<software>-cli repl`.

### Input Parsing and Cobra Dispatch

User input lines in the REPL are parsed and dispatched to the Cobra command tree. This gives the REPL the same command surface as the CLI without duplicating command logic:

1. The user types a command string (e.g., `project info --output json`)
2. The REPL splits the input into args and prepends the binary name
3. The Cobra root command is re-executed with those args, capturing stdout/stderr
4. The output is displayed in the REPL's output panel

This design means every CLI subcommand works identically inside and outside the REPL.

### Tab Completion

Tab completion is implemented by walking the Cobra command tree at keypress time:

1. On `Tab`, extract the partial token from the current input
2. Walk `rootCmd.Commands()` recursively to collect command and flag names
3. Filter completions by the partial token prefix
4. If one completion matches, fill it in; if multiple match, display a completion list below the input

The completion list is styled with a dimmed lipgloss color and disappears when input changes.

### Command History

Command history is managed by the bubbletea text input component's built-in history support. The Up/Down arrow keys cycle through previously entered commands. History is kept in memory for the duration of the REPL session and is not persisted to disk.

### Session State

The REPL maintains in-memory session state that persists between commands within a single REPL session:

**Project reference.** Once a project is opened with `project open <path>`, the REPL holds a reference to it. Subsequent commands that operate on a project (e.g., `export render`) do not require `--project` to be specified again. The current project path is displayed in the styled prompt.

**Undo/redo stack.** Every operation that modifies the project appends an entry to an in-memory undo stack. `session undo` and `session redo` traverse this stack. The stack is not persisted across REPL restarts.

**`session info` output.** The `session info` command prints current session state as structured output (respecting `--output`), including: current project path, unsaved changes flag, undo stack depth, and session start time.

**Session state is ephemeral.** All session state — open project reference, undo stack, and in-memory changes — is lost when the REPL exits. To persist changes, the user must explicitly save the project before exiting (`project save` or `Ctrl+S`).

### skin.go Requirements

`internal/repl/skin.go` defines all visual styling for the REPL. It must satisfy the following requirements:

**Branded banner.** The REPL displays a banner on startup using the cli-anything logo mark `◆`. Example:
```
◆ gimp-cli  v0.1.0   GIMP 2.10.36
Type 'help' for available commands. Ctrl+C to exit.
```

**Software-specific accent colors.** Each harness has a designated accent color applied to the banner, prompt, and highlights:

| Software      | Accent Color   | Hex       |
|---------------|----------------|-----------|
| gimp          | Warm orange    | `#E67E22` |
| blender       | Deep orange    | `#E44D26` |
| inkscape      | Bright blue    | `#0082C8` |
| audacity      | Navy blue      | `#003366` |
| libreoffice   | Green          | `#1D7E2A` |
| obs_studio    | Purple         | `#7B2D8B` |
| kdenlive      | Slate blue     | `#3D6B9A` |
| shotcut       | Teal green     | `#2E9E8A` |

For software not in this table, derive an accent color from the application's official brand colors.

**Styled prompt.** The prompt shows the software name and current project state:
```
gimp [portrait.xcf*] >
```
The `*` suffix indicates unsaved changes. When no project is open, the prompt shows only the software name:
```
gimp >
```

**Color helpers.** `skin.go` exports the following lipgloss-based helpers used throughout the REPL and output formatter:

```go
func Success(msg string) string  // green
func Error(msg string) string    // red
func Warning(msg string) string  // yellow
func Info(msg string) string     // accent color (software-specific)
func Hint(msg string) string     // dimmed/muted
```

**Table renderer.** The `skin.go` package provides a `RenderTable(headers []string, rows [][]string) string` function that produces a lipgloss-styled table using the Charm table component. Column widths are calculated from content.

**`NO_COLOR` compliance.** All styling must be disabled when either:
- The `NO_COLOR` environment variable is set (to any value, per the no-color.org spec)
- The `--no-color` flag was passed on the command line

When color is disabled, `Success()`, `Error()`, `Warning()`, `Info()`, and `Hint()` return their input strings unchanged.

---

*End of HARNESS-GO.md Part 2 — Project Structure, CLI Framework, and REPL*

---

# Part 3 — Testing, Rendering, Packaging

---

## Testing Strategy

The harness uses a three-tier testing model. Each tier has a distinct build tag, distinct scope, and distinct failure contract.

---

### Tier 1: Unit Tests

**Location:** Alongside source files, e.g. `internal/core/project_test.go`

**Build tag:**
```go
//go:build unit
```

**Run:**
```bash
go test -tags unit ./...
```

**Contract:**
- Synthetic data only — no external processes, no network, no GUI software required
- Tests every exported and unexported function in `internal/core/` in isolation
- Fixtures loaded via `//go:embed testdata/...`
- Table-driven tests with Testify assertions (`assert`, `require`)
- Fast: the full suite must complete in under 30 seconds on a typical developer machine

**Table-driven test pattern:**
```go
//go:build unit

package core_test

import (
    "testing"

    "github.com/<user>/<software>-cli/internal/core"
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
)

func TestParseProject(t *testing.T) {
    cases := []struct {
        name    string
        input   string
        want    *core.Project
        wantErr bool
    }{
        {
            name:  "valid project",
            input: "testdata/valid.xcf",
            want:  &core.Project{Name: "valid", Layers: 3},
        },
        {
            name:    "missing file",
            input:   "testdata/nonexistent.xcf",
            wantErr: true,
        },
    }

    for _, tc := range cases {
        t.Run(tc.name, func(t *testing.T) {
            got, err := core.ParseProject(tc.input)
            if tc.wantErr {
                require.Error(t, err)
                return
            }
            require.NoError(t, err)
            assert.Equal(t, tc.want.Name, got.Name)
            assert.Equal(t, tc.want.Layers, got.Layers)
        })
    }
}
```

---

### Tier 2: E2E Tests

**Location:** `e2e/e2e_test.go`

**Build tag:**
```go
//go:build e2e
```

**Run:**
```bash
go test -tags e2e ./e2e/
```

**Contract:**
- Requires actual GUI software installed — hard failure if missing, no graceful degradation
- Creates real project files, invokes real backends, verifies output
- Real artifacts are produced; their paths are printed with `t.Logf` for manual inspection after a run
- Slow: individual tests may take tens of seconds; no timeout shorter than 5 minutes

**Missing software check (fail loudly):**
```go
func requireSoftware(t *testing.T, name string) string {
    t.Helper()
    path, err := exec.LookPath(name)
    if err != nil {
        t.Fatalf("required software not found in PATH: %s — install it before running e2e tests", name)
    }
    return path
}
```

**Output verification — beyond magic bytes and file size:**

| Media type | Checks |
|------------|--------|
| Video | Magic bytes, file size > threshold, probe specific frames (exclude letterboxing pixels), verify resolution and codec via `ffprobe` |
| Audio | Magic bytes, file size > threshold, RMS levels non-zero, verify sample rate and channel count |
| Images | Magic bytes, verify dimensions, color depth, sample pixel regions to confirm content is not blank |
| Documents | Magic bytes, page count matches expected, text extraction contains known strings, embedded resources present |

---

### Tier 3: Subprocess Tests

**Location:** `e2e/subprocess_test.go`

**Build tag:**
```go
//go:build e2e
```

**Contract:**
- Tests the compiled binary via `os/exec` — not library code
- Exercises flag parsing, exit codes, stdout/stderr formatting, and signal handling
- Used in Phase 7 to validate that the installed binary behaves correctly end-to-end

**Binary resolution helper:**
```go
func resolveCLI(t *testing.T, name string) string {
    t.Helper()
    if path, err := exec.LookPath(name); err == nil {
        t.Logf("[resolveCLI] Using installed command: %s", path)
        return path
    }
    if os.Getenv("CLI_ANYTHING_FORCE_INSTALLED") == "1" {
        t.Fatalf("%s not found in PATH and CLI_ANYTHING_FORCE_INSTALLED=1", name)
    }
    // Fallback: go build into temp dir
    tmp := t.TempDir()
    bin := filepath.Join(tmp, name)
    cmd := exec.Command("go", "build", "-o", bin, ".")
    if out, err := cmd.CombinedOutput(); err != nil {
        t.Fatalf("failed to build %s: %v\n%s", name, err, out)
    }
    t.Logf("[resolveCLI] Falling back to built binary: %s", bin)
    return bin
}
```

**`CLI_ANYTHING_FORCE_INSTALLED` environment variable:**

When set to `1`, `resolveCLI` will not fall back to building from source. If the binary is not found in `PATH`, the test fails immediately. This is used in Phase 7 to validate that `go install` placed the binary correctly.

```bash
CLI_ANYTHING_FORCE_INSTALLED=1 go test -tags e2e ./e2e/ -v
```

---

### TEST.md Structure

The agent writes a `TEST.md` file in the project root. It has two parts, written in separate phases:

**Part 1 (Phase 4):** Test inventory and plan — lists every test case by tier, input, and expected outcome before any tests are run.

**Part 2 (Phase 6):** Full `go test -v` output appended with pass/fail results. This part is **always appended regardless of pass/fail status** — a failing run must still be recorded. The agent must never omit Part 2 because some tests failed; the failures are the information.

---

## Rendering & Backend Guidance

### The Rendering Gap

The #2 pitfall when wrapping GUI software is the **rendering gap**: the application applies filters and effects through an internal pipeline that differs from what its CLI or scripting interface exposes. An image edited in GIMP may look different when re-exported via `gimp --batch` if the Script-Fu bridge does not reproduce the same compositing order.

**Priority order for rendering:**

1. **Native engine** — Use the application's own rendering pipeline invoked headlessly. Examples: `gimp --no-interface --batch`, `blender --background --python`, `inkscape --export-type=pdf`. This is always the preferred path because it guarantees identical output to what the GUI would produce.

2. **Translated filtergraph** — Map the application's filter chain to the backend CLI's equivalent representation. Example: translate Shotcut's MLT XML filter list into an `ffmpeg` filtergraph. Use this only when the native engine cannot be invoked headlessly.

3. **Script/macro** — Generate a script in the application's own scripting language (Script-Fu, Python-Fu, Blender Python API) and execute it headlessly. Use this when neither of the above is feasible.

**Never reimplement rendering logic** — do not attempt to replicate blur, color grading, or compositing math in Go. The application's implementation is the ground truth.

---

### Filter Translation Pitfalls

When translating from an application's filter chain to a backend CLI equivalent, four pitfalls account for the majority of rendering discrepancies:

**Duplicate filter types.** Many applications ship multiple implementations of conceptually similar effects (e.g., GIMP has both "Gaussian Blur" and "Blur" under different menu paths). Map to the specific implementation the application uses, not the generic name.

**Ordering constraints.** Filter order matters and must be preserved exactly. A sharpen applied before a color correction produces different output than the reverse. Preserve the application's chain order in the translated representation.

**Parameter space differences.** A "brightness" slider ranging 0–100 in the application UI may not map linearly to a backend parameter ranging −1.0 to 1.0. Document the mapping formula in the translator and test it at the boundary values (0, 50, 100).

**Unmappable effects.** Some effects have no CLI equivalent. When an effect cannot be translated, fail loudly with a descriptive error message rather than silently dropping it. Example:
```
error: filter "Ripple Distortion" has no ffmpeg equivalent — use native GIMP rendering for this project
```

---

### Timecode Precision

Frame-to-timecode conversion is a frequent source of off-by-one errors in video tooling.

**Use `math.Round()`, not `int()` truncation:**
```go
// Correct
frames := int(math.Round(seconds * fps))

// Wrong — accumulates truncation error
frames := int(seconds * fps)
```

**Prefer integer arithmetic for timecode display** to avoid float accumulation across long durations:
```go
totalFrames := durationMs * fps / 1000  // integer division
hours   := totalFrames / (fps * 3600)
minutes := (totalFrames % (fps * 3600)) / (fps * 60)
seconds := (totalFrames % (fps * 60)) / fps
frames  := totalFrames % fps
```

**E2E test tolerance:** Allow ±1 frame tolerance when verifying timecodes in E2E tests, because backend renderers (ffmpeg, MLT) may differ by one frame at clip boundaries due to rounding in their own pipelines.

---

### Output Verification Methodology

Magic bytes and file size are necessary but not sufficient. A corrupt or blank output file can pass both checks. Apply the following additional verifications by media type:

**Video:**
- Probe specific frames using `ffprobe -select_streams v:0 -show_frames`
- Exclude letterboxing pixels when sampling (sample from the center region, not edges)
- Verify resolution and codec match the expected output profile
- Verify duration is within ±0.5 seconds of expected

**Audio:**
- Check RMS levels are non-zero (a silent output file indicates a rendering failure)
- Verify sample rate and channel count match the project settings
- For multi-track exports, verify each track has non-zero content

**Images:**
- Verify pixel dimensions exactly match the export settings
- Verify color depth (8-bit, 16-bit, 32-bit float) matches the project
- Sample pixel regions: check that the center region is not uniform black or uniform white (indicates a blank render)
- For layer exports, verify the correct layers are present/absent

**Documents:**
- Verify page count matches expected
- Run text extraction and assert that known strings from the source content are present
- Verify embedded resources (fonts, images) are present and not broken

---

## Go Module & Installation

### go.mod Template

```go
module github.com/<user>/<software>-cli

go 1.23

require (
    github.com/spf13/cobra v1.8.x
    github.com/charmbracelet/bubbletea v1.x
    github.com/charmbracelet/lipgloss v1.x
    github.com/stretchr/testify v1.9.x
    gopkg.in/yaml.v3 v3.x
)
```

**Go version policy:** Use the current or previous stable Go release at time of generation. Do not pin to a version older than two releases back.

---

### main.go Template

```go
package main

import "github.com/<user>/<software>-cli/cmd"

func main() {
    cmd.Execute()
}
```

`main.go` contains only the entry point. All command wiring lives in `cmd/root.go` and the other `cmd/` files. This keeps `main.go` trivially small and ensures the library surface (`cmd.Execute`) is importable in tests.

---

### Binary Name

The compiled binary is named `<software>-cli` (e.g., `gimp-cli`, `blender-cli`, `shotcut-cli`). The module path follows the same pattern: `github.com/<user>/<software>-cli`.

**Development mode:** Run from the agent harness directory without installing:
```bash
go run . <command> [flags]
```

---

### Installation & Verification

```bash
go install github.com/<user>/<software>-cli@latest
which <software>-cli
<software>-cli --version
CLI_ANYTHING_FORCE_INSTALLED=1 go test -tags e2e ./e2e/ -v
```

The `--version` flag must print a string containing the module path or a recognisable `cli-anything-go` signature so that the `/cli-anything-go:list` command can identify it.

---

### Phase 7 Checklist

Before marking a project complete, verify all of the following:

1. `go build .` succeeds with no errors or warnings
2. `go vet ./...` is clean
3. `golangci-lint run ./...` is clean
4. `go install .` places the binary in `$GOPATH/bin` (verify with `which <software>-cli`)
5. Binary runs: `<software>-cli --version` prints the expected version string
6. Subprocess tests pass with `CLI_ANYTHING_FORCE_INSTALLED=1 go test -tags e2e ./e2e/ -v`
7. `go mod tidy` leaves no diff (run it and verify `git diff go.mod go.sum` is empty)

---

### CLI Discovery for `/cli-anything-go:list`

The `/cli-anything-go:list` command discovers installed CLIs by:

1. Scanning `$GOPATH/bin` and `$HOME/go/bin` for binaries matching the `*-cli` pattern
2. Invoking each candidate with `--version`
3. Retaining candidates whose `--version` output contains a `cli-anything-go` signature string

The signature string is embedded in the `--version` output by the root command template. Agents must not remove or alter this string.

---

*End of HARNESS-GO.md Part 3 — Testing, Rendering, Packaging*

*HARNESS-GO.md is complete.*
