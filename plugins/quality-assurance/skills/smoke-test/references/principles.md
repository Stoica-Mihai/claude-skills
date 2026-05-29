# Smoke Testing — Principles Reference

Distilled background for the `smoke-test` skill. Read selectively — the
SKILL.md already includes the load-bearing rules. This file exists for
the user who asks *why*, or for cases where the skill needs to make a
defensible recommendation.

## Table of contents

1. [Origin & definition](#origin--definition)
2. [Smoke vs sanity vs regression vs retest](#smoke-vs-sanity-vs-regression-vs-retest)
3. [Suite-design rules of thumb](#suite-design-rules-of-thumb)
4. [Domain checklists](#domain-checklists)
5. [Quality-engineering metrics (for the QA dashboard, not the gate)](#quality-engineering-metrics)
6. [Common failure modes](#common-failure-modes)

## Origin & definition

The metaphor is from electrical / plumbing engineering — power on the
board, watch for smoke. In software, ISTQB defines smoke testing as a
preliminary suite that verifies the *main functions* of the system
before more detailed testing begins. The objective is not bug-finding;
it is **build-stability gating**.

Microsoft formalised "daily build + smoke test" in the 1990s as the
project heartbeat. Cusumano + Selby called it the "sync pulse".
McConnell argued that the cadence matters most under schedule pressure,
when teams are tempted to skip discipline. The cultural pattern is the
same in every shop: a failed smoke is a stop-the-line event.

## Smoke vs sanity vs regression vs retest

| Dimension | Smoke | Sanity | Regression | Retest |
|---|---|---|---|---|
| Purpose | Verify build is stable enough to test | Verify a specific change is rational | Verify nothing else broke | Verify one bug is now fixed |
| Scope | Broad + shallow, critical paths | Narrow + deep, changed modules | Comprehensive | Reproduction steps only |
| Build state | Unstable / fresh | Post-smoke / stable | Release-ready | Stable with fix |
| Timing | First, after deploy | After a focused fix | Late, before release | After fix lands |
| Method | Mostly automated | Often manual | Highly automated | Either |
| Relationship | Subset of regression | Subset of regression | Superset | Independent |

Smoke and sanity are sometimes conflated in casual conversation but the
distinction is load-bearing: a sanity test trusts that smoke already
passed and only re-checks the area touched by a recent change.

## Suite-design rules of thumb

These are the rules the skill applies when proposing the 5-10 checks.

- **5–10 checks for small/medium services**, 20–50 for large enterprise
  apps. Past that the gate is too slow to gate anything.
- **API-first**: HTTP / API assertions in milliseconds; UI tests in
  seconds; UI smoke only when the flow is unobservable at the API.
- **< 2 minutes wall-clock** end-to-end. > 2 minutes degrades developer
  trust; > 15 minutes is effectively no gate.
- **Idempotent**: every run can be rerun in any order without state
  pollution. No shared mutable test data.
- **Read-only-safe**: writes only with explicit ephemeral test data and
  cleanup, or guarded so prod runs skip them.
- **No hard sleeps**: replace `sleep(5)` with polling waits driven by
  the real condition.
- **No flaky tests in the gate**: quarantine to a non-blocking suite,
  fix within the sprint, do not let them rot the signal.

Typical primary checks worth including:

- Readiness / health probe responds 200
- Token mint / basic auth succeeds; missing-token returns 401
- One primary read endpoint returns correct shape for known fixture
- (Optional) one primary write that is provably idempotent
- One dependency-liveness probe — DB read, cache ping, queue depth
- One representative error path (404 / 401) returns correct status

## Domain checklists

For each domain, the canonical happy-path list. These are starting
points, not contracts.

### Web / e-commerce

- Homepage / app loads
- User logs in with valid creds
- Search bar returns product listings
- Add to cart works
- Checkout funnel loads, payment stub succeeds

### API service

- Health endpoint 200
- Auth endpoint mints token / rejects bad creds
- One representative GET returns expected schema
- One representative POST creates a record (idempotent or cleanup)
- One unauthorised request returns 401
- One missing-record request returns 404

### Mobile app (out of scope for current templates)

- App installs / launches on target device
- Reaches initial screen without crashing
- Core flows run with active device permissions (GPS, camera)
- Local data syncs with backend
- HTTPS used for API calls

### Messaging / realtime

- WebSocket / SSE connection established
- Message dispatched returns ack
- Recipient receives the message
- Settings panel loads
- Reconnect after drop works

### ERP / CRM / internal tooling

- Core modules deploy + are accessible
- DB read + write queries succeed
- Access control prevents unauthorised access
- Standard report generates with correct data
- Job scheduler runs a no-op job

### ML pipelines (out of scope for current templates)

- Data-source connection succeeds (S3 / DB)
- Preprocessing runs without NaN / Inf
- Model artefact loads into memory
- Inference returns the expected shape
- Output values fall in the expected range

## Quality-engineering metrics

These are for tracking the *process* over time, not for the per-build
gate. Surface them only if the user is building a QA dashboard.

- **Pass rate (PR)**: `(passed / total) × 100`. Build stability across
  deploys. < 100% on smoke is a red flag.
- **Flakiness rate (FR)**: `(flaky / executed) × 100`. Target < 2%.
- **Defect escape rate (DER)**: `(prod / (prod + caught)) × 100`. For
  consumer-facing web, target < 5%.
- **Mean time to detect (MTTD)**: avg time from commit-that-broke to
  detection. Smoke automation drives this from days to minutes.
- **Mean time to repair (MTTR)**: avg time from gate-fail to green
  build. Shorter suites + clearer failure messages drive it down.

Rising FR usually causes engineers to ignore failures, which pushes
MTTD up, which pushes DER up. The feedback loop is real.

## Common failure modes

- **Smoke suite grows into a regression suite.** Symptom: > 15 min
  runtime, > 50 checks. Fix: split — move detailed checks to nightly
  regression, keep smoke under 10.
- **Flaky smoke tests get ignored.** Symptom: "always re-run it once".
  Fix: quarantine to non-blocking suite, debug the root cause
  (timing / pollution / contention), do not let it back into the gate
  until fixed.
- **No diagnostics on failure.** Symptom: "failed at line 47" with no
  payload. Fix: capture response bodies, correlation ids, container
  logs at failure point; redact PII / tokens before storage.
- **Shared mutable test data.** Symptom: tests pass alone, fail in
  parallel. Fix: ephemeral per-run data, programmatic setup + teardown.
- **Smoke runs against the wrong env.** Symptom: "passes in staging
  fails in prod". Fix: parameterise base URL + creds via env vars; run
  against the actual deployed instance, not localhost.
- **Hard-coded waits**. Symptom: "fast machines flake, slow machines
  pass". Fix: replace `sleep` with polling for the actual condition.
