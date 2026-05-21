# Architectural Hotspots — `/home/mcs/Documents/git/claude-skills/plugins/architectural-analysis/skills/architectural-hotspots/evals/fixtures/synthetic`

Analyzed **16** source files, **20** internal import edges. Edges count file-to-file imports inside the repo only; external/unresolved imports are dropped.

## Hubs — high fan-in
Many files depend on these. Hubs are often legitimate (core libraries, shared types). They become interesting when paired with god-size, grab-bag naming (`utils`, `helpers`, `common`), or high churn in git history.

| File | Fan-in | LOC |
|------|-------:|----:|
| `utils/helpers.py` | 8 | 151 |
| `models/user.py` | 4 | 8 |
| `models/order.py` | 2 | 8 |
| `core/config.py` | 2 | 3 |
| `services/order_service.py` | 1 | 18 |
| `services/notification_service.py` | 1 | 5 |
| `core/db.py` | 1 | 3 |
| `models/audit.py` | 1 | 3 |

## Tangles — high fan-out
These files reach into many corners of the repo. Often a sign of weak single-responsibility — the file is doing too many things, or is a coordination layer that should be split.

| File | Fan-out | LOC |
|------|--------:|----:|
| `services/order_service.py` | 6 | 18 |
| `models/user.py` | 2 | 8 |
| `models/order.py` | 2 | 8 |
| `handlers/order_handler.py` | 2 | 8 |
| `services/notification_service.py` | 2 | 5 |
| `handlers/user_handler.py` | 2 | 4 |
| `handlers/notification_handler.py` | 2 | 4 |
| `core/db.py` | 1 | 3 |
| `models/audit.py` | 1 | 3 |

## God modules — LOC ≥ 400
Large files concentrate too much responsibility in one place. Cross-reference with the Hubs table — a file that is both god-sized *and* a hub is a refactor priority.

_None above threshold._

## Cycles — strongly-connected components
Files inside a cycle cannot be understood, tested, or deployed independently. Cycles of size 2 often mean a missing seam (extract a third module both depend on); larger cycles usually signal a layering violation.

### Cycle 1 — 2 files
- `models/order.py`
- `models/user.py`

## Limitations
- Imports resolved by relative path (where possible) and basename match across the repo. Path aliases, dynamic imports, re-exports, and codegen are likely missed.
- LOC counts non-blank lines; comments are not stripped.
- External / third-party imports are not counted — only intra-repo coupling.
- Treats each file as a node. Class- or function-level coupling is invisible here.
