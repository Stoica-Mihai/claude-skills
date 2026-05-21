# Architectural Review — `synthetic/`

## Scope
16 files, ~275 lines, layout:

```
core/       config.py, db.py
handlers/   user_handler.py, order_handler.py, notification_handler.py
services/   order_service.py, notification_service.py
models/     user.py, order.py, audit.py
utils/      helpers.py
```

Intent appears to be a classic layered architecture: `handlers -> services -> models -> core`, with `utils` cross-cutting. Reality diverges from that intent in several load-bearing ways.

## Where to focus (ranked)

### 1. `models/user.py` <-> `models/order.py` — circular import between models (highest priority)

- `models/user.py` imports `models.order` to expose `User.orders()`.
- `models/order.py` imports `models.user` to expose `order.owner()` returning a `User`.

This is a true module-level cycle inside the *same* layer. It will:
- Surface as `ImportError`/half-initialized modules the moment one is imported before the other in a new context (tests, scripts, workers).
- Block any attempt to extract `models/` into its own package or split files further.
- Cause subtle bugs where `user.User` is partially defined when `order` first resolves it.

Fix direction: move the relationship traversal out of the model classes. Either (a) introduce a `repository` / `service` layer that joins `User` and `Order`, or (b) keep one direction only (e.g. `Order.owner_id` as a plain id, lookup done by caller). The `notification_service` and `order_service` already need this — they're the natural home.

### 2. `utils/helpers.py` — God module / kitchen-sink utility (highest blast radius)

- 192 lines, ~40 unrelated functions: currency formatting, date math, retry, deep_merge, html_escape, csv_escape, hash_dict, env_bool, slugify, snake_case, chunk/window/partition, etc.
- Imported by *every* other non-`core` module: `models/user`, `models/order`, `models/audit`, `services/order_service`, `services/notification_service`, `handlers/user_handler`, `handlers/order_handler`, `handlers/notification_handler`.
- Mixes concerns that should not share a module: formatting, validation, collection algorithms, crypto/hashing, env/config access, HTML/CSV escaping.
- Several functions reach into env (`env_bool`) or do crypto (`hash_dict`) — these are not "helpers", they're side-effectful infra.
- `retry()` swallows exceptions and re-raises the last one, but `last` starts as `None` — if `attempts <= 0` it'll raise `None`. Latent bug.

Fix direction: split by concern. Suggested first cut:
- `utils/formatting.py` — currency, percent, title_case, camel_case, snake_case, truncate, humanize_bytes
- `utils/text.py` — html_escape, csv_escape, slugify, trim_lines, is_blank
- `utils/collections.py` — chunk, flatten, group_by, partition, dedupe, window, take, drop, find_index, count_if, any/all_match, first, coalesce, zip_longest_fill, split_chunks
- `utils/dictutil.py` — safe_get, deep_merge, pick, omit, hash_dict
- `utils/dates.py` — parse_iso_date, days_between, hours_between
- `utils/validation.py` — is_valid_email, normalize_phone
- `core/env.py` — env_bool (it's config, not a helper)
- `core/retry.py` — retry (and fix the empty-attempts bug)

This single change cuts the fan-in on `utils.helpers` from 8 modules to roughly 1-2 per split file, which is the biggest architectural-coupling win available.

### 3. Layer-violation: `models/` imports `utils.helpers`

- `models/user.py` calls `helpers.title_case` inside `__init__` to mutate the name.
- `models/order.py` calls `helpers.format_currency` inside `total()`.
- `models/audit.py` calls `helpers.hash_dict`.

Domain models should not depend on presentation/formatting helpers. `format_currency` belongs in a view/serializer; the model should store an amount. `title_case` is also presentation — and worse, it's applied silently in the constructor, so the stored `name` is no longer what the caller passed in (lossy mutation).

Fix direction: keep models as plain data + invariants. Move formatting to handler/serializer layer. `User.__init__` should store `name` verbatim (or validate it), not transform it.

### 4. `User.__init__` signature mismatch (real bug, follows from #3)

- Definition: `User(self, id, name)`.
- `services/order_service.place_order`: `user.User(user_id, "buyer")` — passes the literal string `"buyer"` as the name.
- `services/notification_service.notify`: same — `user.User(user_id, "buyer")`.
- `handlers/user_handler.handle_create`: passes the real name from the request.
- `models/order.owner`: `user.User(1, "alice")` — hardcoded.

So `User` is being constructed as both "a named user from a request" and "a placeholder with role-as-name" from inside services. The second argument is being abused. This is a symptom of missing repository/lookup: services should be *fetching* users, not minting fake ones.

### 5. Service layer is anemic and bypasses itself

- `order_service.place_order` constructs a fake `User`, ignores `o = order.find_by_user(...)` (return value discarded), sums prices itself, returns a *formatted string*. It does no persistence, no validation, no transaction.
- `cancel_order` / `refund_order` only call `audit.log` and return `True` — no state change.
- `notification_service.notify` builds a throwaway `User` it doesn't use, then just truncates the message.
- `order_handler.handle_send` already truncates the message to 200, then `notification_service.notify` truncates again to 140 — duplicated, inconsistent truncation logic split across layers.

These services aren't doing service work; handlers could call models directly with the same result. Either flesh out the service layer (transactions, validation, orchestration) or collapse it. Don't keep a layer that adds only indirection.

### 6. `core/db.connect()` doesn't connect

- It returns the URL string. No connection object, no pool, no lifecycle. `order_service.place_order` calls it and discards the result.

This is a stub, but it's a stub at the foundation, so every service that "uses the DB" is actually using nothing. Worth flagging because refactoring services without a real DB boundary will mislead you about coupling.

### 7. Cross-cutting `audit.log` called ad-hoc from services

`audit.log` is invoked inline in `place_order`, `cancel_order`, `refund_order`. It's not wrapped, not transactional with the operation, and its return value (a hash) is discarded. If audit matters, it belongs in a decorator or middleware around service calls, not as scattered inline calls that are easy to forget.

## Suggested refactor order

1. Break the `user <-> order` model cycle (#1) — unblocks everything else.
2. Split `utils/helpers.py` by concern (#2) — biggest decoupling win, mechanical, low-risk.
3. Remove `helpers` usage from `models/` and stop mutating fields in `__init__` (#3, #4).
4. Decide: flesh out or delete the service layer (#5).
5. Replace `core/db.connect()` stub with a real boundary, then revisit service responsibilities (#6).
6. Move `audit.log` to a decorator/middleware (#7).

## TL;DR

Two architectural hotspots dominate:
- `utils/helpers.py` — God module, fan-in from 8 of the 10 non-init source files.
- `models/user.py` <-> `models/order.py` — same-layer circular import.

Everything else (anemic services, layer violations into utils, the `User("buyer")` abuse, the `db.connect()` stub) is a downstream symptom of those two plus a missing repository concept between models and services.
