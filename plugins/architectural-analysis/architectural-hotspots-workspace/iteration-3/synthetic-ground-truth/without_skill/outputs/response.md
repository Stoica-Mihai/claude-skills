# Architectural review: `synthetic/` app

Quick read of the tree (16 files, ~275 LOC) plus every module read top-to-bottom. The codebase is tiny, but the way it's wired has several clear architectural problems. Focus areas are listed in priority order — top of the list is what to refactor first.

---

## 1. `utils/helpers.py` is a god-module / junk drawer (HIGHEST PRIORITY)

This is by far the biggest architectural smell. 193 lines / ~46 unrelated functions in a single file. For context, the *entire rest of the app* is ~80 LOC — so this one module is ~70% of the code.

The functions are doing wildly different things, with no cohesion:

- Formatting: `format_currency`, `format_percent`, `humanize_bytes`, `truncate`, `title_case`, `camel_case`, `snake_case`, `slugify`
- Date/time: `parse_iso_date`, `days_between`, `hours_between`
- Validation: `is_valid_email`, `is_blank`, `normalize_phone`
- Collection ops: `chunk`, `flatten`, `group_by`, `dedupe`, `partition`, `take`, `drop`, `window`, `split_chunks`, `find_index`, `count_if`, `any_match`, `all_match`, `first`, `zip_longest_fill`
- Dict ops: `safe_get`, `deep_merge`, `pick`, `omit`, `coalesce`
- Control flow: `retry`
- Environment / hashing: `env_bool`, `hash_dict`
- Encoding: `csv_escape`, `html_escape`, `trim_lines`

This is the classic "Utils god class" anti-pattern. **Every other module in the codebase imports it** (`models/user.py`, `models/order.py`, `models/audit.py`, `services/*`, `handlers/*`) — so it's also the most coupled file in the project. Any change here can ripple everywhere; it'll be a constant merge-conflict magnet as the team grows.

Imports are also inlined inside several functions (`parse_iso_date`, `snake_case`, `env_bool`, `hash_dict`) which is a smell on its own — it suggests the module grew by accretion, with people avoiding top-level imports to dodge load-time cost or to "keep it light." Real fix is to split the module.

**Refactor target:** break it into focused modules under `utils/` (or better, push them to the layer that owns them): `formatting.py`, `dates.py`, `validation.py`, `collections.py`, `dicts.py`, `text.py`, `retry.py`, `env.py`, `hashing.py`. A lot of these (e.g. `partition`, `flatten`, `first`, `count_if`) are also reinventing `itertools` / `more_itertools` and could just be deleted.

Several functions also look unused inside this repo (`window`, `zip_longest_fill`, `split_chunks`, `humanize_bytes`, `find_index`, `csv_escape`, `html_escape`, `trim_lines`, …) — worth grepping for callers and dropping dead code before refactoring.

---

## 2. Circular / bidirectional dependency between `models/user.py` and `models/order.py`

```
models/user.py     -> from models import order
models/order.py    -> from models import user
```

Both modules import each other at module top-level. Today it works only because Python tolerates partial-module imports when neither side touches the other's attributes at import time — but the moment anyone adds a top-level call (`user.User(...)` at module scope in `order.py`, etc.) this will break with an `ImportError` or `AttributeError`. It's a latent landmine.

It's also a real architectural smell: `User.orders()` calls `order.find_by_user`, and `order.owner()` returns a `user.User`. Those two modules are effectively one bounded context pretending to be two.

**Fix options:**
- Move the cross-referencing functions into a service layer (`services/`), keeping the model modules pure data.
- Or use `TYPE_CHECKING`-guarded imports and lazy-import the cross-reference at function-call time.
- Or merge into a single `models/domain.py` if they really are one aggregate.

---

## 3. Same circular pattern between `services/notification_service.py` and `models/user.py`

`notification_service.notify` constructs a `user.User(user_id, "buyer")` with a hardcoded `"buyer"` name (clearly a stand-in for a real lookup). Meanwhile `user.User` imports `helpers` and calls `helpers.title_case` in `__init__`. Same architectural shape as #2 — services reaching into models and constructing them with placeholder data is a smell that the model layer is anemic and there's no proper repository / lookup abstraction.

This shows up again in `services/order_service.place_order`:

```python
u = user.User(user_id, "buyer")        # fake name
o = order.find_by_user(u.id)           # result discarded
```

`o` is computed and thrown away. The whole function is structured as "instantiate fake objects, do nothing with them, return a formatted total." That suggests this is placeholder code, but the *architecture* it implies (services manually constructing model objects with literals) is what to push back on during refactor — introduce a `UserRepository` / `OrderRepository`.

---

## 4. Layering violations — models reaching "up" into utils, handlers skipping services

Two related issues:

**(a) Models depend on `utils/helpers`.** `models/user.py`, `models/order.py`, and `models/audit.py` all import `helpers`. In a clean layered architecture, models are the innermost layer and shouldn't depend on a cross-cutting utility grab-bag; formatting belongs in the presentation/handler layer, not in `User.__init__`. Concretely, `User.__init__` calling `title_case(name)` means *every* code path that constructs a User mutates the input — including `notification_service.notify` which passes the literal `"buyer"`. That's a behavior change hidden in a constructor.

**(b) Handlers bypass services.** `handlers/user_handler.handle_create` calls `user.User(...)` directly, bypassing any service layer. `handlers/notification_handler.handle_send` calls `helpers.truncate(req["message"], 200)` *before* handing off to `notification_service.notify`, which then truncates *again* to 140. So the message gets double-truncated and the handler is doing business-logic work that should live in the service. Either everything funnels through services, or the service layer is redundant — pick one.

---

## 5. `core/config.py` is a global-mutable-state singleton

```python
DEBUG = False
DB_URL = "postgres://localhost/app"
CACHE_TTL = 60
```

Module-level constants imported everywhere (`core/db.py`, `services/order_service.py`). Issues:

- No environment-variable loading — the DB URL is hardcoded to localhost; production will need code changes.
- `CACHE_TTL` defined but unused anywhere in the codebase — dead config.
- `services/order_service.refund_order` does `if config.DEBUG: print(...)` — using `print` for diagnostics and a global flag for log levels is exactly what `logging` exists to solve.
- Anything that imports `config` is now untestable without monkey-patching the module.

**Fix:** a `Settings` dataclass loaded from env (e.g. `pydantic-settings`), injected where needed. Replace `print` + `DEBUG` with the `logging` module.

---

## 6. `core/db.connect()` is a stub that returns a string

```python
def connect():
    return config.DB_URL
```

`order_service.place_order` calls `db.connect()` and discards the result. There's no actual connection pool, session, or transaction abstraction. If this app is intended to do anything real with a database, the entire persistence layer is missing and needs to be designed deliberately (SQLAlchemy session / repository pattern / unit-of-work) rather than bolted on later module-by-module.

---

## 7. Cross-cutting concerns are scattered and ad-hoc

- **Logging:** `print` in `order_service`, return-the-hash-of-the-event in `audit.log` (which doesn't log anywhere, just hashes and returns), nothing else. No consistent observability story.
- **Audit:** `models/audit.log` is called from `order_service` with dict literals — event schema lives nowhere, format will drift. Plus, audit is in `models/` despite being a side-effecting infrastructure concern, not a domain entity.
- **Error handling:** `helpers.retry` exists but is never called. Nothing in the services has any try/except. When the DB or notification layer is filled in, error handling will need to be designed; right now there's nothing.
- **Validation:** `is_valid_email`, `normalize_phone` exist but nothing in handlers actually validates the request payloads (`req["user"]`, `req["items"]`, `req["message"]` — all blind dict access, will `KeyError` on bad input).

---

## Recommended order of attack

1. **Split `utils/helpers.py`** — biggest single architectural win, unblocks everything else by reducing cross-module coupling. Delete dead helpers while you're in there.
2. **Break the model-layer import cycles** (`user` <-> `order`, `notification_service` <-> `user`) by introducing repositories or lazy imports. Move `title_case` out of `User.__init__`.
3. **Decide on the service/handler boundary** and stop handlers from constructing models or pre-processing payloads.
4. **Replace `core/config.py`** with a proper `Settings` object loaded from env; introduce `logging`; drop the `DEBUG`/`print` pattern.
5. **Design the persistence layer** properly (or remove `db.connect` until you do).
6. **Pick a cross-cutting story** for audit/logging/validation/retry before the codebase grows.

The "small Python app" framing is a little misleading — the code itself is small, but the *shape* it's establishing (god-module utils, bidirectional model imports, services constructing models with literals, handlers bypassing services, module-level config) is the shape that scales badly. Fixing it now while it's 275 LOC is a lot cheaper than fixing it at 27,500.
