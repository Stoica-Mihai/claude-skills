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
| `/opsx-ext:task` | Autonomous end-to-end workflow: explore, plan, implement, verify, archive, commit |

## License

MIT
