# Smoke suite for the Django REST Framework service

## Stack detected (from your description)

- **Language:** Python
- **Framework:** Django + Django REST Framework (~30 endpoints)
- **Entry point:** `manage.py runserver`, `settings.py` at project root
- **Test runner:** pytest (in dev deps)
- **Template match:** `references/templates/django-pytest.md` — canonical, not adapted.

> No live filesystem detection was run (no real project on disk), so the
> route paths below are placeholders based on common DRF conventions —
> `TODO` markers in the file flag every value you need to substitute.

## Proposed smoke suite — 6 checks (< 2 min budget)

1. **GET `/health/`** returns 200 — liveness probe.
2. **GET `/api/users/{known_id}/`** returns 200 + shape-correct user — primary read path.
3. **GET `/api/users/999999999/`** returns 404 — error path, not 500.
4. **GET `/api/orders/` without auth** returns 401/403/302 — authN gate works.
5. **GET `/api/orders/` with auth** returns 200 — exercises DRF auth + a ViewSet end-to-end.
6. **POST `/api/orders/` with auth** returns 201 — primary write path, guarded against prod
   via `SMOKE_ALLOW_WRITE=1`.

6 checks is comfortably inside the 5-10 band for a service of this size.
Cross out any that hit endpoints owned by another team; add a domain-specific
happy-path (checkout, login redirect) if one obviously dominates the critical path.

## Artefact

- `tests/smoke/test_smoke.py` — runnable scaffold, in-process by default
  via Django's bundled `Client`, switches to `requests` against
  `SMOKE_BASE_URL` when set.

## TODOs you must wire

| Marker | What to supply |
| --- | --- |
| `DJANGO_SETTINGS_MODULE` | Add to `pytest.ini` / `pyproject.toml [tool.pytest.ini_options]` — e.g. `myproject.settings`. pytest-django must see it before app import. |
| `SMOKE_TOKEN` | Real bearer token for deployed-env runs. |
| `KNOWN_USER_ID` | A seeded user id that exists in every environment. The `seed_user` fixture creates it in-process; for deployed runs you guarantee it via a data-seed step. |
| `READ_PATH` / `LIST_PATH` / `WRITE_PATH` | Substitute two endpoints from your ~30 that represent the critical path. |
| `HEALTH_PATH` | Confirm — could be `/health/`, `/healthz/`, `/readyz/`, or a custom view. |
| `seed_user` fixture fields | If you use a custom user model with required fields, adjust the `defaults={...}`. |
| Create payload in `test_create_record_happy_path` | Minimal valid body your serializer accepts. |

## How to run

```bash
# In-process (uses Django's test Client, transactional DB rollback):
pytest tests/smoke -q

# Against a deployed env (uses requests over the network):
SMOKE_BASE_URL=https://api.example.com \
SMOKE_TOKEN=eyJ... \
pytest tests/smoke -q

# Enable the write check against a deployed env (opt-in, off by default):
SMOKE_ALLOW_WRITE=1 SMOKE_BASE_URL=... SMOKE_TOKEN=... pytest tests/smoke -q
```

Expected runtime: < 5 s in-process, < 30 s against a deployed URL.

## CI

A minimal GitHub Actions snippet is included as a comment block at the
bottom of `test_smoke.py` — uncomment into `.github/workflows/smoke.yml`
if/when you want it as a PR gate. You didn't ask for CI explicitly, so
I haven't created the workflow file.

## Failure discipline

- Smoke failure = stop-the-line. Subsequent stages do not run.
- Capture status + response body + any correlation header (`X-Request-ID`)
  on failure — the asserts in this file already inline the status/body
  into the message string, so a CI log is enough for triage.
- Quarantine (don't delete) flaky smoke tests; fix within the sprint.
- This is **not** a regression suite — resist the urge to grow it past
  ~10 checks. Edge cases, validation rules, error-message wording all
  belong in the regression tier.
