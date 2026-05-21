# skill-builder

Drop-in replacement for Anthropic's `skill-creator` with one deliberate
change: **evaluation prompts and assertions are authored by a blind
subagent**, never by the agent that designed the skill.

## Why

In the upstream `skill-creator` workflow, the same agent that drafts the
SKILL.md also writes the eval prompts. That agent already knows where the
skill is strong and where it is weak, so prompt selection drifts toward the
strong path. The benchmark looks healthy while real blind spots stay
invisible.

`skill-builder` splits the roles:

- The **designer agent** drafts the skill (same as upstream).
- A **blind subagent** writes the eval prompts and assertions. It sees only
  the skill's `name`, `description`, and a few example use cases — never the
  SKILL.md body, the bundled scripts, or the test fixtures.

Everything else — eval viewer, benchmark aggregator, description optimizer,
packaging — is carried over from upstream unchanged.

## When to use this instead of skill-creator

Pretty much always, unless you have a specific reason to want upstream's
behaviour. The cost of `skill-builder` is one additional Agent call per
iteration (the blind subagent). The benefit is an unbiased benchmark.

## Attribution

Derived from `skill-creator` in `anthropics/claude-plugins`. Apache 2.0.
See `NOTICE.md`.
