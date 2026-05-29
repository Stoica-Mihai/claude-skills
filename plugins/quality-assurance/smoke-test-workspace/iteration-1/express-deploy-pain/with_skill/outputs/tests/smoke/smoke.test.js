// tests/smoke/smoke.test.js
//
// Smoke tests for express-app — verify the build is stable enough for QA to bother.
// Scope: broad + shallow. NOT a regression suite.
// Runtime budget: < 2 s in-process, < 30 s against a deployed URL.
//
// Run locally (in-process):
//   npx vitest run tests/smoke
//
// Run against a deployed env:
//   SMOKE_BASE_URL=https://api.example.com \
//   SMOKE_TOKEN=eyJ... \
//   npx vitest run tests/smoke
//
// Failure policy: a red smoke run is a stop-the-line event. Do NOT promote the
// build, do NOT hand off to QA. Capture the response body + status from the
// failing assertion (vitest prints both) and route to the on-call channel.

import { describe, test, expect, beforeAll } from "vitest";
import request from "supertest";

const BASE_URL = process.env.SMOKE_BASE_URL || null;
const TOKEN = process.env.SMOKE_TOKEN || "smoke-token-placeholder"; // TODO: real token for deployed runs
const KNOWN_USER_ID = Number(process.env.SMOKE_USER_ID || 1);       // TODO: known-good user in target env

let agent;

beforeAll(async () => {
  if (BASE_URL) {
    agent = request(BASE_URL);
  } else {
    const mod = await import("../../src/index.js");
    agent = request(mod.app);
  }
});

describe("smoke", () => {
  let createdOrderId;

  // 1. liveness — service is up and responding
  test("GET /health returns 200 + {status: ok}", async () => {
    const r = await agent.get("/health");
    expect(r.status).toBe(200);
    expect(r.body).toMatchObject({ status: "ok" });
  });

  // 2. primary read — known fixture round-trips
  test("GET /users/:id returns the known user", async () => {
    const r = await agent.get(`/users/${KNOWN_USER_ID}`);
    expect(r.status).toBe(200);
    expect(r.body.id).toBe(KNOWN_USER_ID);
    expect(typeof r.body.name).toBe("string");
  });

  // 3. error path — 404 wired up correctly
  test("GET /users/99999 returns 404", async () => {
    const r = await agent.get("/users/99999");
    expect(r.status).toBe(404);
  });

  // 4. auth gate — write endpoint rejects missing token
  test("POST /orders without auth returns 401", async () => {
    const r = await agent.post("/orders").send({ userId: KNOWN_USER_ID, items: ["x"] });
    expect(r.status).toBe(401);
  });

  // 5. primary write — happy path with auth creates a record
  test("POST /orders with bearer creates an order", async () => {
    const r = await agent
      .post("/orders")
      .set("authorization", `Bearer ${TOKEN}`)
      .send({ userId: KNOWN_USER_ID, items: ["smoke-item"] });
    expect([200, 201]).toContain(r.status);
    expect(r.body.userId).toBe(KNOWN_USER_ID);
    expect(typeof r.body.id).toBe("number");
    createdOrderId = r.body.id;
  });

  // 6. read-after-write — the record we just created is retrievable
  test("GET /orders/:id round-trips the created order", async () => {
    if (createdOrderId == null) {
      throw new Error("create-order step did not produce an id; cannot verify roundtrip");
    }
    const r = await agent.get(`/orders/${createdOrderId}`);
    expect(r.status).toBe(200);
    expect(r.body.id).toBe(createdOrderId);
    expect(r.body.userId).toBe(KNOWN_USER_ID);
  });
});
