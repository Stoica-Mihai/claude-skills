# Template: Rust / axum + tokio test + tower::ServiceExt

Use for axum services. The same pattern works for other tower-based
Rust frameworks (warp, tide) with minimal adjustment. Runs in-process
by driving the router as a `tower::Service`, or against a deployed URL
when `SMOKE_BASE_URL` is set via `reqwest`.

## File location

`tests/smoke.rs` — the `tests/` directory at crate root runs as
integration tests via `cargo test`. Add `cargo test --test smoke` to
run smoke alone.

## Cargo.toml dev-dependencies

```toml
[dev-dependencies]
tokio = { version = "1", features = ["macros", "rt-multi-thread"] }
tower = { version = "0.4", features = ["util"] }
http-body-util = "0.1"
serde_json = "1"
reqwest = { version = "0.12", optional = true }   # only if you hit deployed URLs
```

## Body

```rust
// tests/smoke.rs
//
// Smoke tests — verify the build is stable enough to test further.
// Runtime budget: < 2 s in-process.
//
// Run locally (in-process):    cargo test --test smoke
// Run against an environment:  SMOKE_BASE_URL=https://api.example.com \
//                              SMOKE_TOKEN=eyJ... cargo test --test smoke

use axum::{
    body::{Body, to_bytes},
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use tower::ServiceExt;

// TODO: update to your crate name + router constructor.
use axum_app::router;

const TOKEN: &str = "smoke-token-placeholder"; // TODO: pull from env in CI

async fn call(req: Request<Body>) -> (StatusCode, Vec<u8>) {
    let resp = router().oneshot(req).await.unwrap();
    let status = resp.status();
    let bytes = to_bytes(resp.into_body(), 64 * 1024).await.unwrap().to_vec();
    (status, bytes)
}

#[tokio::test]
async fn health_returns_ok() {
    let req = Request::builder().uri("/health").body(Body::empty()).unwrap();
    let (status, body) = call(req).await;
    assert_eq!(status, StatusCode::OK);
    let v: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(v["status"], "ok");
}

#[tokio::test]
async fn known_user_returns_200() {
    let req = Request::builder().uri("/users/1").body(Body::empty()).unwrap();
    let (status, _) = call(req).await;
    assert_eq!(status, StatusCode::OK);
}

#[tokio::test]
async fn missing_user_returns_404() {
    let req = Request::builder().uri("/users/99999").body(Body::empty()).unwrap();
    let (status, _) = call(req).await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn create_order_requires_auth() {
    let body = Body::from(r#"{"user_id":1,"items":["a"]}"#);
    let req = Request::builder()
        .method("POST")
        .uri("/orders")
        .header("content-type", "application/json")
        .body(body)
        .unwrap();
    let (status, _) = call(req).await;
    assert_eq!(status, StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn create_order_happy_path() {
    let body = Body::from(r#"{"user_id":1,"items":["smoke-item"]}"#);
    let req = Request::builder()
        .method("POST")
        .uri("/orders")
        .header("content-type", "application/json")
        .header("authorization", format!("Bearer {}", TOKEN))
        .body(body)
        .unwrap();
    let (status, raw) = call(req).await;
    assert!(
        status == StatusCode::CREATED || status == StatusCode::OK,
        "POST /orders = {}", status
    );
    let order: serde_json::Value = serde_json::from_slice(&raw).unwrap();
    let id = order["id"].as_u64().expect("missing order id");

    let req2 = Request::builder()
        .uri(format!("/orders/{}", id))
        .body(Body::empty())
        .unwrap();
    let (status2, raw2) = call(req2).await;
    assert_eq!(status2, StatusCode::OK);
    let roundtrip: serde_json::Value = serde_json::from_slice(&raw2).unwrap();
    assert_eq!(roundtrip["id"], id);
}
```

## Notes

- The `router().oneshot(req)` pattern is the canonical axum in-process
  test. It exercises every middleware layer and uses no network.
- For "smoke against a deployed URL" use `reqwest::Client` instead of
  `oneshot` — same assertions, same shape — and gate it behind
  `SMOKE_BASE_URL`.
- The example uses a single `router()` per test for clarity. If your
  router holds expensive state, build it once in a `static` `OnceCell`
  and share it.
- Adapt `to_bytes(..., 64 * 1024)` ceiling if your endpoints return
  larger payloads.
