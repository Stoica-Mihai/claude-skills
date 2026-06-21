---
name: dry-principle
description: >
  Enforces DRY (Don't Repeat Yourself) thinking across all programming tasks — writing new code,
  reviewing code, fixing bugs, refactoring, editing config, schemas, tests, and documentation.
  Use this skill for ANY coding or programming-related task: feature implementation, bug fixes,
  code review, refactoring, writing tests, editing configuration, database schema changes,
  build system modifications, or documentation updates. This skill should trigger whenever
  Claude is about to write, modify, or review code or code-adjacent files. Even if the user
  doesn't mention "DRY" or "duplication", this skill applies to all software engineering work.
---

# DRY Principle

Apply DRY thinking to every programming task — not as a pedantic rule, but as a design instinct.
DRY means every piece of **knowledge** has a single, authoritative representation in the system.
The key word is knowledge, not code. Two identical-looking code blocks might represent different
knowledge (and should stay separate). Two different-looking blocks might encode the same business
rule (and should be unified).

The test: "If this knowledge changes, how many places do I need to update?" If the answer is
more than one, that's a DRY violation worth examining.

## Run this as a multi-pass sweep

The different kinds of duplication below don't just *look* different — they're found by
different search motions, and that's the catch. Magic values surface when you *scan literals*.
Knowledge duplication surfaces when you *ask what changes together*. Wiring duplication surfaces
when you *compare interaction shapes* across siblings. Symbol↔label duplication surfaces when
you *match a typed token against a bare string in another file*. Same-file scattered duplication
surfaces when you *read look-alike function bodies side by side*. Per-instance duplication
surfaces only when you *picture the component multiplied across every screen, row, or tab it
renders into* — it's invisible in the source, which appears exactly once. These are genuinely
different mental questions, and the moment you lock onto one — say, hunting magic numbers — you stop
seeing the others, because you're no longer asking their question. This is why a single
read-through reliably catches the loudest one or two categories and silently walks past the
rest. It isn't that the rest are subtle; it's that you weren't looking with the right lens.

So don't try to see everything in one look. Make one focused pass per lens, switching the
question you ask each time, and keep a running note of which passes you've completed so you
don't circle the same ground. A later pass routinely finds things an earlier one couldn't —
not because they were hidden, but because you were asking a different question. The passes:

1. **Knowledge & business rules** — the same policy, validation, or calculation in more than
   one place; parallel structures kept in sync by hand; redundant or derivable state; scattered
   config. Ask: *"if this rule changes, how many places do I edit?"*
   → see "Knowledge duplication (the real target)".
2. **Per-instance / fan-out state** — screen-independent knowledge (a fetch, a timer, a cache, a
   "pinned" / "selected" flag) living inside a component the framework instantiates per screen /
   row / tab. The source appears exactly once, so this is invisible to every text-based lens —
   it only duplicates at runtime, and it's the one that's also a latent desync *bug*, not just
   waste. Ask: *"if there were two monitors or ten rows, would this run or store twice — and does
   it need to?"* → see "Per-instance and fan-out duplication".
3. **Magic values & boundary literals** — unnamed literals that carry meaning; `0` / `1` / `-1`
   comparisons that really ask a semantic question; stringly-typed code ignoring an enum that
   already exists. Ask: *"does this literal mean something, and does a name for it already
   exist?"* → see "Code-level duplication" (magic numbers/strings, boundary literals).
4. **Repeated logic, parameters & orchestration** — copied blocks with one or two values
   changed; parameter sprawl; the same `begin/try/commit/rollback` or `load→auth→authorize`
   wrapped *around* a varying call. Ask: *"what did every caller do around the interesting
   line?"* → see "Repeated logic patterns", "Parameter sprawl", "Call-site duplication".
5. **Cross-file siblings, wiring & symbol↔label** — 3+ sibling files exposing the same outward
   shape (signal triples, event sets, prop interfaces, repeated UI elements/layouts/tokens); a
   handler's token versus its user-facing label/route/flag living as a bare string in another
   file. Ask: *"do the siblings share an interface? does this name reappear as a literal
   somewhere else?"* → see "UI components", "Interaction and wiring duplication", "Symbol /
   label duplication".
6. **Same-file scattered & beyond-code** — the same 4-line block embedded in three functions of
   one file; duplicated test setup, config, docs, or schema constraints. Ask: *"read the
   look-alike bodies side by side — what repeats?"* → see "Same-file scattered" scanning,
   "Beyond code".

Scale the sweep to the work: a one-line fix collapses to near-nothing (a quick glance and
you're done), but a real review or refactor earns all six deliberate passes. When you
finish, fold the hits from every pass into one consolidated set of findings rather than
reporting each pass separately — see "Communication".

When the codebase is large enough that you fan the sweep out across several readers or
subagents, partition the work by *concern* — data flow, wiring, theming, per-instance state —
not by directory. A module-by-module split feels tidy but is blind to exactly the cross-module
and runtime-instantiation duplication that hides best; each reader sees one folder and every
file in it reads fine on its own. Carry a short ledger of what you rejected and *why* from one
pass to the next, so a later pass doesn't re-flag a coincidental match you already cleared. You
know you've converged when a fresh deep pass turns up only one-line nits — literal zero is never
provable on a live codebase, so stop when the angles run dry, not when you've "proven" emptiness.

For a whole-repository audit specifically — "find all the duplication in this codebase", a large
refactor, a pre-release cleanup — fan the six passes out **one agent per lens** (giving each
agent a single question is what stops it drifting across lenses), and read
`references/parallel-sweep.md` first: it has the agent tree, the rule that cross-cutting lenses
must keep whole-repo view rather than being directory-split, and where the Rule-of-Three count
has to live. Don't reach for this on an ordinary edit — the fan-out only pays off at repo scale.

## What to look for

Before writing or modifying code, scan the relevant context for these patterns:

### Knowledge duplication (the real target)

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

### Per-instance and fan-out duplication

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
per-instance component becomes a thin view that binds to it.

Signs to scan for: a component instantiated via `Variants` / `Repeater` / `.map` over a
collection, holding members — timers, fetchers, network calls, caches, selection state — that
don't depend on the per-instance key.

### Code-level duplication

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

### Beyond code

- **Config files** — same dependency version in multiple build files, same env var in multiple
  deployment configs. Use variables, templates, or shared definitions.
- **Documentation** — comments that restate what code does (instead of why) will drift from
  the code. API docs maintained separately from code will go stale. Prefer auto-generated
  docs or doc-comments close to the source.
- **Database schemas** — a constraint that also exists as application-level validation is
  duplicated knowledge. Decide which layer owns it and derive the other.
- **Tests** — duplicated setup/fixture code across test cases should be extracted into shared
  helpers. But keep test assertions specific — DRY test setup, not test intent.

### UI components

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

### Interaction and wiring duplication

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

### Symbol / label duplication

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

### Call-site duplication

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

## Guardrails: when NOT to deduplicate

DRY's biggest failure mode is premature or wrong abstraction. These guardrails are just as
important as the principle itself.

### The Rule of Three

Two instances of similar code are not enough evidence to abstract. Wait for three occurrences —
by the third time, the real pattern is visible and you can design a good abstraction. On the
first or second occurrence, note the similarity but leave it alone unless the duplication is
clearly the same piece of knowledge.

### Coincidental similarity is not duplication

Two code blocks can look identical today but exist for different reasons. Ask: "Do these change
for the same reason, at the same time, by the same person?" If not, they represent different
knowledge that happens to look alike right now. Merging them creates coupling between unrelated
concerns — when one changes, the shared abstraction must accommodate both, harming both.

**Example:** A `validateUserInput()` and `validateAPIResponse()` might have identical checks
today. But user input validation changes when the UI changes, while API response validation
changes when the upstream API changes. These are different pieces of knowledge — keep them
separate.

### The wrong abstraction is worse than duplication

Sandi Metz: "Prefer duplication over the wrong abstraction." Watch for these warning signs
that an abstraction has gone wrong:

- A shared function accumulating boolean parameters and conditional branches to handle
  "slightly different" callers
- A base class where subclasses override most methods
- A "utility" module that every file imports but each uses differently
- Adding a new feature requires modifying shared code in a way that might break other callers

When you spot these, the fastest way forward is often back: inline the abstraction into its
callers, remove what each caller doesn't need, then re-examine whether a genuine shared
pattern exists.

### YAGNI complements DRY

Don't build abstractions for hypothetical future duplication. "We might need this in three
other places someday" is not a reason to abstract today. Abstract when you actually have the
duplication, not when you imagine you might.

## How to apply this

### When writing new code

1. **Before writing, search for existing helpers.** Scan the places this codebase keeps
   shared knowledge:
   - The file you're editing and its adjacent siblings in the same directory
   - Utility / helper / shared modules (common names: `utils/`, `lib/`, `common/`, `shared/`,
     `helpers/`)
   - Type and constant modules (`constants.ts`, `types.ts`, `enums.rs`) — existing string
     unions, enums, or branded types the literal you're about to hardcode may already live in
   - Central homes for cross-cutting concerns (auth, logging, HTTP clients, db helpers,
     feature flags)
   - **The standard library.** Before writing a helper that does generic data manipulation —
     cloning a map, checking membership, equality, sorting, reversing, finding, mapping,
     filtering, deduping, batching — check whether the language's stdlib already provides it.
     This is especially worth a check for newer stdlib additions: Go's `maps.Clone` /
     `slices.Contains` / `cmp.Or`, Python's `itertools.batched` / `functools.cache`,
     JavaScript's `Array.prototype.findLast` / `Object.groupBy`, Rust's `slice::is_sorted` —
     these regularly replace hand-rolled utilities that were written before the stdlib caught
     up. A 4-line helper that wraps a single stdlib call is duplicated knowledge with
     extra steps.

   If a helper, constant, config value, or component already does what you need, use it. If
   one *almost* does, consider extending it rather than writing a parallel version — but only
   when the two callers really share the same knowledge (see "Coincidental similarity" below).
2. If you're about to write something that looks like existing code, pause and ask: is this
   the same knowledge? If yes, extend or reuse the existing implementation. If no (different
   reasons to change), write it fresh.
3. Extract shared components **before** duplicating them. If you know two callers need the
   same thing, write the shared version first.
4. **Scan for magic values.** Before finishing, review your code for any literal numbers or
   strings that carry meaning — timeouts, thresholds, status codes, sizes, URLs, format
   strings. Don't skip small values: `0`, `1`, `-1` in comparisons often encode state
   boundaries that deserve a name or helper. Name them. If the same value already exists
   as a constant elsewhere, reuse it.
5. **Scan for repeated patterns.** If you just wrote a block of logic that mirrors something
   nearby, extract a helper function immediately rather than leaving two copies.

### When reviewing or modifying existing code

This is where the multi-pass sweep earns its keep — run the passes from "Run this as a
multi-pass sweep" over the area you're touching, switching the question each pass. The points
below are the same lenses stated as actions:

1. Notice duplication in the area you're touching. You don't need to fix every DRY violation
   in the codebase — focus on the code you're already changing.
2. If you find duplicated knowledge that affects your change, flag it. Suggest a concrete
   refactor if the path is clear, or note it as tech debt if the fix is complex.
3. If you're about to copy-paste-modify, stop. Can you parameterize the existing code instead?
   But only if the variation represents the same underlying knowledge.
4. **Look sideways before finishing.** When the module you're touching has 3+ sibling files
   at the same level (components in `components/`, handlers in a route package, services
   under `services/`, structs implementing the same trait, views in an MVC app), take 30
   seconds to diff their *interface surfaces* — exported functions, emitted events, signal
   names, method signatures, prop types. If three siblings expose the same outward shape in
   parallel (same signal triples, same event set, same prop interface), that's the Rule of
   Three across files, and it's exactly the archetype the rule was designed to catch.
   In-file review misses this every time because each file reads fine on its own. This is the
   cross-file pass (pass 5) — if your earlier passes keep coming up empty but something still
   feels off, that's the signal to widen the lens: the duplication lives *between* files rather
   than within one, and only a sideways diff of sibling interfaces will surface it.

5. **Cross-check handler ↔ label pairs.** For every named action the module wires — a key
   binding, route, CLI flag, command, event, metric, env var, permission, localization key —
   confirm the *user-visible* name comes from the same source as the handler matches on, not
   a parallel string literal in a sibling file. This duplication is invisible to
   structural diffs because the two sides aren't shaped alike (typed match arm vs. bare
   string), so it survives narrow DRY sweeps. See "Symbol / label duplication" above.

6. **Scan within a single file for scattered duplication.** Cross-file scanning catches
   "same function name in two packages." Within-file scanning catches "same 4-line block
   embedded inside three different functions of the same file." The latter is invisible to
   anyone reading one function at a time and easy to miss when reviewing diffs that touch
   only one function. The trick: when you're in a file with several similarly-shaped
   functions (multiple `summarize*`, `format*`, `parse*`, `handle*`, or all the methods on a
   struct), pull up each one and read the bodies side-by-side. Identical literal boundaries
   (`if len(runes) > 40`), identical setup/teardown shapes, identical error-formatting calls
   embedded in different functions are the typical hit. Same-file scattered duplication is
   especially common in:
   - Utility modules with many small functions
   - Formatter/renderer/serializer modules where each function handles a different type
   - Handler/dispatcher modules where each case has its own preamble
   - Test files (covered separately under "Tests" — DRY the setup, not the intent)

### When fixing bugs

A bug that exists in duplicated code probably exists in every copy. After fixing it in one
place, search for other instances of the same logic. If you find copies, consider whether
this is the right time to unify them — but only if they genuinely represent the same knowledge.

## Communication

When you spot DRY issues, be specific and practical:

- Name what knowledge is duplicated and where
- Explain whether it's worth fixing now or just noting
- If recommending a refactor, show the concrete approach
- If recommending against deduplication (coincidental similarity, wrong abstraction risk),
  explain why the duplication is actually healthy

Don't lecture about DRY in the abstract. Apply it through your actions — write DRY code,
flag violations when relevant, and protect against over-abstraction. The goal is better
software, not adherence to a principle for its own sake.
