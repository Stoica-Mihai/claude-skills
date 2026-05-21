# Analyst pass — iteration 1

## Headline numbers

| Metric | With skill | Baseline | Delta |
|---|---|---|---|
| Pass rate | 100% (14/14) | 43% (6/14) | **+57pp** |
| Time | 234s ± 58s | 217s ± 30s | +17s (slower) |
| Tokens | 57.4k ± 6k | 70.1k ± 8k | **−12.7k** |

Pass-rate delta is dramatic; cost is mildly higher latency offset by
materially lower token usage (skill scopes the audit, baseline wanders).

## What the assertions actually measured — and what they didn't

The 57-point pass-rate gap is **mostly format compliance**, not
bug-finding density. Honest read:

| Assertion family | With skill | Baseline | Real signal? |
|---|---|---|---|
| `file:line` regex (e.g. `commit\.rs:\d+`) ≥3 | 3/3 | 0/3 | Mixed — baseline DID emit line refs, just as `commit_one:226` (fn name), `line 233-237`, `H1 — …`. My regex required exact `file.rs:N` form. So this assertion = "did the agent adopt my prescribed citation format". |
| Bold section headers (`**Perf`, `**Correctness`, …) ≥2 | 3/3 | 0/3 | Pure format — baseline used H1-style "High/Medium/Low" severity headers or numbered findings. |
| Specific bug detection (regex_or, e.g. NonceGen / stage_all / emit_node) | 3/3 | 3/3 | Real signal of bug-finding — baseline finds bugs equally. |
| "Top targets" trailing section | 3/3 | 0/3 | Pure format. |

So: out of 5 assertion families, 1 measures actual finding quality
and 4 measure adherence to the skill's prescribed format. The
prescribed format is exactly what the skill exists to impose, so
this isn't fraud — but it would be dishonest to claim the skill
made Claude find more bugs. It didn't, in this iteration. It made
Claude *write the same findings in a denser, more scannable
shape*.

## What the qualitative outputs actually show

Reading the six audit.md files side-by-side, more nuanced
differences emerge:

1. **Bug-finding overlap is high but not total.** Baselines surfaced
   real findings the with-skill runs missed:
   - Baseline eval-2 caught the `field_name_for_child` index-vs-id
     bug at `structural.rs:552` (high-impact correctness) — though
     this finding ALSO appears in the with-skill eval-2 output
     ("Correctness bug, structural.rs:552").
   - Baseline eval-1 retry caught a durability-ordering bug (delete
     backups before fsyncing parent dirs) that the with-skill
     eval-1 run did not flag at all. This is a HIGH-impact
     correctness finding the skill ran past.
   - Baseline eval-3 caught the `--threads` pool not constraining
     apply (M3) which the with-skill eval-3 also missed.
   So baselines occasionally produce findings of equal or greater
   severity. The skill is not strictly dominant.

2. **Skill outputs are denser.** With-skill eval-3: 10 findings in
   ~40 lines. Baseline eval-3: ~5 findings spread across H/M/L
   sections with explanation prose. Reader-throughput per line is
   meaningfully higher with the skill format.

3. **Skill enforces "fix sketch" per finding.** Baseline often
   describes the problem without giving the one-line remediation.

4. **Skill correctly omits axes that don't apply.** Eval-1
   with-skill omitted Memory axis (notes it lives in `plan.rs`,
   not `commit.rs`) — exactly the calibration the SKILL.md
   prescribed.

## Cost analysis

- Tokens **lower** with skill (-18%). Counter-intuitive but
  consistent with the skill scoping the work — the agent is told
  what to look for and stops there, rather than wandering through
  general code-review territory. Baseline runs explored more
  sibling files and produced longer prose.
- Time slightly **higher** with skill (+8%). Reading SKILL.md is
  added latency; format planning is added work. Not a problem.

## Non-discriminating assertions

The "bug detection" `regex_or` assertions (NonceGen, stage_all,
emit_node) all passed for both configs. They confirm both runs
found the obvious findings, but provide zero discrimination. For
iteration 2 evals, these should be replaced with assertions that
do discriminate — e.g. "finds at least N of {ground-truth
findings}" where N is calibrated such that current with-skill
hits it and baseline doesn't, OR a graded comparison.

## Recommended next steps

1. The skill works as designed (impose format, scope audit). But
   the headline 57pp gap overstates its value — the user should
   read the qualitative outputs and decide whether
   *format-and-density alone* justifies the skill, or whether the
   skill needs to do more.
2. If more is wanted: add to SKILL.md explicit instructions to
   look for durability-ordering bugs and execution-pool / thread-
   pool issues (both missed in iteration 1 with-skill runs that
   baseline caught).
3. Consider whether `Top targets` should mandate at least one
   item per active axis, to prevent the agent from collapsing
   everything into a single category.
4. Tighten assertions to measure bug-finding density rather than
   format adherence (e.g. count distinct ground-truth findings hit).

## Reproducibility caveat

n=1 run per cell. Variance unknown. Real benchmark would re-run
each cell 3x to get stddev that means something. Iteration 1 is
indicative, not conclusive.
