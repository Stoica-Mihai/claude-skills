# Analyst pass — iteration 2

## Headline

| Metric | New skill (lang-agnostic, +2 axes) | Old skill (Rust-leaning, 5 axes) | Δ |
|---|---|---|---|
| Pass rate | 89% (8/9) | 100% (9/9) | −11pp |
| Time | 229.5s ± 67s | 202.3s ± 71s | +27s |
| Tokens | 66.7k ± 2.7k | 58.6k ± 9.6k | +8.1k |

New skill **regressed** on detection density. Pass rate down 11pp,
both cost dimensions slightly worse. But the headline number hides
the qualitative story — see below.

## Per-eval

| Eval | New | Old | What happened |
|---|---|---|---|
| commit.rs | 3/3 | 3/3 | Tie. Both hit ≥5/8 ground-truth. New skill found both iter-1 misses (delete-before-fsync durability, --threads pool placement) — the additions worked here. |
| structural.rs | 2/3 | 3/3 | **New regressed.** New hit 2/6 ground-truth, old hit 5/6. New spent attention on perf + coupling depth, missed correctness ground-truth (UTF-8 corruption, field_name_for_child index-vs-id, literal-to-wildcard fallthrough). |
| plan.rs | 3/3 | 3/3 | Tie. Both hit ≥4/7 ground-truth. |

## What the structural.rs regression actually means

New skill on eval-2 did NOT score worse content-wise. It found a
correctness bug old skill missed:

- `structural.rs:464` — hard-coded `root.kind() == "source_file"`
  works only for Rust. Python's root is `module`, Bash is
  `program`, JSON/Markdown are `document`. Friendly patterns
  silently mis-rooted for every non-Rust grammar. Real cross-
  grammar correctness bug. **New found it; old missed it.**

But it missed three correctness bugs old skill caught:
- `field_name_for_child(child.id() as u32)` passing node-id
  where child-index expected
- UTF-8 byte walker corruption (`out.push(b as char)`)
- silent literal-to-wildcard fallthrough

Net qualitative read: **new found 1 new significant bug, missed 3
older significant bugs.** Score regressed. Net engineering value
roughly even or slightly worse.

## Pattern-miss vs real miss

One of the 4 "misses" on eval-2 is a regex artefact, not a real
miss:
- New skill DID find non-deterministic primary-capture (audit line
  4: "fallback 'primary capture' picks the numerically-highest
  capture index...artifact of capture-name ordering"). My assertion
  regex required `non-?deterministic | max\(capture | iteration order
  | @root.{0,30}absent`. None matched the new phrasing. Pattern
  miss.

Adjusting for that, new skill score on structural.rs is 3/6, not
2/6 — still below the 4/6 threshold and still less than old's 5/6.

The assertion methodology itself has a ceiling: regex-on-output
cannot tell "agent found a different but equally-good bug" from
"agent missed the bug". 

## Why the rewrite caused a regression

Best guess from reading the audit transcripts:

1. **More axes = thinner per-axis attention.** Old skill had 5 axes;
   new has 7. Same audit time, more buckets to fill. The new axes
   (durability/ordering, concurrency) won material findings on
   commit.rs but cost attention on structural.rs where they don't
   apply.

2. **"Read every function body" was meant to fight skim-reading but
   may also have led the agent to find more *novel* findings
   (rabbit-hole risk) at the cost of methodical coverage of the
   obvious bugs.**

3. **Language-agnostic rewrite removed Rust-specific cues** (e.g.
   `let _ =`, `.ok()`, `unwrap_or`) that were directly priming the
   agent for the kind of correctness bugs in `commit.rs` and
   `structural.rs`. Generic "fallible call return discarded"
   triggers less reliably than the Rust-specific glyph.

## Cost regression

Tokens up 14%, time up 14%. Reading two new axes plus the
generalization framing costs context. Not catastrophic, but the
skill is now ~5.5k chars (~33% larger than old).

## Recommendation

Three options for iter-3:

**A. Keep new structure, sharpen examples.** Keep durability and
   concurrency axes (they paid off on commit.rs). But replace the
   abstract "fallible call return value discarded" smell with both
   abstract phrasing AND a one-line cross-language example list,
   so the agent recognises the glyph in any stack. Goal: regain
   correctness detection without losing language-agnosticism.

**B. Roll back new axes, keep generalization.** Drop durability /
   concurrency axes since they're not universally applicable; keep
   the lang-agnostic rewrite of the original 5. Risk: lose the
   commit.rs wins on durability and threads.

**C. Accept iter-2 as the right shape, tighten assertions.** The
   skill found a real cross-grammar bug iter-1 missed. The
   "regression" is partly an artefact of measuring on iter-1's
   ground truth. Add the source_file bug to ground truth; re-run.

A is the most disciplined; B is the safe revert; C is most honest
about measurement limits but doesn't actually improve the skill.

My read: **A**. Keep what worked, fix what regressed. Estimate ~20
lines of edits.

## Reproducibility caveat

Still n=1 per cell. Iter-2 std-dev on time is huge (±67s, ±71s).
Don't over-index on single-run deltas.
