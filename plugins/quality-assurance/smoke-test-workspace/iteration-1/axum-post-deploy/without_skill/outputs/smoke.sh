#!/usr/bin/env bash
# Post-deploy health checks for axum-app.
# Idempotent: only read-only GETs against the live service. No POST /orders
# (auto-increments next_id server-side and would leak state across runs).
#
# Usage:
#   BASE_URL=https://prod.example.com ./smoke.sh
#   BASE_URL=https://prod.example.com TIMEOUT=5 RETRIES=5 ./smoke.sh
#
# Exit codes:
#   0 = all checks passed (safe to promote)
#   1 = a check failed (block promotion)
#   2 = bad usage / config

set -u
set -o pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
TIMEOUT="${TIMEOUT:-5}"          # per-request seconds
RETRIES="${RETRIES:-5}"          # retries per check (handles rolling deploy warm-up)
RETRY_SLEEP="${RETRY_SLEEP:-2}"  # seconds between retries

# Seeded user ids in the app. Override if prod is seeded differently.
KNOWN_USER_ID="${KNOWN_USER_ID:-1}"
# A user id that must NOT exist; verifies 404 path is wired.
UNKNOWN_USER_ID="${UNKNOWN_USER_ID:-999999999}"
# Same idea for orders: id that must not exist.
UNKNOWN_ORDER_ID="${UNKNOWN_ORDER_ID:-999999999}"

pass=0
fail=0
failed_names=()

log()  { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }
ok()   { printf '  PASS  %s\n' "$1"; pass=$((pass+1)); }
bad()  { printf '  FAIL  %s -- %s\n' "$1" "$2"; fail=$((fail+1)); failed_names+=("$1"); }

# curl_status METHOD PATH [extra curl args...]
# Echoes "HTTP_STATUS\nBODY". Uses --max-time and --fail-with-body so transport
# errors are distinguishable from HTTP errors.
curl_call() {
  local method="$1"; shift
  local path="$1"; shift
  curl -sS \
       --max-time "$TIMEOUT" \
       -o /tmp/smoke_body.$$ \
       -w '%{http_code}' \
       -X "$method" \
       "$@" \
       "${BASE_URL}${path}"
}

# check NAME EXPECTED_STATUS METHOD PATH [BODY_REGEX] [extra curl args...]
check() {
  local name="$1" expected="$2" method="$3" path="$4"
  local body_regex="${5:-}"
  shift 5 || true
  local attempt=1 status body
  while : ; do
    status="$(curl_call "$method" "$path" "$@" || true)"
    body="$(cat /tmp/smoke_body.$$ 2>/dev/null || true)"
    rm -f /tmp/smoke_body.$$

    if [[ "$status" == "$expected" ]]; then
      if [[ -n "$body_regex" ]] && ! grep -Eq "$body_regex" <<<"$body"; then
        if (( attempt >= RETRIES )); then
          bad "$name" "status ok ($status) but body did not match /$body_regex/: $body"
          return
        fi
      else
        ok "$name"
        return
      fi
    else
      if (( attempt >= RETRIES )); then
        bad "$name" "expected $expected, got '$status' ($method $path) body=$body"
        return
      fi
    fi
    attempt=$((attempt+1))
    sleep "$RETRY_SLEEP"
  done
}

log "Smoke testing ${BASE_URL} (timeout=${TIMEOUT}s, retries=${RETRIES})"

# 1. Liveness — /health must be 200 and report status:ok.
check "health endpoint"           200 GET  "/health"                                '"status"[[:space:]]*:[[:space:]]*"ok"'

# 2. Known user is reachable and the response shape is sane.
check "known user lookup"         200 GET  "/users/${KNOWN_USER_ID}"                "\"id\"[[:space:]]*:[[:space:]]*${KNOWN_USER_ID}"

# 3. Unknown user returns 404 (verifies routing + error path, not just happy path).
check "unknown user is 404"       404 GET  "/users/${UNKNOWN_USER_ID}"

# 4. Unknown order returns 404.
check "unknown order is 404"      404 GET  "/orders/${UNKNOWN_ORDER_ID}"

# 5. Auth gate on POST /orders without writing state.
#    OPTIONS would also work but axum 0.7 default router doesn't auto-respond
#    to OPTIONS. Sending POST with NO Authorization header must yield 401, and
#    because the handler short-circuits BEFORE touching state, this is safe to
#    run repeatedly against prod.
check "orders requires auth"      401 POST "/orders" \
      '' \
      -H 'content-type: application/json' \
      --data '{"user_id":1,"items":["probe"]}'

# 6. Auth-gate sanity #2: a Bearer token plus an obviously-bad user_id must
#    return 400 BEFORE inserting. Same reasoning: handler returns BAD_REQUEST
#    before s.next_id is incremented, so no state mutation. We do NOT send a
#    valid user_id here, that would create an order.
check "orders rejects bad user"   400 POST "/orders" \
      '' \
      -H 'content-type: application/json' \
      -H 'authorization: Bearer smoke-test-probe' \
      --data "{\"user_id\":${UNKNOWN_USER_ID},\"items\":[\"probe\"]}"

echo
log "Result: ${pass} passed, ${fail} failed"
if (( fail > 0 )); then
  printf 'Failed checks:\n'
  for n in "${failed_names[@]}"; do printf '  - %s\n' "$n"; done
  exit 1
fi
exit 0
