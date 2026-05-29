# Template: Fastify + Vitest

Use for Fastify (with or without `@fastify/autoload`) using Vitest.
Runs in-process via Fastify's bundled `app.inject()` — no socket, no
network, sub-millisecond requests — or against a deployed URL via
`fetch` when `SMOKE_BASE_URL` is set.

## File location

`tests/smoke/smoke.test.js` (or `.ts`). Use `tests/smoke/` so the
runner picks the subset with `vitest run tests/smoke`.

## Body

```js
// tests/smoke/smoke.test.js
//
// Smoke tests — verify the build is stable enough to test further.
// Runtime budget: < 1 s in-process, < 30 s against a deployed URL.
//
// Run locally (in-process):    npx vitest run tests/smoke
// Run against an environment:  SMOKE_BASE_URL=https://api.example.com \
//                              SMOKE_TOKEN=eyJ... npx vitest run tests/smoke

import { describe, test, expect, beforeAll, afterAll } from "vitest";

const BASE_URL = process.env.SMOKE_BASE_URL || null;
const TOKEN = process.env.SMOKE_TOKEN || "smoke-token-placeholder"; // TODO

let app;

beforeAll(async () => {
  if (BASE_URL) return;
  // TODO: update if the build function lives elsewhere or is named differently.
  const mod = await import("../../src/app.js");
  app = typeof mod.build === "function" ? await mod.build() : mod.default;
  await app.ready();
});

afterAll(async () => {
  if (app) await app.close();
});

async function inject(opts) {
  if (BASE_URL) {
    const { method = "GET", url, headers = {}, payload } = opts;
    const r = await fetch(BASE_URL.replace(/\/$/, "") + url, {
      method,
      headers: { "content-type": "application/json", ...headers },
      body: payload != null ? JSON.stringify(payload) : undefined,
    });
    const text = await r.text();
    return {
      statusCode: r.status,
      json: () => (text ? JSON.parse(text) : null),
      payload: text,
    };
  }
  return app.inject(opts);
}

describe("smoke", () => {
  let createdId;

  test("health returns 200", async () => {
    const r = await inject({ url: "/health" });
    expect(r.statusCode).toBe(200);
    expect(r.json().status).toBe("ok");
  });

  test("known record returns 200", async () => {
    // TODO: replace /users/1 with a known seeded resource.
    const r = await inject({ url: "/users/1" });
    expect(r.statusCode).toBe(200);
  });

  test("missing record returns 404", async () => {
    const r = await inject({ url: "/users/999999" });
    expect(r.statusCode).toBe(404);
  });

  test("protected route requires auth", async () => {
    const r = await inject({
      method: "POST",
      url: "/orders",
      payload: { items: ["smoke"] },
    });
    expect(r.statusCode).toBe(401);
  });

  test("create-order happy path", async () => {
    const r = await inject({
      method: "POST",
      url: "/orders",
      headers: { authorization: `Bearer ${TOKEN}` },
      payload: { userId: 1, items: ["smoke"] },
    });
    expect([200, 201]).toContain(r.statusCode);
    createdId = r.json().id;
  });

  test("get created record roundtrip", async () => {
    if (createdId == null) return;
    const r = await inject({ url: `/orders/${createdId}` });
    expect(r.statusCode).toBe(200);
  });
});
```

## Notes

- `app.inject()` is Fastify's native in-process request mechanism. It
  exercises every plugin and hook without opening a socket — fastest
  option.
- The unified `inject()` helper hides whether the test is running
  in-process or against a URL; assertions stay identical.
- For Fastify projects that ship `src/app.ts` exporting a `build()`
  function, the fixture auto-detects it. Otherwise the default export
  is assumed to be the app instance.
- If the project uses `@fastify/swagger` and you want a smoke check
  that documents drift, add a 7th test: `inject({ url: "/docs/json" })`
  expecting 200 and a non-empty body.
