# Deploy smoke test for the express-app fixture

You're losing mornings because nobody knows whether the deploy is even alive
before QA starts clicking. The fix is a tiny, fast, deterministic test that
hits every route once and exits non-zero if anything is obviously broken. Two
flavors, pick whichever fits your pipeline:

## What I shipped

1. **`smoke.test.js`** — in-process vitest + supertest smoke. Imports the
   exported `app` (no port, no network), fires ~7 requests, finishes in under
   a second. This is what to run in CI immediately after build, before
   producing a deployable artifact.
2. **`smoke-live.sh`** — pure `curl`/`bash` script aimed at a deployed URL.
   Run it post-deploy from the pipeline (or from a laptop) against staging /
   prod / a preview env. Exits non-zero the moment anything fails, with the
   failing response body printed. This is the one that gates QA: green here
   means "go ahead and test", red means "don't bother, the deploy is dead".

Both cover the same shape of checks, derived from
`fixtures/express-app/src/index.js`:

| Check | Why it matters for a deploy smoke |
|---|---|
| `GET /health` → 200 `{status:"ok"}` | App booted and is serving HTTP. |
| `GET /users/1` → 200 | Read path + JSON serializer works. |
| `GET /users/9999` → 404 | Error handling path isn't crashing into 500. |
| `POST /orders` no auth → 401 | Auth middleware is wired (regression magnet). |
| `POST /orders` unknown user → 400 | Validation path works. |
| `POST /orders` happy path → 201 + id | Write path + request body parsing works. |
| `GET /orders/:id` for the order we just created → 200 | State is reachable end-to-end. |
| `GET /orders/999999` → 404 | Read-miss path. |

That's the minimum that distinguishes "the deploy is completely dead" from
"the deploy looks alive, QA can take over". It is intentionally not a full
functional suite — anything more is QA's job.

## Running it

In-process (CI, pre-deploy):

```bash
cd plugins/quality-assurance/skills/smoke-test/evals/fixtures/express-app
npm install
npx vitest run ../../../../smoke-test-workspace/iteration-1/express-deploy-pain/without_skill/outputs/smoke.test.js
```

Or copy `smoke.test.js` into the fixture's own folder and just `npm test`.

Live (post-deploy gate):

```bash
BASE_URL=https://staging.example.com SMOKE_TOKEN="Bearer $REAL_TOKEN" \
  ./outputs/smoke-live.sh
```

Wire `smoke-live.sh` as the last step of the deploy job. If it exits non-zero,
fail the deploy and skip notifying QA. That alone should kill the broken-morning
loop.

## Notes / honest caveats

- `POST /orders` accepts any `Bearer …` token — the app doesn't actually
  validate it. The smoke test uses `Bearer smoketest`. If you later add real
  token verification, point `SMOKE_TOKEN` at a dedicated smoke-test credential,
  don't reuse a human's.
- `orders` is in-memory in the fixture, so the create-then-read step works
  against a single instance. Behind a load balancer with >1 replica you'd want
  sticky sessions for the smoke run, or split the create/read into separate
  independent checks. Flag this if/when you move to a real datastore.
- `nextOrderId` is process-local — fine for smoke, irrelevant once a DB is
  involved.
- The script uses `sed` to pull the order id out of the JSON to avoid a `jq`
  dependency. If `jq` is guaranteed on your runners, swap it in for robustness.
