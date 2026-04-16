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
| `/opsx-ext:task` | Queue-based autonomous workflow: explore, break into changes, execute each in an isolated worktree (plan, implement, test, verify), then review and commit |

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
| `dry-principle` | Enforces DRY thinking on every coding task — scans for knowledge duplication, magic values, boundary literals, and repeated logic patterns, while guarding against premature abstraction via the Rule of Three, coincidental similarity, and YAGNI. |
| `fact-check` | Enforces evidence-based problem solving. No guessing — reads the actual source, traces callers and callees, checks git history, verifies library behavior against the version in use, and confirms each fix before moving on. |

## License

MIT
