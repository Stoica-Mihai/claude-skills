# Post-deploy smoke checks for axum-app

## What I inspected

`src/main.rs` exposes four routes:

| Route | Method | Notes |
|---|---|---|
| `/health` | GET | returns `{"status":"ok"}` |
| `/users/:id` | GET | seeded with ids `1` (alice) and `2` (bob) |
| `/orders` | POST | requires `Authorization: Bearer …`; validates `user_id`; **mutates** `next_id` and inserts an order |
| `/orders/:id` | GET | 404 if unknown |

## Idempotency analysis (this drove the design)

Running the checks repeatedly against the live prod env must not leave state behind.

- `GET /health`, `GET /users/:id`, `GET /orders/:id` — pure reads, always safe.
- `POST /orders` — the handler short-circuits on auth and on unknown `user_id` *before* touching `AppState`. Specifically:
  - missing/non-`Bearer` auth header → returns `401` at line 55, before `state.lock()`,
  - unknown `user_id` → returns `400` at line 59, before `next_id += 1` at line 61.

So we can exercise the auth gate and the validation gate of `POST /orders` without ever creating an order. We never send a request that would reach the `s.next_id += 1` line. That keeps the suite fully idempotent.

I deliberately did **not** include a "create an order, then fetch it, then expect it to be deletable" round-trip — there is no DELETE in the service, so any successful POST would permanently grow prod state. Auth-gate + bad-input probes give us coverage of the POST path without that cost.

## The script

`smoke.sh` — bash + curl, no extra runtime deps. Six checks:

1. `/health` returns 200 with `"status":"ok"` (liveness + JSON shape).
2. `/users/1` returns 200 and includes `"id":1` (seeded data reachable, DB/state wired).
3. `/users/999999999` returns 404 (routing + error path wired, not just happy path).
4. `/orders/999999999` returns 404.
5. `POST /orders` with no auth → 401 (auth middleware/gate is live). **Idempotent**: handler returns before state mutation.
6. `POST /orders` with valid Bearer but unknown `user_id` → 400 (validation gate live). **Idempotent** for the same reason.

Behaviour worth calling out:

- Per-request `--max-time` so a hung backend can't wedge the promoter.
- `RETRIES` / `RETRY_SLEEP` env knobs — important during a rolling deploy where the new pods may briefly serve 502/503 from the LB before they're ready. Default 5 retries × 2 s.
- Configurable `KNOWN_USER_ID` / `UNKNOWN_USER_ID` / `UNKNOWN_ORDER_ID` so the same script works against an env whose seed data differs.
- Exits non-zero on the first persistent failure with a summary, so it slots straight into a CI gate.

## Usage

```bash
BASE_URL=https://prod.example.com ./smoke.sh
# or, tighter, in a CD pipeline:
BASE_URL=https://prod.example.com TIMEOUT=3 RETRIES=10 RETRY_SLEEP=3 ./smoke.sh
```

## What I did **not** do, and why

- No load / latency assertions — that's a separate concern (perf canary, not smoke).
- No "happy-path POST /orders" — would mutate prod state, violates the idempotency requirement you set.
- No TLS / cert checks beyond what curl does by default — add `--cacert` or `--resolve` flags in the pipeline if you pin certs.
- No auth-token probing with a real production Bearer token — checks 5 and 6 use a dummy token because we only want to observe the 401 / 400 boundaries, not authenticate as a real principal.

## Files generated

- `outputs/smoke.sh` — the script (executable, `bash -n` clean).
- `outputs/response.md` — this note.
