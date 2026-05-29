// tests/smoke/smoke.test.ts
//
// Smoke tests — verify the build is stable enough to test further.
// Runtime budget: < 1 s in-process, < 30 s against a deployed URL.
//
// Run locally (in-process):    npx vitest run tests/smoke
// Run against an environment:  SMOKE_BASE_URL=https://api.example.com \
//                              SMOKE_TOKEN=eyJ... npx vitest run tests/smoke

import { describe, test, expect, beforeAll, afterAll } from "vitest";
import type { FastifyInstance } from "fastify";

const BASE_URL = process.env.SMOKE_BASE_URL || null;
const TOKEN = process.env.SMOKE_TOKEN || "smoke-token-placeholder"; // TODO

let app: FastifyInstance | undefined;

beforeAll(async () => {
  if (BASE_URL) return;
  // TODO: update if the build function lives elsewhere or is named differently.
  const mod = await import("../../src/app");
  app = typeof mod.build === "function" ? await mod.build() : mod.default;
  await app!.ready();
});

afterAll(async () => {
  if (app) await app.close();
});

type InjectOpts = {
  method?: string;
  url: string;
  headers?: Record<string, string>;
  payload?: unknown;
};

type InjectResult = {
  statusCode: number;
  json: () => any;
  payload: string;
};

async function inject(opts: InjectOpts): Promise<InjectResult> {
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
  const r = await app!.inject(opts as any);
  return {
    statusCode: r.statusCode,
    json: () => r.json(),
    payload: r.payload,
  };
}

describe("smoke", () => {
  let createdId: string | number | undefined;

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
