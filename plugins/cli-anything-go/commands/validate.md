# cli-anything-go:validate Command

Validate a Go CLI harness against HARNESS-GO.md standards and best practices.

## CRITICAL: Read HARNESS-GO.md First

**Before doing anything else, you MUST read `./HARNESS-GO.md`.** It is the single source of truth for all validation checks below. Every check in this command maps to a requirement in HARNESS-GO.md.

## Usage

```bash
/cli-anything-go:validate <software-path-or-repo>
```

## Arguments

- `<software-path-or-repo>` - **Required.** Either:
  - A **local path** to the software source code (e.g., `/home/user/gimp`, `./blender`)
  - A **GitHub repository URL** (e.g., `https://github.com/GNOME/gimp`, `github.com/blender/blender`)

  If a GitHub URL is provided, the agent clones the repo locally first, then works on the local copy.

  The software name is derived from the directory name. The agent locates the CLI harness at `<software-name>/agent-harness/`.

## What This Command Validates

### 1. Directory Structure

- `agent-harness/` directory exists
- `cmd/` subdirectory present
- `internal/core/` subdirectory present
- `internal/backend/` subdirectory present
- `internal/output/` subdirectory present
- `internal/repl/` subdirectory present
- `e2e/` subdirectory present
- `testdata/` subdirectory present (optional but recommended)

### 2. Required Files

- `HARNESS-GO.md` — copy of harness specification
- `go.mod` — valid Go module declaration
- `go.sum` — dependency checksums
- `main.go` — entry point
- `cmd/root.go` — root Cobra command
- `internal/core/project.go` — project management
- `internal/backend/<software>.go` — backend availability helpers
- `internal/output/formatter.go` — output formatting
- `internal/repl/repl.go` — REPL model
- `internal/repl/skin.go` — Lip Gloss theme
- `README.md` — installation and usage guide
- `<SOFTWARE>.md` — software-specific SOP
- `TEST.md` — test plan and results (at project root)

### 3. CLI Implementation Standards

- Uses Cobra framework (`github.com/spf13/cobra` in go.mod)
- `--output` flag present on root command with `json`, `yaml`, `table`, `plain` values
- `--project` flag present for project file path
- `--no-color` flag present
- `--verbose` flag present
- REPL launches as default when no subcommand is provided (root `Run` or `RunE` invokes REPL)
- Backend check is a helper function called per-subcommand — NOT a `PersistentPreRunE`

### 4. Core Module Standards

- `internal/core/project.go` defines a `Project` struct and functions for create, open, save, info
- `internal/core/session.go` defines a `Session` struct with lifecycle methods
- `internal/core/export.go` defines export operations and format constants
- All functions return `error` as the final return value
- Error wrapping uses `fmt.Errorf("...: %w", err)` (not `errors.New` for wrapping)
- `context.Context` is threaded through long-running operations
- `internal/` package boundary is respected — no outside packages import from `internal/`

### 5. Test Standards

- Unit test files exist alongside source (`internal/core/*_test.go`)
- Unit tests carry `//go:build unit` build tag
- E2E test files exist in `e2e/` directory
- E2E tests carry `//go:build e2e` build tag
- Subprocess tests use `resolveCLI()` helper — no hardcoded binary paths
- `resolveCLI()` prints which backend is being used (`[resolveCLI]` log line)
- `resolveCLI()` respects `CLI_ANYTHING_FORCE_INSTALLED` environment variable
- Table-driven tests used throughout (slice of `struct{ name, input, want }`)
- `TEST.md` has **Part 1** (test plan) and **Part 2** (test results)

### 6. Documentation Standards

- `README.md` has: installation instructions (`go install`), usage examples, command reference
- `<SOFTWARE>.md` has: architecture analysis, command map, rendering/export gap assessment
- No duplicate copy of `HARNESS-GO.md` content — only a reference copy is acceptable
- All subcommands documented with flags and examples

### 7. Go Module Standards

- `go.mod` declares a valid module path following `github.com/<user>/<software>-cli` convention
- `go build ./...` succeeds with no errors
- `go vet ./...` produces no warnings or errors
- `golangci-lint run ./...` is clean
- `go mod tidy` produces no diff (all imports accounted for)
- `CGO_ENABLED=0 go build .` produces a static binary

### 8. Code Quality

- No compilation errors
- No unused imports
- Proper error wrapping using `%w` verb (not string concatenation)
- `context.Context` used for operations that call subprocesses
- `internal/` package boundary respected throughout
- No hardcoded binary paths (uses `exec.LookPath` or `resolveCLI()`)
- Consistent receiver naming within each type

## Validation Report

The command generates a detailed report:

```
CLI Harness Validation Report
Software: gimp
Path: /home/user/gimp/agent-harness

1. Directory Structure       5/8  checks passed
2. Required Files           13/13 files present
3. CLI Implementation        7/7  standards met
4. Core Module Standards     6/6  standards met
5. Test Standards           10/10 standards met
6. Documentation Standards   4/4  standards met
7. Go Module Standards       6/6  standards met
8. Code Quality              8/8  checks passed

Overall: PASS (59/62 checks)
```

For any failed checks, the report shows:
- Which check failed
- What was expected
- What was found (or missing)
- A suggested fix

## Example

```bash
# Validate a GIMP CLI harness
/cli-anything-go:validate /home/user/gimp

# Validate from a GitHub repository
/cli-anything-go:validate https://github.com/blender/blender
```
