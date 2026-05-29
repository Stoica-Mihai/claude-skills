# Template: Express + Vitest + supertest

Use for Express / Fastify / Koa with Vitest (or Jest — see notes) and
supertest for in-process HTTP. Same code works against a deployed URL
by swapping in `axios` / `undici` when `SMOKE_BASE_URL` is set.

## File location

`tests/smoke/smoke.test.js` (or `.test.ts`). Use `tests/smoke/` so the
runner picks the subset with `vitest run tests/smoke`.

## Imports + fixtures

```js
// tests/smoke/smoke.test.js
//
// Smoke tests — verify the build is stable enough to test further.
// Runtime budget: < 2 s in-process, < 30 s against a deployed URL.
//
// Run locally (in-process):    npx vitest run tests/smoke
// Run against an environment:  SMOKE_BASE_URL=https://api.example.com \
//                              SMOKE_TOKEN=eyJ... npx vitest run tests/smoke

import { describe, test, expect, beforeAll } from "vitest";
import request from "supertest";

const BASE_URL = process.env.SMOKE_BASE_URL || null;
const TOKEN = process.env.SMOKE_TOKEN || "smoke-token-placeholder"; // TODO

let agent;

beforeAll(async () => {
  if (BASE_URL) {
    agent = request(BASE_URL);
  } else {
    // TODO: update the import if the app object lives elsewhere.
    const mod = await import("../../src/index.js");
    agent = request(mod.app);
  }
});
```

## Body

```js
describe("smoke", () => {
  let createdOrderId;

  test("health returns 200", async () => {
    const r = await agent.get("/health");
    expect(r.status).toBe(200);
    expect(r.body.status).toBe("ok");
  });

  test("known user returns 200", async () => {
    const r = await agent.get("/users/1");
    expect(r.status).toBe(200);
    expect(r.body.id).toBe(1);
  });

  test("missing user returns 404", async () => {
    const r = await agent.get("/users/99999");
    expect(r.status).toBe(404);
  });

  test("create-order without auth returns 401", async () => {
    const r = await agent.post("/orders").send({ userId: 1, items: ["a"] });
    expect(r.status).toBe(401);
  });

  test("create-order happy path", async () => {
    const r = await agent
      .post("/orders")
      .set("authorization", `Bearer ${TOKEN}`)
      .send({ userId: 1, items: ["smoke-item"] });
    expect([200, 201]).toContain(r.status);
    expect(r.body.userId).toBe(1);
    createdOrderId = r.body.id;
  });

  test("get created order roundtrip", async () => {
    if (createdOrderId == null) return; // skip if write was skipped
    const r = await agent.get(`/orders/${createdOrderId}`);
    expect(r.status).toBe(200);
    expect(r.body.id).toBe(createdOrderId);
  });
});
```

## Notes

- Same code works under Jest with import-style tweaks (`import` →
  `require`).
- supertest's `request(app)` accepts the Express app object directly —
  no need to start a server.
- For TypeScript, change extension to `.test.ts` and ensure `vitest`
  has `tsconfig` paths sorted; nothing else changes.
- For Fastify, replace `request(app)` with `app.inject({...})` —
  Fastify ships its own in-process injection.
