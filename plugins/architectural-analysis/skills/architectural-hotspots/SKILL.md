---
name: architectural-hotspots
description: >
  Surfaces architectural hotspots in a codebase — high-coupling hub files,
  tangled high-fan-out modules, oversized god modules, and dependency cycles.
  Use this skill when the user asks where to refactor, which files are
  architecturally problematic, which modules are most tightly coupled, where
  the tech debt is concentrated, what should be split up, or how the
  dependency structure of a project looks. Also trigger on phrases like
  "find hotspots", "coupling problems", "god classes", "circular dependencies",
  "refactor candidates", or "which files do too much" — even if the user
  does not say the word "architecture".
---

# Architectural Hotspots

Static dependency-graph analyzer that ranks files along four orthogonal
dimensions instead of inventing a single composite score:

- **Hubs** — many other files depend on them (high fan-in).
- **Tangles** — they depend on many other files (high fan-out).
- **God modules** — large files concentrating too much responsibility.
- **Cycles** — strongly-connected components of size > 1 in the import graph.

Each dimension answers a different question; the human reader combines them.
A file showing up in **two** sections is more interesting than one with a high
score in any single dimension.

## When to run this

Run it when the user is asking a *strategic* question about the codebase —
"where should I start refactoring", "what's tightly coupled", "is this app
architecturally sound", "which files keep biting us". Do not run it for
narrow questions about a specific file or function.

Skip it on:
- Single-file edits or bugfix tasks.
- Codebases with fewer than ~30 source files — the analyzer needs scale to
  be useful, and on small repos the user can read the structure directly.
- Repos that are mostly generated code or templates.

## How to run

The analyzer is a single Python 3 script with no third-party dependencies.

```bash
python plugins/architectural-analysis/skills/architectural-hotspots/scripts/find_hotspots.py <repo_path>
```

Useful flags:

- `--top N` — rows per section (default 15).
- `--god-loc N` — LOC threshold for the god-modules section (default 400).
- `--output report.md` — write to file instead of stdout.
- `--ext .EXT=LANG` (repeatable) — force a file extension to be parsed as a
  specific language. `LANG` can be any precise tag (`python`, `js`, `go`,
  `rust`, `java`, `c`, `ruby`, `csharp`, `php`, `swift`, `scala`, `qml`,
  `nix`) or `generic`. Use when a project uses unusual extensions
  (`--ext .nut=generic` for Squirrel scripts).
- `--sniff` — parse files with unknown extensions if they look like text.
  Catches obscure languages at the cost of more false positives. Off by
  default; turn on for polyglot or unusual repos.

The script enumerates files via `git ls-files` when the target is a git repo
(so `.gitignore` is honoured for free), and falls back to `os.walk` with a
hardcoded ignore list (`node_modules`, `.venv`, `target`, `dist`, …) otherwise.

**Precise parsers** (per-language regex, lower false-positive rate):
Python, JS/TS, Vue, Svelte, Rust, Go, Java/Kotlin, C/C++, Ruby, C#, PHP,
Swift, Scala, QML, Nix.

**Generic fallback** (best-effort regex on common import keywords —
`import`, `require`, `use`, `include`, `from`, `open`, `with`, `mod`,
`extern crate`): Dart, Elixir/Erlang, Haskell, OCaml, F#, Lua, R, Julia,
Nim, Zig, V, Crystal, Perl, shell, Clojure, Lisp, Scheme, Racket, Ada,
Pascal, D, Groovy, GDScript, Gleam, Solidity, Move, Pkl, Elm. Lossier than
the precise parsers — extra false positives possible — but means the
analyzer degrades gracefully on language families without dedicated
support. For everything else: see the fallback clause below.

Imports are resolved to internal repo files by:

1. **Path-alias expansion** for TypeScript / JavaScript projects — the
   analyzer reads `tsconfig.json` / `jsconfig.json` and resolves aliases like
   `@/lib/foo` according to the project's declared `paths`.
2. **Relative path resolution** where the language supports it (`./`, `../`,
   leading-dot Python imports).
3. **Basename match across the repo** otherwise — the last segment of the
   import path is matched against file stems, with ties broken by directory
   proximity to the source file.

For files **without a recognised extension** the analyzer additionally tries:
- The first line as a shebang (`#!/usr/bin/env python3` → Python).
- A Vim / Emacs modeline (`# vim: ft=lua`).
- With `--sniff`, treat the file as generic if it looks like text.

External, third-party, and unresolved imports are dropped. **The graph only
reflects intra-repo coupling.**

### When the analyzer can't help

If the report says **"Analyzed 0 source files"** or shows a non-empty repo
producing **0 internal import edges**, the codebase is in a language the
analyzer doesn't parse, or the language uses a coupling mechanism the
analyzer can't see (component-instantiation in QML, runtime DI in some Java
projects, codegen in others). Do not pretend the report is the answer in
that case. Say so explicitly to the user, fall back to reading the codebase
manually (or with grep/LSP), and offer to extend the analyzer if this
language family will come up again. A blank report with no caveat is worse
than no report at all — it implies the codebase is healthy when really the
tool just didn't see it.

## Reading the output

The report is markdown with five sections in this order:

### Hubs

Sorted by fan-in (descending). High fan-in is *not automatically a problem* —
core libraries, type modules, and shared clients are *supposed* to be hubs.

A hub becomes a refactor candidate when **at least one** of the following is
also true:

- Its name is generic / grab-bag (`utils.py`, `helpers.ts`, `common.go`,
  `misc.rs`). That naming usually means the file accumulated unrelated
  responsibilities because nobody knew where else to put them.
- It also appears in the god-modules table (large + many dependents = the
  blast radius of changes is huge).
- The user mentions it changes often, breaks often, or is constantly in
  merge conflicts — these are observable symptoms of an over-loaded hub.

If a hub is small, focused, and well-named (e.g. `db/client.py` at 80 LOC),
note it as healthy and move on.

### Tangles

Sorted by fan-out (descending). High fan-out means the file reaches into
many parts of the repo — a sign of either:

- **Coordination / glue code** doing too much orchestration (a god service,
  a single huge handler).
- **Wrong layer** — a low-level module reaching up into application code, or
  a view layer reaching directly into data layer internals instead of going
  through a seam.

A fan-out of 2–3 in a small file is usually fine. The interesting cases are
files with fan-out in the double digits, especially when LOC is also high.

### God modules

Files whose LOC is at or above the threshold. Cross-reference these against
the Hubs and Tangles tables: a file that is both **god-sized and a hub** is a
top refactor priority because every change to it ripples widely.

The LOC metric is non-blank lines, not stripped of comments. Treat it as a
*rough* size signal, not a precise measurement. A 400-line file that is 60%
comments is less of a problem than a dense 400-line file.

### Cycles

Files inside a strongly-connected component cannot be understood, tested, or
deployed in isolation — they all need each other. Cycle size matters:

- **Size 2** — often a missing seam. Two modules import each other because
  there is a shared concept that wants its own home. Extract a third module
  both depend on.
- **Size 3+** — usually a layering violation. Some abstraction has been
  inverted: a "lower" layer is reaching back into a "higher" one. Identify
  the seam where the cycle crosses a conceptual boundary and break it there
  (dependency inversion, callbacks, events).

### Limitations

The output already lists these, but worth repeating because they shape how
much weight to give the report:

- Path-alias indirection (`@/components/...` in Next.js, `~/lib/...` in some
  TS configs), dynamic imports, re-exports through barrel files, and
  codegen targets can all cause the resolver to miss real edges.
- Basename-match resolution can produce false positives when two unrelated
  files share a stem. The proximity tie-breaker helps but is not perfect.
- The graph is file-level. A god-class buried inside a moderate-sized file
  is invisible to this analysis.

State these caveats in your summary to the user so the report is taken as a
starting point for human judgement, not an authoritative verdict.

## Communicating findings

After running the script, do not just paste the table. The report is the
*evidence*; the user wants the *interpretation*.

A good response looks like:

> Ran the hotspot analyzer on `src/`. Three files are worth your attention:
>
> 1. **`src/utils/helpers.ts`** (LOC 312, fan-in 47) — both a god module and
>    a hub. Generic name + accumulated dependents = high blast radius. Worth
>    splitting by domain.
> 2. **`src/services/order_service.py`** (LOC 612, fan-out 18) — large
>    coordination layer reaching into many modules. Candidate for breaking
>    into orchestrator + steps.
> 3. **One cycle of 3 files** between `models/user.py`, `models/order.py`,
>    `models/audit.py` — likely a shared concept (audit context?) wanting
>    its own module.
>
> Full report at `<path>` if you want the raw numbers. Caveat: the resolver
> uses basename matching, so path-aliased imports may be undercounted.

Always include:

1. The 2–4 files that stand out, with the *reason* they stand out (which
   tables they hit, what the combination implies).
2. One concrete suggestion per finding — even if hedged. "Split by domain",
   "extract a shared module", "invert the dependency".
3. The caveat about resolution limits, so the user calibrates trust.

Do not dump the entire table unless the user asks for it. The script writes
markdown that *can* be shown verbatim — but lead with the human-readable
summary first.

## When the analyzer disagrees with the user

If the user pushes back ("`utils.ts` is fine, leave it alone") trust them —
they know the codebase. The analyzer surfaces *candidates*; humans confirm.
Update your reading of the codebase based on their pushback rather than
re-arguing from the metrics.
