#!/usr/bin/env bash
# Live-deploy smoke test. Hits a running instance over HTTP and bails on the
# first failure. Use this against a deployed URL before QA touches the env.
#
# Usage:  BASE_URL=https://staging.example.com ./smoke-live.sh
#         ./smoke-live.sh http://localhost:3000
#
# Exit codes: 0 = deploy looks alive, non-zero = deploy is dead, stop QA.
set -euo pipefail

BASE="${1:-${BASE_URL:-http://localhost:3000}}"
TOKEN="${SMOKE_TOKEN:-Bearer smoketest}"

# Each check: METHOD URL EXPECTED_STATUS [extra curl args...]
check() {
  local name="$1" method="$2" path="$3" want="$4"; shift 4
  local got
  got=$(curl -sS -o /tmp/smoke.body -w "%{http_code}" \
          --max-time 5 -X "$method" "$BASE$path" "$@" || echo "000")
  if [ "$got" != "$want" ]; then
    echo "FAIL  $name  $method $path  want=$want got=$got"
    echo "----- body -----"; cat /tmp/smoke.body || true; echo
    exit 1
  fi
  echo "ok    $name  $method $path  $got"
}

echo "Smoke testing $BASE"

check "health"          GET  /health         200
check "user known"      GET  /users/1        200
check "user unknown"    GET  /users/9999     404
check "orders no-auth"  POST /orders         401 \
    -H "Content-Type: application/json" -d '{"userId":1,"items":[]}'
check "orders bad user" POST /orders         400 \
    -H "Content-Type: application/json" -H "Authorization: $TOKEN" \
    -d '{"userId":9999,"items":[]}'

# Happy path: create order, then read it back.
ORDER_ID=$(curl -sS --max-time 5 -X POST "$BASE/orders" \
    -H "Content-Type: application/json" -H "Authorization: $TOKEN" \
    -d '{"userId":1,"items":["widget"]}' | \
    sed -n 's/.*"id":\([0-9][0-9]*\).*/\1/p')
[ -n "$ORDER_ID" ] || { echo "FAIL  create order returned no id"; exit 1; }
echo "ok    orders create id=$ORDER_ID"

check "orders read"     GET  "/orders/$ORDER_ID" 200
check "orders missing"  GET  /orders/999999      404

echo "PASS  deploy looks alive"
