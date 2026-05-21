# NOTICE

This plugin is derived from Anthropic's `skill-creator` plugin, distributed
under the Apache License 2.0.

- Upstream source: `anthropics/claude-plugins` (plugin `skill-creator`)
- Original copyright: Copyright Anthropic, PBC.
- License: Apache License 2.0 (see `LICENSE`).

## Changes from upstream

The drafting workflow, eval viewer (`eval-viewer/`), benchmark aggregator
(`scripts/aggregate_benchmark.py`), description optimizer
(`scripts/run_loop.py`, `scripts/run_eval.py`), packaging script
(`scripts/package_skill.py`), and the supporting agents and references are
all carried over essentially unchanged.

The single deliberate departure is in `skills/skill-builder/SKILL.md`, in
the "Test Cases" and "Step 2: While runs are in progress" sections:

- **Upstream `skill-creator`** instructs the same agent that designed the
  skill to also write the test prompts and assertions. This embeds the
  agent's implementation knowledge into the eval set; the benchmark
  tends to reflect what the skill already does well rather than what the
  description promises.

- **`skill-builder`** delegates eval authoring to a fresh subagent that
  sees only the skill's `name`, `description`, and a handful of example
  use cases the designer supplies. The subagent does not read the
  SKILL.md body, bundled scripts, or fixtures, so its prompt selection
  is independent of the implementation. The designer then runs and
  reviews those evals as normal.

No other behavioural change is intended. If you want the upstream
behaviour exactly, use `skill-creator` from `claude-plugins-official`.
