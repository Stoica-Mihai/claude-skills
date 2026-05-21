# Where to focus your refactor

Ran the hotspot analyzer on the synthetic app (16 Python files, 20 internal import edges). No file is over the god-module LOC threshold, but three architectural problems stand out — in priority order:

## 1. `utils/helpers.py` — grab-bag hub (top priority)

- **Fan-in: 8** (every other top-level package depends on it) — by far the most depended-on file.
- **LOC: 151**, containing **~40 unrelated functions**: currency/percent formatting, date math, slugify, retry, deep_merge, phone/email validation, byte humanization, list flattening, case conversion, env parsing, sha256 hashing, CSV/HTML escaping, windowing, partitioning, predicates…

This is the textbook "grab-bag utils" smell: a generic name accumulating responsibilities because nobody knew where else to put them. Every module touches it, so the blast radius of any change is the whole app, and unrelated concerns share a change history.

**Suggestion:** split by domain into focused modules — e.g. `utils/formatting.py` (currency, percent, bytes, truncate, case), `utils/text.py` (slugify, html/csv escape, trim, normalize), `utils/collections.py` (chunk, flatten, group_by, partition, dedupe, window…), `utils/validation.py` (is_valid_email, is_blank, normalize_phone), `utils/runtime.py` (retry, env_bool, hash_dict, safe_get/deep_merge). Each becomes a small, cohesive hub that callers import only when they actually need it.

## 2. `services/order_service.py` — tangled coordinator

- **Fan-out: 6** (the highest in the repo, more than 3x the next file) reaching across **every layer**: `core.config`, `core.db`, `models.user`, `models.order`, `models.audit`, `utils.helpers`.
- Only 18 LOC, so it isn't huge yet — but it already orchestrates connection, user construction, order lookup, audit logging, totaling, and formatting in a single function.

It's the classic glue/service that knows about everything. As the app grows this will become the file that always breaks and always conflicts.

**Suggestion:** push responsibilities down. `User` should not be constructed by the service from a raw id — let `models.user` handle that. Audit logging belongs behind a decorator or an event the service emits, not inline calls. Currency formatting belongs at the presentation seam, not in the service return value. After that, this file should depend on `models` and an `audit` port only — fan-out drops to 2–3.

## 3. `models/user.py` <-> `models/order.py` — 2-cycle

- Strongly-connected component of size 2: `user.py` imports `order.find_by_user`; `order.py` imports `user.User` to return from `owner()`.

A size-2 cycle almost always means a missing seam — two modules share a concept that wants its own home. Here both files reach across the boundary purely to express the user<->order relationship.

**Suggestion:** invert the dependency. Move the `User.orders()` lookup out of the model (let callers query `order.find_by_user(user.id)` directly), and have `order.owner()` return a user id instead of constructing a `User`. That removes both edges and leaves the models as plain data with no cross-imports. If you'd rather keep rich navigation, extract a small `models/relations.py` that both depend on.

## Caveats on the analysis

- The repo is small (16 files); the analyzer is designed for ~30+ files, so treat the numeric rankings as directional rather than authoritative.
- Imports are resolved by relative path and basename match — fine for this layout, but path-aliased or dynamic imports would be undercounted.
- The graph is file-level: a god-class hiding inside a moderate-LOC file is invisible here.

Raw report (full tables, all four sections) is at `raw_report.md` in the same directory.
