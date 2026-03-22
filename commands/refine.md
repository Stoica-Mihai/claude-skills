# cli-anything-go:refine Command

Refine an existing Go CLI harness to improve coverage of the software's functions and usage patterns.

## CRITICAL: Read HARNESS-GO.md First

**Before doing anything else, you MUST read `./HARNESS-GO.md`.** All new commands and tests must follow the same standards as the original build. HARNESS-GO.md is the single source of truth for architecture, patterns, and quality requirements. New code that does not conform to HARNESS-GO.md is not acceptable.

## Usage

```bash
/cli-anything-go:refine <software-path> [focus]
```

## Arguments

- `<software-path>` - **Required.** Local path to the software source code (e.g., `/home/user/gimp`, `./blender`). Must be the same source tree used during the original build.

  **Note:** Only local paths are accepted. If you need to work from a GitHub repo, clone it first with `/cli-anything-go`, then refine.

- `[focus]` - **Optional.** A natural-language description of the functionality area to target. When provided, the agent skips broad gap analysis and instead narrows its analysis and implementation to the specified capability area.

  Examples:
  - `/cli-anything-go:refine /home/user/shotcut "vid-in-vid and picture-in-picture features"`
  - `/cli-anything-go:refine /home/user/gimp "all batch processing and scripting filters"`
  - `/cli-anything-go:refine /home/user/blender "particle systems and physics simulation"`
  - `/cli-anything-go:refine /home/user/inkscape "path boolean operations and clipping"`

  When `[focus]` is provided:
  - Step 2 (Analyze Software Capabilities) narrows to only the specified area
  - Step 3 (Gap Analysis) compares only the focused capabilities against current coverage
  - The agent presents findings before implementing, but scoped to the focus area

## What This Command Does

This command is used **after** a CLI harness has already been built with `/cli-anything-go`. It analyzes gaps between the software's full capabilities and what the current CLI covers, then iteratively expands coverage. If a `[focus]` is given, the agent narrows its analysis and implementation to that specific functionality area.

### Step 1: Inventory Current Coverage

- Read `cmd/*.go` to catalog every Cobra command, subcommand, and flag currently defined
- Read `internal/core/*.go` to catalog every exported function and type
- Read the existing test files to understand what is currently tested
- Build a coverage map: `{ function_or_command: covered | not_covered }`
- Identify patterns already in use (Cobra structure, output formatting, error handling style)

### Step 2: Analyze Software Capabilities

- Re-scan the software source at `<software-path>`
- Identify all public APIs, CLI tools, scripting interfaces, configuration knobs, and batch-mode operations
- Focus on operations that produce observable output (renders, exports, transforms, conversions, queries)
- Categorize by domain (e.g., for GIMP: filters, color adjustments, layer ops, selections, scripting)

  If `[focus]` is provided, narrow this scan to only the specified area.

### Step 3: Gap Analysis

- Compare current CLI coverage against the software's full capability set
- Prioritize gaps by:
  1. **High impact** — commonly used functions missing from the CLI
  2. **Easy wins** — operations with simple, well-defined inputs and outputs
  3. **Composability** — operations that unlock new workflows when combined with existing commands
- Present the gap report to the user and confirm which gaps to address before implementing

### Step 4: Implement New Commands

- Add new Cobra commands and subcommands in `cmd/` following the exact same patterns as existing commands
- Add corresponding core logic in `internal/core/` or a new domain-specific package under `internal/`
- Follow HARNESS-GO.md standards for every new file:
  - `--output` flag wired through to `formatter.go`
  - `--project` flag plumbed to core functions
  - Backend check as a helper function called inside `RunE`, not as `PersistentPreRunE`
  - Error wrapping with `fmt.Errorf("...: %w", err)`
  - `context.Context` passed to subprocess-calling functions
- Never modify the calling convention of existing commands — only add, never break

### Step 5: Expand Tests

- Add unit tests alongside every new `internal/` file (`<file>_test.go`)
  - Tag: `//go:build unit`
  - Use table-driven tests with Testify assertions
  - Use synthetic data only — no subprocess calls
- Add E2E tests in `e2e/` for new commands
  - Tag: `//go:build e2e`
  - Use `resolveCLI()` for subprocess tests — no hardcoded binary paths
  - Test realistic multi-step workflows where possible
- Run the full test suite (old + new) to ensure no regressions:
  ```bash
  go test -tags unit -v ./...
  go test -tags e2e -v ./e2e/
  ```

### Step 6: Update Documentation

- Update `README.md` with new commands, flags, and usage examples
- Update `<SOFTWARE>.md` with expanded coverage notes and any new architectural insights
- Append test results to `TEST.md` Part 2

## Example

```bash
# Broad refinement — agent finds gaps across all capabilities
/cli-anything-go:refine /home/user/gimp

# Focused refinement — agent targets a specific functionality area
/cli-anything-go:refine /home/user/shotcut "vid-in-vid and picture-in-picture compositing"
/cli-anything-go:refine /home/user/gimp "batch processing and Script-Fu filters"
/cli-anything-go:refine /home/user/blender "particle systems and physics simulation"
/cli-anything-go:refine /home/user/inkscape "path boolean operations and clipping masks"
```

## Success Criteria

- All existing tests still pass (no regressions)
- New commands follow the same architectural patterns defined in HARNESS-GO.md
- New tests carry correct build tags (`//go:build unit` or `//go:build e2e`)
- New tests achieve 100% pass rate
- Coverage meaningfully improved — new software functions are now accessible via the CLI
- `go vet ./...` and `golangci-lint run ./...` remain clean after changes
- Documentation updated to reflect all new commands

## Notes

- Refine is incremental — run it multiple times to steadily expand coverage
- Each run should focus on a coherent set of related functions, not try to cover everything at once
- The gap analysis must be presented before implementation so the user can steer priorities
- Refine never removes existing commands — it only adds or enhances
- If a `[focus]` area reveals architectural changes are needed (e.g., a new `internal/` package), implement those cleanly rather than bolting onto existing packages
