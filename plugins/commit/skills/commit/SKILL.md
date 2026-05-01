---
version: 1.1.0
name: commit
description: >
  Handles git commits with concise, list-style messages and no co-author trailers.
  Use this skill whenever the user asks to commit, says "commit", "/commit", "commit this",
  "save my changes", or any variation of requesting a git commit. This skill MUST be used
  for every commit operation — it overrides the default commit behavior.
---

# Commit

Create clean, minimal git commits. No fluff, no co-author lines.

## Process

1. Run `git status` and `git diff` (staged + unstaged) to understand what changed. Also run `git log --oneline -5` to match the repo's existing message style.
2. **Read the full output.** Never truncate diffs or logs with `head`, `tail`, line limits, or any other form of partial reading. A truncated diff means you're guessing about changes you haven't seen — and that leads to wrong or vague commit messages. If the diff is large, read all of it before writing the message. The quality of the commit message depends entirely on seeing the complete picture.
3. Stage the relevant files by name — avoid `git add -A` or `git add .` to prevent accidentally staging secrets or junk.
4. Write a commit message following the format below.
5. Commit. Do not push unless explicitly asked.

## Message format

Use a single-line summary in conventional commit style (`fix:`, `feat:`, `refactor:`, `docs:`, `chore:`, `test:`), lowercase, no period. Keep it under 72 characters.

If multiple distinct changes are staged, use a bulleted list body:

```
feat: add volume slider and notification history

- wire up PipeWire volume control with mute toggle
- add notification history dropdown in bar capsule
```

The summary line should capture the overall theme; bullets cover the specifics. Skip the body if one line says it all.

## Rules

- **No Co-Authored-By trailers.** Ever.
- **No trailing summaries.** Don't narrate what you just committed — the user can read the diff.
- **Don't commit files that look like secrets** (`.env`, credentials, tokens). Warn if the user asks to.
- **Use a HEREDOC** to pass the message so multi-line formatting is preserved:
  ```bash
  git commit -m "$(cat <<'EOF'
  feat: the summary line

  - detail one
  - detail two
  EOF
  )"
  ```
- If there are no changes to commit, say so and stop.
- If a pre-commit hook fails, fix the issue and create a **new** commit — never amend.
