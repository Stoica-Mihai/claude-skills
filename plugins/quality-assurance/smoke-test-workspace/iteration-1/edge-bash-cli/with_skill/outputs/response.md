# Smoke tests for a Bash CLI

Honest scoping note up front: the `smoke-test` skill I have here ships
templates for **web services and HTTP APIs** — FastAPI/pytest,
Express/Vitest, Go `net/http`, axum/tower. There is no canonical CLI
template, so I'm going to adapt rather than pretend one fits. The
underlying smoke-test discipline still applies — broad/shallow,
idempotent, <2 minutes, fail fast, 5–10 checks — only the runner and
the "what to probe" list change.

For a ~400-line Bash CLI with a few subcommands, the right runner is
**`bats-core`** (Bash Automated Testing System). It's the de-facto
standard for testing shell programs, runs anywhere bash runs, ships in
most package managers (`apt install bats`, `brew install bats-core`),
and produces TAP output that CI tools already understand. **ShellCheck**
sits alongside it as a static-analysis gate — different category, but
worth wiring into the same CI step because it catches a huge class of
"deploy is broken" failures (unset vars, quoting bugs, bashisms in
`/bin/sh` scripts) before any test runs.

## What I need from you before scaffolding

So I can name your subcommands instead of writing `TODO` everywhere:

1. The CLI's name + path (`./mytool`, `bin/mytool`, …).
2. The subcommands you want covered — pick the 3–5 most critical
   happy-paths.
3. Are any subcommands **destructive** (write files, hit network, mutate
   state)? Those get isolated to a `BATS_TEST_TMPDIR` sandbox or skipped
   in prod smoke.
4. Do you want ShellCheck wired in as well, or just functional tests?
5. CI target — GitHub Actions, GitLab, Jenkins, none?

## Proposed smoke suite shape (the 5–10 checks)

These are the CLI analogues of the skill's default web-service shape.
You'd prune to the ones that match your tool:

1. **`mytool --version`** prints a non-empty version string, exit 0.
   *(analogue of "service is up")*
2. **`mytool --help`** exits 0 and lists every documented subcommand.
   *(analogue of "routes registered")*
3. **`mytool <unknown-subcommand>`** exits non-zero with a usage message
   on stderr. *(error-path / 404 analogue)*
4. **`mytool <subcommand-1> <good-input>`** exits 0 and produces the
   expected output shape (stdout matches, file gets created, etc.).
   *(primary read/write happy-path)*
5. **`mytool <subcommand-2> <good-input>`** — same idea, second
   critical subcommand.
6. **Missing required flag** → exit non-zero, helpful error on stderr.
   *(input-validation gate, not deep validation)*
7. **`mytool` with no args** → prints help, exits with documented code
   (often 0 or 2 — pick what the contract says).
8. **(optional)** External dependency probe — if the tool requires
   `jq`/`curl`/`git`, one check that it fails cleanly when the
   dependency is missing (mock by `PATH=/empty`). Skip if your tool has
   no hard external deps.
9. **(optional)** ShellCheck passes on the script with zero errors —
   *static* smoke, runs in ~100ms, catches the most embarrassing
   regressions before functional tests even start.

That's 6–9 checks, well inside the <2-minute budget — for a Bash CLI
this whole suite typically runs in under a second.

## Scaffold shape (what I'd write once you confirm)

```
tests/smoke/
  smoke.bats           # the bats suite, one @test per check above
  helpers.bash         # shared setup/teardown, tmpdir helpers
  fixtures/            # any sample inputs the tests feed in
.github/workflows/
  smoke.yml            # (only if you said GH Actions) installs bats +
                       # shellcheck, runs both as the deploy gate
```

A representative `smoke.bats` test looks like:

```bash
#!/usr/bin/env bats

setup() {
  CLI="${BATS_TEST_DIRNAME}/../../mytool"   # TODO: confirm path
  export TMP="$BATS_TEST_TMPDIR"            # bats gives us per-test tmpdir
}

@test "version prints non-empty string" {
  run "$CLI" --version
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}

@test "help lists all subcommands" {
  run "$CLI" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"subcmd-a"* ]]            # TODO: real names
  [[ "$output" == *"subcmd-b"* ]]
}

@test "unknown subcommand exits non-zero" {
  run "$CLI" definitely-not-a-real-subcmd
  [ "$status" -ne 0 ]
  [[ "$output" == *"usage"* || "$output" == *"unknown"* ]]
}
```

Local run command would be `bats tests/smoke -t` — TAP output, <1s
expected. CI step is just `bats tests/smoke && shellcheck mytool`.

## Failure-mode reminders (these carry over from the skill's principles)

- Treat a red smoke run as **stop-the-line** — block the deploy/merge.
- On failure, surface the actual `output`/`status` — bats does this by
  default; don't suppress it.
- Anything destructive runs inside `$BATS_TEST_TMPDIR` so the suite is
  idempotent and safe to point at any environment.
- Flaky test → quarantine with `skip "flaky, fix by <date>"`, don't
  delete; fix within the sprint.

## Want me to proceed?

Send me answers to the five questions above (CLI path, top 3–5
subcommands, any destructive ones, ShellCheck yes/no, CI target) and
I'll write the actual `smoke.bats` + helpers + CI snippet with your
real subcommand names baked in. If you'd rather I just generate a
generic skeleton with `TODO` markers everywhere, say the word — same
output, more placeholders.
