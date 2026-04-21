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

## What to look for

Before writing or modifying code, scan the relevant context for these patterns:

### Knowledge duplication (the real target)

- **Repeated business rules** — the same policy, validation, or calculation encoded in multiple
  places (frontend + backend, service + report, handler + test fixture). Unify into one
  authoritative implementation that others reference.
- **Parallel data structures** — two arrays/objects that must be kept in sync (a list of names
  and a separate list of IDs at matching indices). Merge into a single structure.
- **Scattered configuration** — the same value (URL, timeout, threshold, feature flag) hardcoded
  in multiple files. Extract to a single config source.
- **Repeated validation** — identical input checks in the UI, API layer, and database. Derive
  from a single schema definition where possible.
- **Shotgun surgery smell** — when a single logical change requires touching many files, the
  knowledge is probably scattered rather than centralized.

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

- **Boilerplate patterns** — if every new module requires the same 15-line setup sequence,
  that's a sign the setup should be a shared helper or generated from a template.

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

1. Before writing, check existing code for related patterns. Is there already a helper,
   constant, config value, or component that does what you need? Use it.
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
   In-file review misses this every time because each file reads fine on its own. Repeated
   invocations of DRY review on a project that never surface a given duplication are a
   signal to widen the scan: if narrow review has already been run three times without
   catching something, the something lives between files rather than within one.

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
