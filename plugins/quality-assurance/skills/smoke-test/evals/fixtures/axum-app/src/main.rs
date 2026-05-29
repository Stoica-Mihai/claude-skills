use axum::{
    extract::{Path, State},
    http::{HeaderMap, StatusCode},
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, sync::Arc};
use tokio::sync::Mutex;

#[derive(Clone, Serialize)]
struct User {
    id: u64,
    name: String,
}

#[derive(Clone, Serialize)]
struct Order {
    id: u64,
    user_id: u64,
    items: Vec<String>,
}

#[derive(Deserialize)]
struct OrderIn {
    user_id: u64,
    items: Vec<String>,
}

#[derive(Default)]
struct AppState {
    users: HashMap<u64, User>,
    orders: HashMap<u64, Order>,
    next_id: u64,
}

type Shared = Arc<Mutex<AppState>>;

async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({"status": "ok"}))
}

async fn get_user(State(state): State<Shared>, Path(id): Path<u64>) -> Result<Json<User>, StatusCode> {
    let s = state.lock().await;
    s.users.get(&id).cloned().map(Json).ok_or(StatusCode::NOT_FOUND)
}

async fn create_order(
    State(state): State<Shared>,
    headers: HeaderMap,
    Json(input): Json<OrderIn>,
) -> Result<(StatusCode, Json<Order>), StatusCode> {
    let auth = headers.get("authorization").and_then(|v| v.to_str().ok()).unwrap_or("");
    if !auth.starts_with("Bearer ") {
        return Err(StatusCode::UNAUTHORIZED);
    }
    let mut s = state.lock().await;
    if !s.users.contains_key(&input.user_id) {
        return Err(StatusCode::BAD_REQUEST);
    }
    s.next_id += 1;
    let id = s.next_id;
    let order = Order { id, user_id: input.user_id, items: input.items };
    s.orders.insert(id, order.clone());
    Ok((StatusCode::CREATED, Json(order)))
}

async fn get_order(State(state): State<Shared>, Path(id): Path<u64>) -> Result<Json<Order>, StatusCode> {
    let s = state.lock().await;
    s.orders.get(&id).cloned().map(Json).ok_or(StatusCode::NOT_FOUND)
}

pub fn router() -> Router {
    let mut state = AppState::default();
    state.users.insert(1, User { id: 1, name: "alice".into() });
    state.users.insert(2, User { id: 2, name: "bob".into() });
    let shared: Shared = Arc::new(Mutex::new(state));

    Router::new()
        .route("/health", get(health))
        .route("/users/:id", get(get_user))
        .route("/orders", post(create_order))
        .route("/orders/:id", get(get_order))
        .with_state(shared)
}

#[tokio::main]
async fn main() {
    let listener = tokio::net::TcpListener::bind("0.0.0.0:8080").await.unwrap();
    axum::serve(listener, router()).await.unwrap();
}
