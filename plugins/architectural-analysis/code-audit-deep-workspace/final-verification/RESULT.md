# Final verification — "what are the hotspots in /home/mcs/Documents/git/recast?"

The originating problem: user asked this question, hotspots-skill-only
gave file rankings without line-level findings, user wanted both.

Test setup: same generic prompt sent to two subagents.
- A: no skills available (raw tool access)
- B: both `architectural-hotspots` and `code-audit-deep` skills available

| | A: no skills | B: both skills |
|---|---|---|
| Output shape | File-level rankings only | Rankings **+ line-level findings** |
| Top finding granularity | "split structural.rs into 4 files" | `structural.rs:552` ID/index conflation, `commit.rs:247` unlink-before-fsync, `commit.rs:114` --threads scope, etc. |
| Actionable line refs | 0 | ~15 |
| Skill chain used | n/a | hotspots → code-audit-deep on top 4 |
| Tokens | 67.3k | 88.6k (+31%) |
| Time | 244s | 219s (-10%) |

## Verdict

**Gap closed.** The both-skills configuration produces what no-skill
*should have* produced — file rankings PLUS line-level findings,
matching the iter-0 unmet expectation.

Counter-intuitively the no-skill baseline produced *less* depth on
this generic phrasing than it did on explicit "audit commit.rs" prompts
(iter-1). Without a specialized skill, the agent answered the literal
question ("hotspots") as a structural-ranking question and stopped
there. The skill chain forces the second pass.

Specific bugs the both-skills agent caught that no-skill missed:
- `commit.rs:247` — backups unlinked before parent-dir fsync
  (durability ordering bug in atomicity-critical code)
- `commit.rs:114` + `main.rs:343` — `--threads N` honored only in
  planner, stage/commit on global pool
- `structural.rs:552` — `field_name_for_child(child.id() as u32)`
  ID/index conflation; field constraints silently lost on every
  friendly query
- `plan.rs:139` — convergence uses `find_iter().count()` instead of
  `find().is_some()`
- `commit.rs:425` — `SystemTime::now()` per nonce in parallel stage
- `structural.rs:341` + `plan.rs:112` — dual orchestrator coupling

## Cost

Both-skills uses 31% more tokens but 10% less wall time
(parallelizable file reads + skill instruction reduces
exploratory wandering). Net acceptable.

## Side observation

The both-skills agent autonomously executed the chain instruction
in `architectural-hotspots/SKILL.md` ("after producing rankings,
invoke code-audit-deep on top 3-5 files"). Chain pattern works
without needing the user to ask twice.
