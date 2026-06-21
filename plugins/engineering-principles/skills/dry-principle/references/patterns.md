# DRY pattern catalogue

The duplication families, each with before/after examples across languages and frameworks. The
skill body lists these lenses with their test questions under "Run this as a multi-pass sweep" —
this file is the worked detail behind each one. Read it when doing a real review or audit; an
ordinary small edit only needs the lens list and tests in the body.

## Contents

- Knowledge duplication (the real target)
- Per-instance and fan-out duplication
- Code-level duplication — magic numbers/strings, boundary literals, repeated logic, parameter
  sprawl, boilerplate, parallel/inverse operations
- Beyond code — config, documentation, database schemas, tests
- UI components
- Interaction and wiring duplication
- Symbol / label duplication
- Call-site duplication

## Knowledge duplication (the real target)

- **Repeated business rules** — the same policy, validation, or calculation encoded in multiple
  places (frontend + backend, service + report, handler + test fixture). Unify into one
  authoritative implementation that others reference.
- **Parallel data structures** — two arrays/objects that must be kept in sync (a list of names
  and a separate list of IDs at matching indices). Merge into a single structure.
- **Redundant or un-derived state** — a stored value, cache, observer, or effect that restates
  knowledge already held elsewhere. If `total` is kept alongside `items`, both encode the same
  fact and will drift. If a `useEffect` mirrors one field of a store into local state, the
  local copy is duplicated knowledge. If a watcher fires every tick to recompute something
  that could be derived at read time, the "when it's fresh" rule lives in two places.

  **Before:**
  ```jsx
  function Cart({ items }) {
    const [total, setTotal] = useState(0);
    useEffect(() => {
      setTotal(items.reduce((s, i) => s + i.price, 0));
    }, [items]);
    return <div>{total}</div>;
  }
  ```
  **After:**
  ```jsx
  function Cart({ items }) {
    const total = items.reduce((s, i) => s + i.price, 0);
    return <div>{total}</div>;
  }
  ```

  The test: "can this value be computed from other values I already have?" If yes, derive it at
  read time instead of storing a parallel copy. Storing it creates two jobs — computing it and
  keeping it in sync — and "keeping in sync" is where the bugs live. Similarly, an
  observer/effect/watcher that exists only to push a value from A into B is usually a sign that
  B should be a derivation of A, not a separate piece of state.
- **Scattered configuration** — the same value (URL, timeout, threshold, feature flag) hardcoded
  in multiple files. Extract to a single config source.
- **Repeated validation** — identical input checks in the UI, API layer, and database. Derive
  from a single schema definition where possible.
- **Shotgun surgery smell** — when a single logical change requires touching many files, the
  knowledge is probably scattered rather than centralized.

## Per-instance and fan-out duplication

Every lens so far assumes the copies are *visible in the source* — the same block in two files,
the same literal in three comparisons. This one is invisible to grep, AST diffing, and a careful
read, because the source appears exactly once. The duplication happens at *runtime*, when a
declarative framework instantiates that single component many times.

A component rendered per-screen, per-row, per-tab, or per-window — `Variants` / `Repeater` over
`Quickshell.screens`, a React list `.map`, a per-window controller — multiplies *everything
stateful inside it* by the instance count. When that state is screen-independent knowledge (a
data fetch, a refresh timer, a network client, a cache, a "pinned" or "selected" flag), each
instance keeps its own copy. Two monitors means two API calls, two timers firing forever, and
two diverging copies of the same fact — none of which the author sees, because they wrote the
widget once.

The test: **"if there were two monitors (or ten rows), would this run or store twice — and does
it need to?"** Screen-*dependent* state (this bar's hover, this row's measured geometry) is
correctly per-instance. Screen-*independent* knowledge that merely happens to live inside a
per-instance component is duplicated, and should be hoisted out.

Flag this at MED/HIGH **even when there is currently only one instance**, because unlike textual
duplication it is also a latent *correctness* bug: per-instance mutable state silently desyncs
the moment a second instance appears. A media widget storing its "pinned player" per-bar lets
monitor A pin one player while monitor B drives another — a real desync, not just wasted
compute. A per-bar clock with seconds enabled runs N system clocks ticking every second *and*
drifts visually between bars.

**Fix:** hoist the screen-independent logic into one shared service or singleton (`pragma
Singleton` in QML, a store or context in React, a module-level singleton elsewhere); the
per-instance component becomes a thin view that binds to it. The step-by-step procedure (and the
inverse-bug guard) is in `references/applying-fixes.md`.

Signs to scan for: a component instantiated via `Variants` / `Repeater` / `.map` over a
collection, holding members — timers, fetchers, network calls, caches, selection state — that
don't depend on the per-instance key.

## Code-level duplication

- **Magic numbers and strings** — unnamed literal values whose meaning isn't obvious from
  context. Even a single occurrence is worth naming if the value has semantic meaning; when
  the same literal appears in multiple places, it's urgent. The constant name should explain
  *what the value means*, not just what it is.

  **Before:**
  ```python
  if retries > 3:
      time.sleep(60)
  # ... elsewhere in the codebase
  if attempts >= 3:
      timeout = 60
  ```
  **After:**
  ```python
  MAX_RETRIES = 3
  RETRY_BACKOFF_SECONDS = 60

  if retries > MAX_RETRIES:
      time.sleep(RETRY_BACKOFF_SECONDS)
  ```

  Watch for: HTTP status codes (`if status == 404`), array indices (`row[3]`), timeouts,
  thresholds, pixel values, regex patterns, format strings, error messages, and config
  defaults scattered through logic. Extract them to named constants at the top of the file
  or in a shared constants module.

  Before hardcoding a literal, check whether the codebase *already* has a name for it. An
  existing enum, string union, branded type, or constants module is the authoritative source
  of that knowledge — using `"active"` as a raw string when `UserStatus.Active` already exists
  introduces a second representation that can drift. Common hiding places: `constants.ts`,
  `types.ts`, `enums.rs`, a domain-specific module (`order/status.ts`), or a generated types
  file from a schema. "Stringly-typed" code that ignores these existing names is duplicated
  knowledge dressed up as a shortcut.

- **Boundary and state-check literals** — values like `0`, `1`, `-1` look harmless but often
  encode meaningful state boundaries. When a comparison against a small literal is really
  asking a semantic question ("is this empty?", "has at least one?", "not found?"), the
  literal obscures the intent. Either extract a named constant or — often better — extract
  a descriptive helper/method that reads like the question being asked.

  **Before:**
  ```typescript
  if (currentCount === 0) {
    showEmptyState();
  }
  if (currentCount > 0) {
    enableCheckout();
  }
  // ... elsewhere
  if (results.length === 0) {
    return fallback;
  }
  if (index === -1) {
    throw new Error("not found");
  }
  ```
  **After:**
  ```typescript
  const EMPTY = 0;
  const NOT_FOUND = -1;

  // or better — helper functions that read like the question:
  const isEmpty = (count: number) => count === 0;
  const hasItems = (count: number) => count > 0;

  if (isEmpty(currentCount)) {
    showEmptyState();
  }
  if (hasItems(currentCount)) {
    enableCheckout();
  }
  if (results.length === 0) {  // .length === 0 is idiomatic enough, but prefer isEmpty() if repeated
    return fallback;
  }
  if (index === NOT_FOUND) {
    throw new Error("not found");
  }
  ```

  The test: if you see the same literal in multiple comparisons that all ask the same
  semantic question, that's duplicated knowledge — the meaning of that boundary value.
  Common culprits: `=== 0` (empty), `> 0` (has items), `=== -1` (not found),
  `=== 1` (single item/first), `< 0` (error/invalid).

- **Repeated logic patterns** — when the same sequence of operations appears in multiple
  places (even with minor variations), extract a helper function. The function name becomes
  documentation of what the pattern does, and fixing a bug in the helper fixes it everywhere.

  **Before:**
  ```python
  # in handler A
  user = db.get_user(user_id)
  if not user:
      raise NotFoundError("User not found")
  if not user.is_active:
      raise ForbiddenError("User is inactive")
  check_permissions(user, "admin")

  # in handler B — same pattern, different resource name in the error
  user = db.get_user(user_id)
  if not user:
      raise NotFoundError("User not found")
  if not user.is_active:
      raise ForbiddenError("User is inactive")
  check_permissions(user, "editor")
  ```
  **After:**
  ```python
  def get_active_authorized_user(user_id: str, role: str) -> User:
      user = db.get_user(user_id)
      if not user:
          raise NotFoundError("User not found")
      if not user.is_active:
          raise ForbiddenError("User is inactive")
      check_permissions(user, role)
      return user
  ```

  Signs you need a helper: you're copying a block and changing one or two values, multiple
  functions follow the same setup/validate/act structure, or the same error handling pattern
  appears across handlers.

- **Parameter sprawl** — a function that has accumulated booleans, mode strings, or optional
  hooks because each new caller needed "just one more tweak." Each flag encodes a branch of
  behavior, and the *which-flags-mean-what* knowledge ends up duplicated at every call site.
  The fix is usually not another parameter — it's a restructure: split into two functions,
  take a strategy object, or let callers compose smaller pieces.

  **Before:**
  ```python
  def send_email(to, subject, body, *,
                 html=False,
                 retry=False,
                 track_opens=False,
                 dry_run=False,
                 async_=False,
                 skip_unsubscribed=True):
      ...
  ```
  Every caller now has to know that `(html=True, track_opens=True, skip_unsubscribed=True)`
  means "marketing email" and `(retry=True, async_=True)` means "transactional." That mapping
  is real knowledge, and it's being reassembled at each call site instead of living in one
  place.

  **After:**
  ```python
  def send_transactional(to, subject, body): ...
  def send_marketing(to, subject, body): ...
  # or, when the variants really are the same operation with a policy:
  send_email(to, subject, body, policy=TRANSACTIONAL)
  ```

  Signs of sprawl: the *next* change to the signature is obviously another boolean; multiple
  call sites pass the same constellation of flags; internal branches share little beyond the
  function's name. When you feel the urge to add a parameter to existing code, ask whether
  you're really describing a new operation — and give it its own name if so.

- **Boilerplate patterns** — if every new module requires the same 15-line setup sequence,
  that's a sign the setup should be a shared helper or generated from a template.

- **Parallel and inverse operations** — when you create a helper for one direction of an
  action, check whether the inverse should also be centralized. Common pairs: `set` / `clear`,
  `open` / `close`, `lock` / `unlock`, `subscribe` / `unsubscribe`, `acquire` / `release`,
  `register` / `unregister`, `attach` / `detach`, `start` / `stop`, `enable` / `disable`,
  `push` / `pop`, `save` / `load`. If you extract `setNotice(m, title, body)` but leave the
  reset (`m.notice = ""; m.noticeTitle = ""`) inlined at three call sites, the knowledge of
  "what fields constitute a notice" lives in two places — the setter and every reset. Adding a
  field to a notice now requires updating both the setter and every reset site. The fix is
  symmetry: define the inverse alongside the helper. Same applies when the inverse is
  conceptual rather than literal — e.g., a `serialize` helper without a matching `parse`,
  or a `format` helper without a matching `unformat`, leaves the round-trip knowledge split.

  Signs to watch for: you've just extracted a helper and the call sites that *don't* use it
  are all doing the opposite of what the helper does; multiple call sites set fields back to
  zero values together; "reset" / "teardown" / "cleanup" blocks that mirror a "setup" helper
  with no corresponding centralization.

## Beyond code

- **Config files** — same dependency version in multiple build files, same env var in multiple
  deployment configs. Use variables, templates, or shared definitions.
- **Documentation** — comments that restate what code does (instead of why) will drift from
  the code. API docs maintained separately from code will go stale. Prefer auto-generated
  docs or doc-comments close to the source.
- **Database schemas** — a constraint that also exists as application-level validation is
  duplicated knowledge. Decide which layer owns it and derive the other.
- **Tests** — duplicated setup/fixture code across test cases should be extracted into shared
  helpers. But keep test assertions specific — DRY test setup, not test intent.

## UI components

UI code is especially prone to duplication because similar-looking elements get rebuilt from
scratch in every view. Think in terms of atomic components — small, self-contained building
blocks that compose into larger pieces.

- **Repeated UI elements** — if the same button style, card layout, input group, or badge
  appears in multiple places, extract it into a reusable component. The component becomes
  the single source of truth for how that element looks and behaves.

  **Before:**
  ```jsx
  {/* in UserProfile.jsx */}
  <div className="px-3 py-1 rounded-full bg-green-100 text-green-800 text-sm font-medium">
    Active
  </div>

  {/* in OrderList.jsx — same pattern, different label */}
  <div className="px-3 py-1 rounded-full bg-yellow-100 text-yellow-800 text-sm font-medium">
    Pending
  </div>
  ```
  **After:**
  ```jsx
  // StatusBadge.jsx — one component, used everywhere
  const VARIANT_STYLES = {
    success: "bg-green-100 text-green-800",
    warning: "bg-yellow-100 text-yellow-800",
    error: "bg-red-100 text-red-800",
  };

  function StatusBadge({ label, variant = "success" }) {
    return (
      <span className={`px-3 py-1 rounded-full text-sm font-medium ${VARIANT_STYLES[variant]}`}>
        {label}
      </span>
    );
  }
  ```

- **Repeated layout patterns** — if multiple pages share the same header/content/sidebar
  structure, extract a layout component. If every form has the same label + input + error
  arrangement, make a FormField component.
- **Scattered design tokens** — colors, spacing, font sizes, border radii repeated as raw
  values across components. Centralize them in a theme, CSS variables, or a tokens file so
  a design change propagates everywhere at once.
- **Oversized components and classes** — a large component is a DRY problem in disguise.
  When a single file handles layout, data fetching, validation, state management, and
  rendering, the reusable patterns inside it are trapped — other parts of the codebase
  can't use them, so they get rebuilt from scratch elsewhere.

  Break large components into smaller, focused pieces. Each piece should do one thing well
  and be independently reusable. Signs a component needs splitting:
  - It's over ~150-200 lines
  - You can describe what it does only with "and" ("it loads data **and** validates input
    **and** renders a form **and** handles submission")
  - Parts of it would be useful in other contexts but can't be extracted without rewriting
  - Changing one section risks breaking unrelated sections in the same file

  This applies equally to UI files (QML, JSX, Vue SFCs, SwiftUI views), backend classes,
  and service modules. A 500-line class with multiple responsibilities will inevitably
  contain logic that gets duplicated elsewhere because nobody realizes it's buried in there.

## Interaction and wiring duplication

Event handlers, listeners, callbacks, middleware chains, and glue code across sibling modules
often duplicate without looking duplicated. They're *behavioral* patterns — they don't show up
as "same styled element" or "same magic number", so grep-based reviews and eyeball diffs miss
them. What repeats is the *shape of the interaction*, not the surrounding content.

Signals that point here:

- Multiple sibling widgets each define a click / tap / gesture handler with the same button
  set and emit three signals whose names differ by one word (`togglePopup` / `toggleConfigPopup`
  / `dismissPopup` in one file, `togglePopup` / `toggleEditPopup` / `dismissPopup` in another).
- Multiple HTTP handlers each start with an identical `load → authenticate → authorize` prelude
  before their domain-specific body.
- Multiple worker classes each wrap their main method in `emit("start"); try { ... } catch (e)
  { emit("error", e); } finally { emit("done"); }`.
- Multiple trait / interface impls share the same prelude and postlude around the one line
  that actually differs.

**Before (React, but the same shape appears in Android `OnClickListener`s, iOS `IBAction`s,
Qt/QML `MouseArea`s, or plain DOM `addEventListener`):**

```jsx
// Clock.jsx
function Clock({ onView, onConfig }) {
  const handle = e => { e.button === 2 ? onConfig() : onView(); };
  return <div onClick={handle} onContextMenu={handle}>{time}</div>;
}

// Weather.jsx — same click shape, different emitted callbacks
function Weather({ onView, onEdit }) {
  const handle = e => { e.button === 2 ? onEdit() : onView(); };
  return <div onClick={handle} onContextMenu={handle}>{temp}</div>;
}

// CpuMeter.jsx — same again
function CpuMeter({ onView, onConfig }) {
  const handle = e => { e.button === 2 ? onConfig() : onView(); };
  return <div onClick={handle} onContextMenu={handle}>{meter}</div>;
}
```

**After — interaction contract declared once, widgets only supply the content:**

```jsx
function DualClickable({ onPrimary, onSecondary, children }) {
  const handle = e => { e.button === 2 ? onSecondary() : onPrimary(); };
  return <div onClick={handle} onContextMenu={handle}>{children}</div>;
}

function Clock()    { return <DualClickable onPrimary={openView} onSecondary={openConfig}>{time}</DualClickable>; }
function Weather()  { return <DualClickable onPrimary={openView} onSecondary={openEdit}>{temp}</DualClickable>; }
function CpuMeter() { return <DualClickable onPrimary={openView} onSecondary={openConfig}>{meter}</DualClickable>; }
```

The knowledge being unified isn't the widget's appearance — it's the *interaction contract*:
left = primary, right = secondary. Declaring that contract once means when you decide
middle-click should close, or that hold-to-reveal needs a keyboard equivalent, you change one
file instead of N.

## Symbol / label duplication

A behavior identified by some token — a key code, route path, CLI flag, env var name, metric
label, command id, event name, signal name, localization key — frequently lives in two
places: the wiring that *acts on* the token and the surface that *renders* it to a user
(button caption, help text, docs, dashboard query, translation table). The token is one piece
of knowledge: "what this thing is called *and* how it appears to the reader." When the two
sides drift, the binding still works but the UI lies.

Example sites across ecosystems:

- Key handlers + their displayed shortcut hints (`match KeyCode::Tab => …` ↔ footer string
  `"Tab toggles danger"`)
- HTTP route definitions + `<Link to="…">` / `href` strings in views
- CLI flag names declared in clap/argparse/cobra + the same flag spelled out in README usage
  examples and onboarding docs
- Command dispatch maps + their auto-generated or hand-written `--help` text
- Metric / counter names emitted by instrumentation (`counter!("api.requests")`) + the same
  names baked into dashboard queries and alert rules
- Event emitter names + listener registrations + analytics docs
- Localization keys in code (`t("auth.signin")`) + the key columns of translation files
- Env var names in `os.getenv(...)` + onboarding docs and Dockerfiles
- Permission / role strings checked by middleware + the same strings rendered in admin UI

**Fix:** define each token (and its display form) once and have every side reference it.

**Before (Rust TUI — key binding and its UI label live in two files):**
```rust
// handlers/picker.rs
match key.code {
    KeyCode::Tab => state.dangerous = !state.dangerous,
    ...
}

// ui/picker.rs — independent literal, will drift the moment the binding moves
draw_hint("Tab = toggle danger");
```

**After:**
```rust
// keys.rs — single source of truth
pub struct Chord { pub codes: &'static [KeyCode], pub label: &'static str }
pub const PICKER_TOGGLE_DANGER: Chord = Chord {
    codes: &[KeyCode::Tab],
    label: "Tab",
};

// handlers/picker.rs
if keys::PICKER_TOGGLE_DANGER.matches(&key) { state.dangerous = !state.dangerous }

// ui/picker.rs
draw_hint(&format!("{} = toggle danger", keys::PICKER_TOGGLE_DANGER.label));
```

Now the binding and its label are one decision. Move the chord to Ctrl-D and the hint
updates automatically; nobody has to remember to grep for "Tab".

Signs you're looking at this pattern:

- "Why didn't the help text update when I changed the keybinding?" — the handler moved, the
  label didn't.
- Touching one feature requires edits in both `handlers/` and `ui/` (or `docs/`), even though
  the change is conceptually one decision.
- A grep for the token finds it as both a typed constant (`KeyCode::Tab`, route enum, flag
  struct field) *and* a bare string literal (`"Tab"`, `"/users"`, `"--verbose"`) in nearby
  files.

**Why narrow DRY sweeps miss it.** Each side reads fine in isolation: the handler is clearly
a `match`, the UI is clearly a label string, the README is clearly prose. Neither is a copy
of the other in *shape*, so structural diffing and "find duplicated blocks" reviews skim past.
The duplication is *semantic*: two representations of the same name in two languages
(code-form and display-form) pointing at the same concept.

When scanning, ask: **for every named action this module wires, where does its name show up
to the user?** If the answer is "a string literal in another file" rather than "the same
constant", that's the duplication — even when no two lines look alike.

## Call-site duplication

A subtler form of duplication — and one the "extract a helper function" instinct tends to miss
because the duplicate isn't the function itself. The *callers* share the same orchestration
shape around a polymorphic dependency: before-hooks, after-hooks, error wrapping, bookkeeping.
Callee-site duplication is "the same function lives in three files." Call-site duplication is
"three call sites wrap their calls in the same orchestration."

You look for this pattern by asking **"what did every caller do *around* the interesting
call?"** rather than **"what did every caller call?"**.

Examples across ecosystems:

- Every panel opener runs `dismissOtherPanels(); panel.toggle();`.
- Every DB write does `tx.begin(); try { work(); tx.commit(); } catch { tx.rollback(); throw; }`.
- Every React data-fetcher does `setLoading(true); try { setData(await fetch()); } catch (e)
  { setError(e); } finally { setLoading(false); }`.
- Every Go HTTP handler does `defer log.Trace(...)(); if err := auth(r); err != nil { return
  401 }; if err := validate(r); err != nil { return 400 }; ...business...`.

The fix is to lift the orchestration into a helper that accepts the varying piece as a
parameter — a context manager, a decorator, a higher-order function, a hook, a middleware
layer, a trait default method. The name of the mechanism differs by language; the move is the
same.

**Before (Python):**
```python
# order_service.py
tx.begin()
try:
    order.save()
    tx.commit()
except Exception:
    tx.rollback()
    raise

# invoice_service.py — same orchestration, different work
tx.begin()
try:
    invoice.save()
    tx.commit()
except Exception:
    tx.rollback()
    raise
```

**After:**
```python
@contextmanager
def transactional(tx):
    tx.begin()
    try:
        yield
        tx.commit()
    except Exception:
        tx.rollback()
        raise

with transactional(tx): order.save()
with transactional(tx): invoice.save()
```

Call-site duplication is how "shotgun surgery" smells are born — a change to the orchestration
touches every caller. Unifying it turns one conceptual change into one file change.
