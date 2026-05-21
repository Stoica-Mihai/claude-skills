# Architectural review — `synthetic/`

I read every `.py` file in the tree (10 source files, plus 5 empty `__init__.py`s) and traced imports by hand. Below is what's structurally wrong, ordered by where I'd focus refactoring effort.

## Module dependency map

```
core/config.py        (leaf)
core/db.py            -> core.config
utils/helpers.py      (leaf, ~40 funcs)

models/user.py        -> models.order, utils.helpers       [cycle]
models/order.py       -> models.user,  utils.helpers       [cycle]
models/audit.py       -> utils.helpers

services/order_service.py        -> core.config, core.db,
                                    models.user, models.order, models.audit,
                                    utils.helpers
services/notification_service.py -> models.user, utils.helpers

handlers/order_handler.py        -> services.order_service, utils.helpers (unused)
handlers/user_handler.py         -> models.user, utils.helpers
handlers/notification_handler.py -> services.notification_service, utils.helpers
```

Fan-in counts (how many internal modules import each):
- `utils.helpers` — 9 importers (every non-leaf module)
- `models.user` — 4
- `models.order` — 2
- everything else — 1 or 0

## Where to focus, in priority order

### 1. Circular import: `models.user` <-> `models.order` (critical)

`models/user.py` imports `models.order`, and `models/order.py` imports `models.user`. They each instantiate the other (`User.orders()` calls `order.find_by_user`; `order.owner()` returns `User(...)`). Both files even carry docstrings that say `"Planted size-2 cycle"` — this is the most obvious red flag in the codebase.

Fix direction: pick the dominant aggregate (almost certainly `User`) and have `Order` reference a user only by `user_id` (string/int), not by importing the `User` class. If you need a `User` back from an order, that's a service/repository concern, not a model concern.

### 2. `utils/helpers.py` is a god module / hub (critical)

`helpers.py` contains ~40 unrelated functions: currency formatting, date parsing, slugify, retry, deep_merge, phone normalization, email validation, byte humanization, flatten, group_by, pick/omit, case conversions, env parsing, SHA-256 hashing, CSV escape, HTML escape, partition, windowing, etc. It is imported by every single non-leaf module in the system.

Two distinct problems sit on top of each other:
- **God module**: unrelated concerns share a file. Any change to formatting forces a re-read of hashing, retry policy, collection utilities, and HTML escape.
- **Hub dependency**: 9 modules touch it, so every edit has system-wide blast radius and the file is a magnet for unrelated future additions.

Fix direction: split by concern — `formatting.py` (currency/percent/bytes/dates), `strings.py` (case, slugify, escape, truncate), `collections.py` (chunk, flatten, group_by, pick/omit, partition, window), `hashing.py`, `validation.py` (email, phone), `env.py`. Then let callers depend on the narrow module they actually need. After the split, several callers will drop to zero `helpers` imports.

### 3. `services/order_service.py` has the highest fan-out (high)

It reaches into `core.config`, `core.db`, `models.user`, `models.order`, `models.audit`, and `utils.helpers` — and inside one function (`place_order`) it does all of: connect to DB, construct a `User` from raw fields, look up orders, write an audit event, sum prices, and format currency for the return value. That's at least four responsibilities in 7 lines, and the return value is a *display string* (`"$12.34"`), not a domain result.

Specific smells:
- `place_order` returns formatted currency — presentation logic in a service.
- `refund_order` reads `config.DEBUG` and prints — logging concern bleeding into business logic.
- `user.User(user_id, "buyer")` hardcodes a role string; the service is fabricating a user object instead of loading one.
- `db.connect()` is called but its return value is discarded; there is no transaction or connection object threaded through.

Fix direction: services should return domain values (a total as a number or `Money`), delegate formatting to the handler/presentation edge, take a real user via a repository, and log via a logger — not via `config.DEBUG` + `print`.

### 4. Layering is inconsistent (high)

The intended layers look like `handlers -> services -> models -> core`, but:
- `handlers/user_handler.py` skips services and constructs `models.user.User` directly. The other two handlers go through a service. Pick one and apply it consistently — handlers should not know about model constructors.
- `models/*` imports `utils/helpers` for presentation (`title_case`, `format_currency`). Models should hold identity/state; formatting belongs at the edges. This is what makes `helpers` a hub in the first place.
- `core/db.connect()` returns a config string. There's no real persistence boundary — the "core" layer is currently just a constants bag with a misleading function name.

### 5. Dead and misleading code (medium)

- `handlers/order_handler.py` imports `utils.helpers` and never uses it. Remove the import.
- `services/notification_service.py` constructs `user.User(user_id, "buyer")` then throws it away. Either look the user up properly or drop the import.
- `models/order.py::find_by_user` returns `[]` unconditionally; `models/audit.py::log` only hashes the dict and returns it. Names imply persistence/side effects that don't happen — easy source of false confidence when refactoring.
- `core/config.py` is three module-level constants with no environment-variable override and no type. `CACHE_TTL` isn't read anywhere in the tree.

### 6. `core/config.py` as mutable globals (low, but easy win)

Module-level `DEBUG = False` is the kind of flag that someone will eventually mutate at runtime or shadow with a monkeypatch in tests. Replace with a `Settings` object loaded from env (e.g. `pydantic-settings` or even a frozen dataclass) so the truth source is explicit and immutable per-process.

## Suggested order of attack

1. **Break the `user <-> order` cycle first.** Until that's gone, any other refactor in `models/` risks import-time surprises.
2. **Carve `utils/helpers.py` into focused modules.** This single change shrinks every other module's fan-out and makes layering violations visible (e.g. it'll be obvious that `models/*` shouldn't depend on `formatting`).
3. **Push presentation out of services.** Make `place_order` return a number; format at the handler. Remove `config.DEBUG`+`print` in favor of `logging`.
4. **Pick one entry pattern for handlers** (all go through services) and route `user_handler` through a `user_service`.
5. **Make `core/db` an actual boundary** (or delete `connect()` until it does something).
6. **Clean up dead imports and misleading stubs** as part of each touch — they're cheap, and they otherwise mislead the next person.

## Files to focus on, ranked

1. `utils/helpers.py` — god module, hub, blast radius 9
2. `models/user.py` + `models/order.py` — circular dependency (must be fixed together)
3. `services/order_service.py` — highest fan-out, mixes concerns, presentation in service layer
4. `handlers/user_handler.py` — inconsistent layering vs the other two handlers
5. `core/config.py` + `core/db.py` — weak boundary, mutable globals, no real persistence

The first three account for essentially all of the structural risk; the rest are cleanup that becomes easy once those land.
