import { describe, it, expect } from "vitest";
import request from "supertest";
import { app } from "../src/index.js";

// Fast deploy smoke test. Proves the app boots, routes are wired,
// auth gate works, and the basic happy path returns 2xx. ~10 requests, <1s.
describe("deploy smoke", () => {
  it("GET /health returns 200 ok", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });

  it("GET /users/:id returns a known user", async () => {
    const res = await request(app).get("/users/1");
    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({ id: 1, name: "alice" });
  });

  it("GET /users/:id 404s on unknown user", async () => {
    const res = await request(app).get("/users/9999");
    expect(res.status).toBe(404);
  });

  it("POST /orders rejects missing auth (401)", async () => {
    const res = await request(app)
      .post("/orders")
      .send({ userId: 1, items: ["a"] });
    expect(res.status).toBe(401);
  });

  it("POST /orders rejects unknown user (400)", async () => {
    const res = await request(app)
      .post("/orders")
      .set("Authorization", "Bearer test")
      .send({ userId: 9999, items: [] });
    expect(res.status).toBe(400);
  });

  it("POST /orders happy path creates an order, GET /orders/:id reads it back", async () => {
    const create = await request(app)
      .post("/orders")
      .set("Authorization", "Bearer test")
      .send({ userId: 1, items: ["widget"] });
    expect(create.status).toBe(201);
    expect(create.body).toMatchObject({ userId: 1, items: ["widget"] });
    expect(typeof create.body.id).toBe("number");

    const read = await request(app).get(`/orders/${create.body.id}`);
    expect(read.status).toBe(200);
    expect(read.body).toMatchObject({ id: create.body.id, userId: 1 });
  });

  it("GET /orders/:id 404s on unknown order", async () => {
    const res = await request(app).get("/orders/999999");
    expect(res.status).toBe(404);
  });
});
