# cli-anything-go Command

Build a complete, stateful CLI harness for any GUI application — implemented in Go.

## CRITICAL: Read HARNESS-GO.md First

**Before doing anything else, you MUST read `./HARNESS-GO.md`.** It defines the complete methodology, architecture standards, and implementation patterns. Every phase below follows HARNESS-GO.md. Do not improvise — follow the harness specification.

## Usage

```bash
/cli-anything-go <software-path-or-repo>
```

## Arguments

- `<software-path-or-repo>` - **Required.** Either:
  - A **local path** to the software source code (e.g., `/home/user/gimp`, `./blender`)
  - A **GitHub repository URL** (e.g., `https://github.com/GNOME/gimp`, `github.com/blender/blender`)

  If a GitHub URL is provided, clone the repo locally first, then work on the local copy.

  **Note:** Software names alone (e.g., "gimp") are NOT accepted. You must provide the actual source code path or repository URL so the agent can analyze the codebase.

## What This Command Does

This command implements the complete cli-anything-go methodology to build a production-ready Go CLI harness for any GUI application. **All phases follow the standards defined in HARNESS-GO.md.**

### Phase 0: Source Acquisition

- If `<software-path-or-repo>` is a GitHub URL, clone it to a local working directory
- Verify the local path exists and contains source code
- Derive the software name from the directory name (e.g., `/home/user/gimp` -> `gimp`)

### Phase 1: Codebase Analysis

- Analyze the local source code
- Identify the backend engine and data model
- Map GUI actions to API calls
- Identify existing CLI tools and scriptable interfaces
- Document the architecture in preparation for CLI design

### Phase 2: CLI Architecture Design

- Design command groups matching the application's domains
- Plan the state model and output formats
- Create the software-specific SOP document (e.g., `GIMP.md`)
- Interaction model is always **Both** (CLI one-shot commands + REPL mode)

### Phase 3: Implementation

Follow HARNESS-GO.md for all directory layout, module structure, and coding standards.

- Create the directory structure per HARNESS-GO.md
- Copy `HARNESS-GO.md` from the plugin into the generated `agent-harness/` directory
- Scaffold `go.mod` with module path `github.com/<user>/<software>-cli`
- Implement `internal/core/` modules:
  - `project.go` — project loading, validation, state
  - `session.go` — session lifecycle and session info struct
  - `export.go` — export operations
  - Additional domain-specific modules as needed
- Implement `internal/backend/<software>.go` — backend availability check as a **helper function called per-subcommand**, NOT as `PersistentPreRunE`
- Implement `internal/output/formatter.go` — supports `json`, `yaml`, `table`, and `plain` formats; respects `--no-color`
- Build `cmd/` Cobra commands:
  - `root.go` — root command, global flags (`--output`, `--no-color`)
  - `project.go` — project management subcommands
  - `session.go` — session management subcommands
  - `export.go` — export subcommands
  - `config.go` — configuration subcommands
  - Domain-specific command files as warranted by the application
- Implement `internal/repl/` — Bubble Tea model with Lip Gloss skin
- Wire `main.go` entry point
- Use templates from the plugin's `templates/` directory as starting points

### Phase 4: Test Planning

- Create `TEST.md` Part 1 with a complete test inventory
- Plan unit tests for every function in `internal/core/`
- Plan E2E tests with real files and full pipeline execution
- Plan subprocess tests that invoke the installed binary
- Design realistic multi-step workflow scenarios

### Phase 5: Test Implementation

- Write unit tests alongside source (`internal/core/*_test.go`) tagged `//go:build unit`
- Write E2E tests (`e2e/e2e_test.go`) tagged `//go:build e2e`
- Write subprocess tests (`e2e/subprocess_test.go`) tagged `//go:build e2e` using `resolveCLI()`
- Use table-driven tests with Testify assertions throughout
- Include output verification (magic bytes, media probing, format validation)

### Phase 6: Test Documentation

- Run `go test -tags unit -v ./...` and `go test -tags e2e -v ./e2e/`
- Append full results to `TEST.md` Part 2 — always, regardless of pass/fail
- Document test coverage and any gaps

### Phase 7: Go Module Publishing & Installation

- Verify `go build ./...`, `go vet ./...`, and `golangci-lint run ./...` are clean
- Run `go install`, verify binary appears in `$PATH`
- Run subprocess tests with `CLI_ANYTHING_FORCE_INSTALLED=1`
- Verify `go mod tidy` leaves no diff

## Output Structure

```
<software-name>/
└── agent-harness/
    ├── HARNESS-GO.md          # Copy of harness spec (reference)
    ├── <SOFTWARE>.md          # Software-specific SOP
    ├── README.md              # Installation and usage guide
    ├── go.mod                 # Module: github.com/<user>/<software>-cli
    ├── go.sum
    ├── main.go                # Entry point
    ├── cmd/                   # Cobra command definitions
    │   ├── root.go
    │   ├── project.go
    │   ├── session.go
    │   ├── export.go
    │   ├── config.go
    │   └── <domain>.go        # Additional domain commands
    ├── internal/
    │   ├── core/              # Business logic
    │   │   ├── project.go
    │   │   ├── project_test.go
    │   │   ├── session.go
    │   │   ├── session_test.go
    │   │   ├── export.go
    │   │   └── export_test.go
    │   ├── backend/
    │   │   └── <software>.go  # Backend availability helpers
    │   ├── output/
    │   │   └── formatter.go   # json/yaml/table/plain + --no-color
    │   └── repl/
    │       ├── repl.go        # Bubble Tea REPL model
    │       └── skin.go        # Lip Gloss theme
    ├── TEST.md                # Test plan (Part 1) and results (Part 2)
    └── e2e/
        ├── e2e_test.go        # E2E tests (//go:build e2e)
        └── subprocess_test.go # Subprocess tests using resolveCLI()
```

## Example

```bash
# Build a CLI for GIMP from local source
/cli-anything-go /home/user/gimp

# Build from a GitHub repository
/cli-anything-go https://github.com/blender/blender
```

## Success Criteria

The command succeeds when:

1. All core modules are implemented and functional
2. CLI supports both one-shot commands and REPL mode
3. `--output` flag works for all commands (`json`, `yaml`, `table`, `plain`)
4. All tests pass (100% pass rate)
5. Subprocess tests use `resolveCLI()` and pass with `CLI_ANYTHING_FORCE_INSTALLED=1`
6. `TEST.md` contains both the test plan and the test results
7. `README.md` documents installation and usage
8. `go.mod` is created and `go install` works
9. Binary is available in `$PATH` as `<software>-cli`
10. `go vet ./...` and `golangci-lint run ./...` are clean
11. `CGO_ENABLED=0 go build .` produces a static binary
