# cli-anything-go Quickstart

Get from zero to a working CLI harness in 5 minutes.

---

## Prerequisites

- **Go 1.25+** — `go version` should print `go1.25` or higher
- **Claude Code** with the plugin system enabled
- The `cli-anything-go` plugin installed (see below)

---

## 1. Install the Plugin

Install the plugin locally in Claude Code:

```bash
claude plugin install /path/to/cli-anything-go
```

Verify it loaded:

```bash
claude plugin list
# Should show: cli-anything-go
```

---

## 2. Your First Build

Point the command at any GUI application's source directory. Using GIMP as an example:

```bash
/cli-anything-go /path/to/gimp
```

Claude Code will run all 7 phases (source analysis through module publishing) and produce a complete CLI harness. This typically takes 3–8 minutes depending on codebase size.

---

## 3. What Gets Generated

```
gimp/
└── agent-harness/
    ├── HARNESS-GO.md        # Reference copy of the harness spec
    ├── GIMP.md              # Software-specific SOP and architecture notes
    ├── README.md            # Installation and usage guide
    ├── go.mod               # Module: github.com/<user>/gimp-cli
    ├── go.sum
    ├── main.go
    ├── cmd/                 # Cobra command definitions
    ├── internal/
    │   ├── core/            # Business logic + unit tests
    │   ├── backend/         # Binary availability helpers
    │   ├── output/          # json/yaml/table/plain formatter
    │   └── repl/            # Bubble Tea REPL model
    ├── TEST.md              # Test plan (Part 1) + results (Part 2)
    └── e2e/
        ├── e2e_test.go
        └── subprocess_test.go
```

For the full directory layout specification and coding standards, see [HARNESS-GO.md](HARNESS-GO.md).

---

## 4. Build and Install

```bash
cd gimp/agent-harness
go build ./...          # Verify it compiles
go install .            # Install binary to $GOPATH/bin
```

The binary is now available as `gimp-cli` in your `$PATH`.

---

## 5. Run Tests

**Unit tests** (no real software required):

```bash
go test -tags unit -v ./...
```

**End-to-end tests** (requires GIMP installed):

```bash
go test -tags e2e -v ./e2e/
```

**Subprocess tests against the installed binary:**

```bash
CLI_ANYTHING_FORCE_INSTALLED=1 go test -tags e2e -v ./e2e/
```

`CLI_ANYTHING_FORCE_INSTALLED=1` tells the test harness to use the installed `gimp-cli` binary instead of building a fresh one for each test run.

---

## 6. Validate the Harness

After building, run the validator to check the harness against all HARNESS-GO.md standards:

```bash
/cli-anything-go:validate /path/to/gimp
```

The validator checks directory structure, required files, CLI implementation standards, test coverage, and Go module hygiene. It prints a scored report and suggests fixes for any failures.

---

## 7. Refine Coverage

Add more commands or expand test coverage with the refine command:

```bash
/cli-anything-go:refine /path/to/gimp
# With a specific focus area:
/cli-anything-go:refine /path/to/gimp "batch export"
```

---

## 8. List Generated CLIs

See all harnesses that are installed or generated on the system:

```bash
/cli-anything-go:list
```

Scan a specific directory:

```bash
/cli-anything-go:list --path /projects --depth 3
```

---

## Common Workflow

```bash
# 1. Build
/cli-anything-go /path/to/gimp

# 2. Test
cd gimp/agent-harness
go test -tags unit -v ./...
go test -tags e2e -v ./e2e/

# 3. Install
go install .

# 4. Validate
/cli-anything-go:validate /path/to/gimp

# 5. Use it
gimp-cli project open myfile.xcf
gimp-cli export png --output /tmp/out.png
gimp-cli repl
```

---

## Troubleshooting

**Software not found (exit code 10)**

The harness exits with code `10` when the wrapped binary is not in `$PATH`. Install the application and make sure it is on your `PATH`:

```bash
which gimp        # Should return a path
gimp --version    # Should work
```

**`go vet` warnings**

Run `go vet ./...` from `agent-harness/` and fix any reported issues before installing. The validator will flag a dirty `go vet` run.

**CGO errors on build**

All harnesses are designed to build without CGO. If you encounter CGO-related linker errors, build with:

```bash
CGO_ENABLED=0 go build .
```

This produces a fully static binary. If `CGO_ENABLED=0` breaks a dependency, check `go.mod` for packages that require CGO and replace them with pure-Go alternatives.

**`go mod tidy` diff**

If `go mod tidy` changes `go.mod` or `go.sum`, run it and commit the result before installing:

```bash
go mod tidy
go install .
```
