import express from "express";

export const app = express();
app.use(express.json());

const users = new Map([
  [1, { id: 1, name: "alice" }],
  [2, { id: 2, name: "bob" }],
]);
const orders = new Map();
let nextOrderId = 1;

app.get("/health", (_req, res) => res.json({ status: "ok" }));

app.get("/users/:id", (req, res) => {
  const u = users.get(Number(req.params.id));
  if (!u) return res.status(404).json({ error: "user not found" });
  res.json(u);
});

app.post("/orders", (req, res) => {
  const auth = req.get("authorization") || "";
  if (!auth.startsWith("Bearer ")) return res.status(401).json({ error: "missing token" });
  const { userId, items } = req.body || {};
  if (!users.has(userId)) return res.status(400).json({ error: "unknown user" });
  const id = nextOrderId++;
  const order = { id, userId, items: items || [] };
  orders.set(id, order);
  res.status(201).json(order);
});

app.get("/orders/:id", (req, res) => {
  const o = orders.get(Number(req.params.id));
  if (!o) return res.status(404).json({ error: "order not found" });
  res.json(o);
});

if (import.meta.url === `file://${process.argv[1]}`) {
  const port = process.env.PORT || 3000;
  app.listen(port, () => console.log(`listening on ${port}`));
}
