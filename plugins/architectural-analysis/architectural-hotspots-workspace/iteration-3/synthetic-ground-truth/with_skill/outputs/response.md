# Where to focus the refactor

Ran the architectural-hotspots analyzer on the app. 16 source files, 20 internal import edges — small enough that you could read the structure by hand, but the report still surfaces three things worth your attention. In rough priority order:

## 1. `utils/helpers.py` — grab-bag hub (LOC 151, fan-in 8)

This is the highest-impact target. It is the most-imported file in the repo (8 of the other ~15 files depend on it) and its contents are a textbook "miscellaneous junk drawer": ~40 unrelated utilities mixing currency formatting, date math, string casing, HTML/CSV escaping, dict merging, list partitioning, env-var parsing, hashing, retry logic, and more. None of these things belong together; they accumulated here because the name `helpers` invited it.

It does not cross the 400-LOC god-module threshold, but the skill explicitly calls out generic/grab-bag naming (`utils.py`, `helpers.ts`, `common.go`) as the disqualifier even at modest size — a hub with a name that means nothing is a hub that will keep growing and ripple changes across the whole repo on every touch.

**Suggestion:** split by domain. The obvious cuts: `formatting.py` (currency, percent, bytes, truncate, html/csv escape, casing), `collections.py` (chunk, flatten, group_by, partition, window, dedupe, pick/omit, first/coalesce), `text.py` (slugify, normalize_phone, is_valid_email, is_blank, title/camel/snake_case), `time.py` (parse_iso_date, days_between, hours_between), `runtime.py` (retry, env_bool, hash_dict, safe_get, deep_merge). Anything used by only one caller can move next to that caller.

## 2. `services/order_service.py` — coordination tangle (LOC 18, fan-out 6)

Highest fan-out in the repo. In 18 lines this file reaches into `core.config`, `core.db`, all three models (`user`, `order`, `audit`), and `helpers`. It is the only true cross-layer orchestrator in the codebase. Right now it is tiny, but the *shape* — one function (`place_order`) instantiating models, calling the DB, writing audit logs, and formatting output — is the shape of a future god service. The skill notes high fan-out is "a sign of weak single-responsibility… a coordination layer that should be split."

**Suggestion:** before it grows, push the cross-cutting concerns out. Audit logging should be a decorator or an event listener, not an inline `audit.log({...})` call repeated in every action. Currency formatting belongs in the response/serializer layer, not in the service. That leaves the service doing one thing: orchestrating the domain step.

## 3. Cycle between `models/user.py` and `models/order.py`

A size-2 strongly-connected component. `user.py` imports `order` (to expose `user.orders()`) and `order.py` imports `user` (to expose `order.owner()`). Per the skill's rule of thumb, size-2 cycles are usually a missing seam — a shared concept that wants its own home.

**Suggestion:** break the cycle by extracting the lookup direction one of them is reaching for. Move `find_by_user` and `owner` into a small `repositories/` (or `queries/`) module that both models can call into without the models needing to know about each other. Models stay as data + behavior on themselves; cross-aggregate lookups live one layer up.

---

## What is NOT a problem (yet)

- `core/config.py`, `core/db.py`, `models/audit.py` are hubs but tiny and focused. Leave them alone.
- No file exceeds the 400-LOC god-module threshold. Size isn't your problem; *naming and responsibility distribution* is.

## Caveats on the report

- The analyzer resolves imports by relative path and basename match. Python `from models import order` style is handled, but any dynamic imports, string-based `importlib`, or aliasing would be invisible.
- 16 files is below the analyzer's recommended ~30-file scale, so a couple of these signals (especially the size-2 cycle and the modest fan-out numbers) might look more dramatic on a small repo than they really are. The `helpers.py` finding is the one I'd act on regardless of repo size.
- File-level graph only — a god class buried inside a moderate-sized file would not show up here. (Not the case in this repo, but worth knowing for future analyses.)

Raw report: `architectural-hotspots-workspace/iteration-3/synthetic-ground-truth/with_skill/outputs/raw_report.md`.
