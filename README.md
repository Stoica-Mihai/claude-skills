# claude-skills

A curated collection of Claude Code plugins and skills by MCS.

## Installation

Add this marketplace to Claude Code:

```
/plugin marketplace add Stoica-Mihai/claude-skills
```

Then browse and install plugins:

```
/plugin install <plugin-name>@claude-skills
```

## Available Plugins

### opsx-ext

Extensions for [OpenSpec](https://github.com/Fission-AI/OpenSpec) — autonomous task workflows with self-correction and verification loops.

**Requires:** OpenSpec initialized in your project (`openspec init`)

```
/plugin install opsx-ext@claude-skills
```

| Command | Description |
|---------|-------------|
| `/opsx-ext:task` | Single-change autonomous workflow: explore, plan, self-review, implement, test, verify in the current working tree, then review and commit |
| `/opsx-ext:task-queue` | Queue-based autonomous workflow for multi-change requests: explore, break into changes, execute each in an isolated worktree (plan, implement, test, verify), then review and commit |

### commit

Clean, minimal git commits — conventional-style summary, optional bullet body, no co-author trailers. Activates whenever you ask Claude to commit.

```
/plugin install commit@claude-skills
```

| Skill | Description |
|-------|-------------|
| `commit` | Stages relevant files by name, writes a conventional-style summary (with a bulleted body when multiple distinct changes are staged), and commits without `Co-Authored-By` trailers or trailing narration. |

### tdd

Test-Driven Development workflow — enforces Red/Green/Refactor discipline with test-first design.

```
/plugin install tdd@claude-skills
```

| Command | Description |
|---------|-------------|
| `/tdd [task]` | Work test-first: list scenarios, write a failing test, implement minimal code to pass, refactor, repeat |

### cli-anything-go

Build powerful, stateful CLI interfaces for any GUI application as compiled Go binaries using Cobra + bubbletea.

```
/plugin install cli-anything-go@claude-skills
```

| Command | Description |
|---------|-------------|
| `/cli-anything-go` | Generate a CLI tool from a specification |

### engineering-principles

Meta-skills that shape how Claude approaches code. These skills don't add new commands — they activate automatically and change Claude's working habits.

```
/plugin install engineering-principles@claude-skills
```

| Skill | Description |
|-------|-------------|
| `dry-principle` | Enforces DRY thinking on every coding task as a deliberate multi-pass sweep — one focused lens per pass (knowledge duplication, per-instance/fan-out state that duplicates at runtime, magic values, boundary literals, redundant state, parameter sprawl, stringly-typed reuse, repeated logic, call-site, interaction, cross-file siblings, symbol↔label, same-file scattered), because each kind hides from the search motion that finds the others. For whole-repo audits it fans out one agent per lens (cross-cutting lenses keep whole-repo view; Rule-of-Three counted centrally), then guides safe refactor execution — fix ordering, per-fix-type verification, and the singleton-hoist procedure. Guards against premature abstraction via the Rule of Three, coincidental similarity, and YAGNI. |
| `fact-check` | Enforces evidence-based problem solving. No guessing — reads the actual source, traces callers and callees, checks git history, verifies library behavior against the version in use, and confirms each fix before moving on. |

### quality-assurance

Quality-engineering skills — smoke testing, build-verification gates, and visual screenshot diffing.

```
/plugin install quality-assurance@claude-skills
```

| Skill / Command | Description |
|-----------------|-------------|
| `smoke-test` | Detects the project's stack and scaffolds a focused 5-10 check smoke-test suite (API-first, <2-minute, idempotent) in the right framework, wired for CI. |
| `/compare-screenshots <img1> <img2>` | Diffs two UI screenshots — handles different sizes/zoom via feature registration — into a similarity score, a confidence-coloured annotated overlay (changed regions boxed), and a written rundown of what changed. |

### futurism-design

A web design system with a strong point of view — bold italic display type, a single red accent, square corners, solid offset shadows, fast directional motion, and paired light/dark themes. Ships a drop-in stylesheet + full component kit, plus an explicit skill that keeps generated UI on-brand instead of defaulting to generic styling.

```
/plugin install futurism-design@claude-skills
```

| Skill | Description |
|-------|-------------|
| `futurism-design` | Applies the Futurism (Paper-Futurist) web aesthetic to any page, component, or app. Reuses a bundled `futurism.css` + `futurism.js` kit (nav, buttons + states, icon button, keycap, badges, inputs, form rows, custom select, toggle, status dot, cards, list rows, tabs, alerts, progress, table, modal, drawer, accent picker) governed by eight design laws, with token-driven light/dark theming. Web-only; invoke with `/futurism-design`. |

## License

MIT
