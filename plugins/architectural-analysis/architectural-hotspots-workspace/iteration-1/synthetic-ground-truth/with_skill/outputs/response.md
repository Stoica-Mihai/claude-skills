# Architectural hotspots in `synthetic/`

Ran the hotspot analyzer over the 16 source files (20 internal import edges). The app is small enough that the picture is clear — there are three things worth focusing on before you start moving code around, in priority order.

## 1. `utils/helpers.py` — grab-bag hub (fan-in 8, LOC 152)

This is the single most architecturally problematic file. It is:

- **The top hub by a wide margin** (fan-in 8 out of 16 files — half the codebase imports it).
- **Generically named** (`helpers`), which is the classic warning sign the SKILL.md flags: when a file is called `helpers`/`utils`/`common`, dependents accumulate not because they share a real abstraction, but because nobody knew where else to put things.
- **A grab-bag in practice**, not just in name. Skimming it, the responsibilities are wildly mixed — currency/percent formatting, date math, slugify, retry, deep_merge, phone normalization, email validation, byte humanization, flatten, group_by, pick/omit, case conversion, env parsing, hash/csv/html escaping, list windowing, etc. Roughly 40 unrelated utilities in one file.

It does not cross the god-module LOC threshold (152 < 400), but the *blast radius* metric matters more than raw size: every one of those 8 importers is coupled to a file whose contents have nothing to do with each other.

**Suggestion:** split by domain rather than refactoring in place. Reasonable seams visible in the file: `formatting/` (currency, percent, bytes, title/camel/snake_case, truncate, csv/html escape), `datetime_utils.py` (parse_iso_date, days_between, hours_between), `collections_utils.py` (chunk, flatten, group_by, pick, omit, dedupe, partition, window, zip_longest_fill, take/drop, find_index, count_if, any_match, all_match, first, coalesce), `validation.py` (is_valid_email, is_blank, normalize_phone), `retry.py`, `config_env.py` (env_bool), `hashing.py` (hash_dict). Once split, each importer pulls in only what it actually uses, and the hub disappears.

## 2. `services/order_service.py` — coordination tangle (fan-out 6)

Top of the tangles table. In a 19-line file it reaches into `core.config`, `core.db`, `models.user`, `models.order`, `models.audit`, and `utils.helpers` — basically every layer of the app. The functions are also doing mixed-level work: `place_order` opens a DB connection, constructs a domain object, queries orders, writes an audit event, computes a sum, and formats currency for return — all in one body.

The fan-out is not large in absolute terms, but it is large *relative to the size of the repo* — this one file touches ~38% of the source files. That makes it the obvious "coordinator that does too much" candidate.

**Suggestion:** introduce a seam. Either (a) pull the DB connection / audit logging out behind a small unit-of-work or context object that `place_order` receives, so the service stops importing `core.db` and `models.audit` directly; or (b) split the service into an orchestrator (`place_order`, `cancel_order`, `refund_order` as thin top-level functions) plus per-step helpers, so each step owns its imports. Either way the return type also wants attention — returning a formatted currency string out of `place_order` mixes presentation into the service layer.

## 3. Cycle between `models/user.py` and `models/order.py` (size 2)

The analyzer found one strongly-connected component: `user.py` imports `order.py` (so `User.orders()` can call `order.find_by_user`) and `order.py` imports `user.py` (so `order.owner` can return a `User`). Per the SKILL.md guidance, size-2 cycles almost always mean **a missing seam** — there's a shared concept that wants its own module.

**Suggestion:** the cleanest extraction is usually a query/repository layer: move `find_by_user` and `owner` into a `models/queries.py` (or `repositories/`) that depends on both `user` and `order`, leaving `user.py` and `order.py` as pure data definitions that don't know about each other. Alternatively, invert one of the two — e.g. have `User.orders()` accept a callable or repository at construction time rather than importing `order` at module top level.

## What I am *not* flagging

- **No god modules.** Nothing in the repo crosses the 400-LOC threshold. `helpers.py` at 152 LOC is the largest file and even that is only a "hub problem", not a "size problem".
- **`models/user.py`, `models/order.py`, `core/config.py` showing up in the hubs table** — these have fan-in 2–4 with tiny LOC counts. They are doing what models and config files are *supposed* to do; ignore them.
- **Handlers fan-out of 2 each** — that's normal for handler code (route + service), not a smell.

## Where to start

If you can only do one thing this week: **split `utils/helpers.py`**. It is the highest-leverage change because it both reduces fan-in across the most files and forces each call site to declare what it actually needs (which often surfaces dead imports). Do the order-service cleanup second, since it'll be easier once helpers is split. Break the user/order cycle last — it's the cleanest of the three to fix but also the most localized in impact.

## Caveats on the analysis

- The graph only reflects intra-repo coupling — external dependencies (stdlib, third-party) are not counted, so a file that's "small" here could still be doing a lot via outside imports.
- LOC counts non-blank lines and does not strip comments; treat it as a rough size signal.
- Resolution is by relative path + basename match. Dynamic imports, re-exports, or path-aliased imports could be undercounted (not really an issue on this fixture — Python imports are plain — but worth knowing for larger codebases).
- The graph is file-level, so a god-class hiding inside a moderate-sized file would be invisible to this report.
- This repo is small (16 files) — below the ~30-file scale where the analyzer is most useful. The findings above are still real, but you can confirm them by reading the files directly in a few minutes, which is usually faster than tooling at this size.

Raw analyzer output is at `outputs/raw_report.md` if you want the numbers.
