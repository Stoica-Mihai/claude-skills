# Not a smoke-test task — this is load testing

What you're describing (5k RPS against an API with k6 or Locust) is **load /
performance testing**, not smoke testing. They get conflated all the time
because both run "after deploy" and both touch the running service, but they
answer different questions and have different shapes:

| | Smoke test | Load test |
|---|---|---|
| Question | Is the build broken / wired up at all? | Does it hold up under sustained traffic? |
| Traffic shape | 1 request per critical path, ~5-10 total | Thousands of RPS, sustained for minutes/hours |
| Runtime budget | < 2 minutes, gates the deploy | Minutes to hours, runs out-of-band |
| Tooling | pytest / vitest / `go test` / curl | k6, Locust, Gatling, wrk, Vegeta |
| Verdict | Pass/fail — block the pipeline if fail | Latency percentiles, error rate, throughput curve |
| Where it lives | CI, every PR / every deploy | Pre-prod soak, capacity planning, before launches |

A k6 or Locust script aimed at 5k RPS does not belong in a smoke suite — it
would blow the < 2-minute budget, generate non-idempotent write traffic, and
the pass/fail signal you'd want is a latency-percentile curve, not a green
checkmark.

## What I can help with

I'm scoped to smoke / build-verification test design. So:

- **If you also want a smoke suite** that gates deploys to the same API
  before the load test ever runs against a broken build — happy to scaffold
  one (5-10 checks, < 2 min, pytest / vitest / go test depending on your
  stack). That's actually a useful pairing: smoke gates the deploy, load
  test runs against a confirmed-healthy build.
- **For the actual k6 / Locust 5k RPS script** — that's a load-testing
  exercise. I'd suggest asking a separate session, or look at:
  - k6: `k6 run --vus 500 --duration 5m script.js` with a ramping
    `stages` config to climb to 5k RPS
  - Locust: distributed mode (`locust --master` + N workers) since one
    Python worker won't push 5k RPS
  - And think about: where the load generator runs (same VPC, not your
    laptop), test-data isolation, observability on the target side, and
    SLO thresholds you'd call a pass.

Want me to draft a smoke suite for the same API as a sibling artefact, or
is this purely a load-test request? If purely load, I'll bow out — wrong
tool for the job.
