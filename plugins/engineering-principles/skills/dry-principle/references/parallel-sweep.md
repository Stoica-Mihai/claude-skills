# Parallel DRY sweep (whole-repo audits)

Read this **only** for a whole-repository DRY audit — "find all the duplication in this
codebase", a large refactor, a pre-release cleanup. A normal edit that triggers `dry-principle`
does inline thinking and never reaches this file; fanning out across agents for a three-line
change is pure overhead.

> The deterministic way to run this is the bundled workflow `scripts/dry-sweep.js` (via the
> `Workflow` tool) — it spawns exactly the agent tree below, the same way every run. This file is
> the *rationale* behind that tree and the by-hand fallback when `Workflow` isn't available.

The point of fanning out is not raw speed. It's that the sweep's core discipline — *one mental
motion per pass, because locking onto one lens blinds you to the others* — is hard to hold in a
single context juggling six questions at once. Give **each agent exactly one lens** and it
physically cannot drift: its whole prompt is one question. Parallelism here is a way to enforce
the discipline, not just to go faster.

## The shape

```
LEVEL 0  orchestrator (you, running the skill)
   │  scope the repo: modules, file count, languages, framework.
   │  Note any declarative fan-out (QML `Variants`/`Repeater`, React list `.map`,
   │  per-window controllers) — that makes Pass 2 high-value.
   │
   ├─ spawn ONE agent per lens (6). Each agent gets exactly one lens question
   │  plus the matching detail section from SKILL.md. Never a mixed-concern agent.
   │
LEVEL 1  lens agents — split differently depending on the lens:
   │
   │   GLOBAL lenses — keep whole-repo view, NEVER directory-split:
   │     P1 knowledge & business rules
   │     P2 per-instance / fan-out
   │     P5 cross-file siblings, wiring, symbol↔label
   │   If a global lens fans out, it splits by SUB-PATTERN, not directory — e.g.
   │   P5 → {sibling-interface diff} {symbol↔label pairs} {wiring/orchestration},
   │   each sub-agent still scanning the whole repo for its sub-pattern.
   │
   │   LOCAL lenses — duplication is within a file/region, so directory-split is safe:
   │     P3 magic values & boundary literals
   │     P4 repeated logic, parameter sprawl, call-site
   │     P6 same-file scattered & beyond-code
   │   Each spawns ≤5 sub-agents, one per repo region, all asking that one question.
   │
LEVEL 2  leaf agents → return structured findings + a rejection list:
   │     findings:  { file:line, knowledge duplicated, severity, proposed fix, confidence }
   │     rejected:  { candidate, why rejected }   ← guardrails applied here, per leaf
   │
MERGE  (orchestrator only — it is the only level that sees everything)
        1. collect findings per lens
        2. cross-lens dedup: same site flagged by two lenses → keep the more specific
        3. Rule-of-Three gate (see below) — count instances across the FULL set
        4. apply the rejection ledger
        5. severity sort — per-instance/desync findings float to the top, MED/HIGH
           even at instance-count 1
        6. emit ONE consolidated report, not six
```

Budget: 6 lenses × ≤5 sub-agents ≈ up to ~30 leaf agents on a large repo. Scale down for
smaller codebases — for a few thousand lines, skip the Level-2 split entirely and run the six
lens agents flat.

## The three rules that solo runs get wrong

These are the difference between a parallel sweep that's better than serial and one that's
actively worse. The model improvising a fan-out reliably violates all three.

### 1. Region-split only the local lenses

The global lenses depend on whole-repo visibility — that *is* the knowledge they detect. Per-
instance duplication is "this component is instantiated per monitor *over here* but holds global
state *in its definition over there*." Cross-file/sibling duplication is, by definition, spread
across files. Symbol↔label pairs live in two files in two different forms. Split any of these by
directory and each sub-agent sees one folder where every file reads fine on its own — you have
recreated the exact blindness the skill exists to fight. Keep them whole-repo. Only the local
lenses (magic values, same-file scattered, region-local repeated logic) survive a directory
split, because their duplication is contained within the region a sub-agent sees.

### 2. Rule-of-Three lives in the orchestrator, never in a leaf

The Rule of Three counts occurrences: don't abstract until the third. A region-split leaf sees
only its region, so it **cannot** count three occurrences spread across regions — it will either
abstract a 2-instance coincidence (noise) or fail to connect a 3-across-module pattern (miss).
So leaves report *candidates* with their local count; the orchestrator sums across the full set
and decides what clears the bar. The single place that sees everything is the only place that
can apply the rule honestly.

### 3. Every leaf carries the "when NOT to deduplicate" guardrails

Thirty eager agents with no brakes produce a wall of over-abstraction suggestions. Each leaf
treats its matches as *hypotheses* — it opens and reads the actual sites and tries to disprove
each one (see the skill's "A candidate is a hypothesis, not a finding") rather than reporting a
surface pattern. It applies the guardrails — coincidental similarity, the wrong-abstraction
risk, YAGNI — and returns *why* it rejected a candidate, not silently drop it. Those rejection reasons
are the **rejection ledger**: the orchestrator keeps it so a finding cleared in one round isn't
re-surfaced in the next, and so the human can see what was considered and dismissed.

## Convergence and second rounds

If the first round produced non-trivial findings, the orchestrator can re-spawn **only the
lenses that hit**, passing the rejection ledger in so already-dismissed candidates don't return.
Stop when a fresh deep round turns up only one-line nits. Literal-zero duplication is never
provable on a live codebase — converge when the angles run dry, not when you've "proven"
emptiness.

## What the orchestrator returns

One consolidated, severity-sorted report — the same output a serial sweep would produce, just
arrived at by six single-minded agents instead of one mind switching lenses. Per-instance/fan-
out findings lead (they're latent desync bugs, not just waste). Each finding names the
duplicated knowledge, where it lives, the proposed fix, and — where relevant — why a nearby
look-alike was *not* flagged.
