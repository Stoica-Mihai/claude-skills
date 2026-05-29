// tests/smoke.rs
//
// Post-deploy smoke tests for the axum-app service.
// Purpose: prove a fresh deploy is healthy enough to promote — not regression.
// Runtime budget: < 30 s wall-clock against a live environment.
// Idempotent: all checks are GETs or auth-rejection probes that do NOT mutate
//   state. Safe to run against production on every deploy.
//
// Run against a deployed env:
//   SMOKE_BASE_URL=https://api.example.com cargo test --test smoke -- --nocapture
//
// Run locally against `cargo run`:
//   SMOKE_BASE_URL=http://localhost:8080 cargo test --test smoke -- --nocapture
//
// If SMOKE_BASE_URL is unset the suite is skipped (so `cargo test` in CI for
// unrelated changes does not fail on missing env). To force a failure when
// the env is missing, set SMOKE_REQUIRE_BASE_URL=1.

use reqwest::{Client, StatusCode};
use std::time::Duration;

fn base_url() -> Option<String> {
    match std::env::var("SMOKE_BASE_URL") {
        Ok(v) if !v.is_empty() => Some(v.trim_end_matches('/').to_string()),
        _ => {
            if std::env::var("SMOKE_REQUIRE_BASE_URL").ok().as_deref() == Some("1") {
                panic!("SMOKE_BASE_URL is required but not set");
            }
            eprintln!("SMOKE_BASE_URL not set — skipping smoke tests");
            None
        }
    }
}

fn client() -> Client {
    Client::builder()
        .timeout(Duration::from_secs(5))
        .connect_timeout(Duration::from_secs(3))
        .user_agent("axum-app-smoke/1.0")
        .build()
        .expect("reqwest client build")
}

// A user id known to exist in every environment. TODO: confirm with ops that
// id=1 is a seeded fixture in prod, or swap for an env var.
const KNOWN_USER_ID: u64 = 1;

// A user id that must NOT exist. Picked to be well above any realistic id;
// override per environment if your id space is larger.
const MISSING_USER_ID: u64 = 99_999_999;

// An order id that must NOT exist. Same reasoning.
const MISSING_ORDER_ID: u64 = 99_999_999;

fn dump(label: &str, status: StatusCode, body: &str, correlation: Option<&str>) {
    eprintln!(
        "[smoke] {label} status={status} correlation_id={cid} body={body}",
        cid = correlation.unwrap_or("<none>"),
    );
}

fn correlation<'a>(resp: &'a reqwest::Response) -> Option<&'a str> {
    resp.headers()
        .get("x-request-id")
        .or_else(|| resp.headers().get("x-correlation-id"))
        .and_then(|v| v.to_str().ok())
}

// 1. Health endpoint returns 200 + {"status":"ok"} — the basic liveness probe.
#[tokio::test]
async fn health_returns_ok() {
    let Some(base) = base_url() else { return };
    let url = format!("{base}/health");
    let resp = client().get(&url).send().await.expect("GET /health");
    let status = resp.status();
    let cid = correlation(&resp).map(str::to_string);
    let body = resp.text().await.unwrap_or_default();
    dump("GET /health", status, &body, cid.as_deref());
    assert_eq!(status, StatusCode::OK, "GET /health");
    let v: serde_json::Value = serde_json::from_str(&body).expect("health body json");
    assert_eq!(v["status"], "ok", "health body shape");
}

// 2. Known user GET returns 200 + shape-correct body — primary read path
// against the user data store.
#[tokio::test]
async fn known_user_returns_200() {
    let Some(base) = base_url() else { return };
    let url = format!("{base}/users/{KNOWN_USER_ID}");
    let resp = client().get(&url).send().await.expect("GET /users/{id}");
    let status = resp.status();
    let cid = correlation(&resp).map(str::to_string);
    let body = resp.text().await.unwrap_or_default();
    dump("GET /users/{id}", status, &body, cid.as_deref());
    assert_eq!(status, StatusCode::OK, "GET /users/{KNOWN_USER_ID}");
    let v: serde_json::Value = serde_json::from_str(&body).expect("user body json");
    assert_eq!(v["id"].as_u64(), Some(KNOWN_USER_ID), "user id roundtrip");
    assert!(v["name"].is_string(), "user name field present");
}

// 3. Missing user GET returns 404 — proves the error path is wired (not a
// catch-all 500) and routing is intact.
#[tokio::test]
async fn missing_user_returns_404() {
    let Some(base) = base_url() else { return };
    let url = format!("{base}/users/{MISSING_USER_ID}");
    let resp = client().get(&url).send().await.expect("GET missing user");
    let status = resp.status();
    let cid = correlation(&resp).map(str::to_string);
    let body = resp.text().await.unwrap_or_default();
    dump("GET /users/{missing}", status, &body, cid.as_deref());
    assert_eq!(status, StatusCode::NOT_FOUND);
}

// 4. POST /orders without auth returns 401 — exercises the auth middleware
// path WITHOUT mutating state. The handler rejects before touching storage
// (see src/main.rs `create_order`: Bearer-prefix check precedes the lock),
// so this is safe to run against prod on every deploy.
#[tokio::test]
async fn create_order_without_auth_is_rejected() {
    let Some(base) = base_url() else { return };
    let url = format!("{base}/orders");
    let resp = client()
        .post(&url)
        .header("content-type", "application/json")
        .body(r#"{"user_id":1,"items":["smoke-probe"]}"#)
        .send()
        .await
        .expect("POST /orders");
    let status = resp.status();
    let cid = correlation(&resp).map(str::to_string);
    let body = resp.text().await.unwrap_or_default();
    dump("POST /orders no-auth", status, &body, cid.as_deref());
    assert_eq!(
        status,
        StatusCode::UNAUTHORIZED,
        "auth gate must reject before any state mutation"
    );
}

// 5. POST /orders with a deliberately invalid (non-Bearer) auth header
// returns 401 — same idempotency reasoning as #4. Confirms the prefix check
// is the gate, not just header presence.
#[tokio::test]
async fn create_order_with_invalid_auth_is_rejected() {
    let Some(base) = base_url() else { return };
    let url = format!("{base}/orders");
    let resp = client()
        .post(&url)
        .header("content-type", "application/json")
        .header("authorization", "NotBearer smoke-probe-invalid")
        .body(r#"{"user_id":1,"items":["smoke-probe"]}"#)
        .send()
        .await
        .expect("POST /orders bad scheme");
    let status = resp.status();
    let cid = correlation(&resp).map(str::to_string);
    let body = resp.text().await.unwrap_or_default();
    dump("POST /orders bad-scheme", status, &body, cid.as_deref());
    assert_eq!(status, StatusCode::UNAUTHORIZED);
}

// 6. Missing order GET returns 404 — read-only liveness probe against the
// orders store, parallel to the users-store check.
#[tokio::test]
async fn missing_order_returns_404() {
    let Some(base) = base_url() else { return };
    let url = format!("{base}/orders/{MISSING_ORDER_ID}");
    let resp = client().get(&url).send().await.expect("GET missing order");
    let status = resp.status();
    let cid = correlation(&resp).map(str::to_string);
    let body = resp.text().await.unwrap_or_default();
    dump("GET /orders/{missing}", status, &body, cid.as_deref());
    assert_eq!(status, StatusCode::NOT_FOUND);
}
