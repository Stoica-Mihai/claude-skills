# cli-anything-go:test Command

Run the test suite for a Go CLI harness and update TEST.md with results.

## CRITICAL: Read HARNESS-GO.md First

**Before doing anything else, you MUST read `./HARNESS-GO.md`.** It defines the test standards, expected structure, build tags, and what constitutes a passing test suite for a Go CLI harness.

## Usage

```bash
/cli-anything-go:test <software-path-or-repo>
```

## Arguments

- `<software-path-or-repo>` - **Required.** Either:
  - A **local path** to the software source code (e.g., `/home/user/gimp`, `./blender`)
  - A **GitHub repository URL** (e.g., `https://github.com/GNOME/gimp`, `github.com/blender/blender`)

  If a GitHub URL is provided, the agent clones the repo locally first, then works on the local copy.

  The software name is derived from the directory name. The agent locates the CLI harness at `<software-name>/agent-harness/`.

## What This Command Does

1. **Locates the harness** — Finds `agent-harness/` under the software path
2. **Runs unit tests** — Executes `go test -tags unit -v ./...` from `agent-harness/`
3. **Runs E2E tests** — Executes `go test -tags e2e -v ./e2e/` from `agent-harness/`
4. **Captures full output** — Saves complete output from both test runs
5. **Verifies subprocess backend** — Confirms `[resolveCLI]` appears in test output, proving the subprocess backend is exercised
6. **Appends results to TEST.md** — Always appends, regardless of pass/fail (failed results are useful documentation)
7. **Reports status** — Shows pass/fail counts and any failures

## Test Execution Details

### Unit Tests

```bash
cd <software>/agent-harness
go test -tags unit -v ./...
```

- Tests all `*_test.go` files with `//go:build unit` tag
- Covers `internal/core/` functions with synthetic data
- Should run fast (no subprocess calls, no real files)

### E2E Tests

```bash
cd <software>/agent-harness
go test -tags e2e -v ./e2e/
```

- Tests `e2e/*_test.go` files with `//go:build e2e` tag
- Covers full pipeline with real files from `testdata/`
- Subprocess tests use `resolveCLI()` — no hardcoded binary paths

### Backend Verification

After running tests, confirm that `[resolveCLI]` appears in E2E test output. This verifies:
- The subprocess test helper is functioning
- The test is using either the installed binary or the locally-built binary (not a mock)
- The `CLI_ANYTHING_FORCE_INSTALLED` environment variable is honored when set

## TEST.md Update Format

Results are **always appended** to the Part 2 section of `TEST.md`, even if tests fail. Failed results are valuable documentation of what is broken and when it broke.

The appended block follows this format:

```markdown
### Run: 2024-03-05 14:30:00

**Unit Tests** (`go test -tags unit -v ./...`)

```
[full go test output]
```

**E2E Tests** (`go test -tags e2e -v ./e2e/`)

```
[full go test output]
```

**Summary**
- Unit: 47 passed, 0 failed
- E2E: 23 passed, 1 failed
- Backend: [resolveCLI] Using installed command: /home/user/go/bin/gimp-cli
```

## Success Criteria

- All unit tests pass
- All E2E tests pass
- `[resolveCLI]` appears in E2E output confirming subprocess backend
- `TEST.md` is updated with the full results

## Failure Handling

If tests fail:
1. Show which tests failed with the failure message
2. **Still append results to TEST.md** (Part 2 documents all runs, including failures)
3. Suggest fixes based on the error output:
   - Build errors → check `go build ./...` first
   - Missing binary → run `go install` then re-run
   - Missing `[resolveCLI]` output → verify `resolveCLI()` is called and prints to stdout
   - Test data missing → check `testdata/` directory is populated
4. Offer to re-run after fixes are applied

## Example

```bash
# Run tests for a GIMP CLI harness
/cli-anything-go:test /home/user/gimp

# Run tests from a GitHub repository
/cli-anything-go:test https://github.com/blender/blender
```
