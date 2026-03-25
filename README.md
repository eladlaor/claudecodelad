# claudecodelad

A Claude Code plugin marketplace. Install individual plugins to enhance your Claude Code workflow.

## Install

Add the marketplace (one-time):

```
/plugin marketplace add eladlaor/claudecodelad
```

Then install any plugin:

```
/plugin install <plugin-name>@claudecodelad
```

## Plugins

### date-context

<img src="illustrations/today_is_today.jpg" width="500">

Claude Code doesn't natively know what day it is. This plugin injects today's date into Claude's context on every session start.

```
/plugin install date-context@claudecodelad
```

### session-finder

<img src="illustrations/session_finder.jpg" width="600">

Gives Claude Code a searchable memory of past sessions.

Every time you exit a session, a `SessionEnd` hook automatically:
- Extracts the first and last user prompts, files touched (Write/Edit), git branch, timestamps, and session name (slug)
- Generates a one-sentence LLM summary using Haiku
- Appends it all as one line to `~/.claude/session-index.jsonl`

Then when you need to find a past session:

```
/session-finder:find-session that session where I set up the database schema
```

Claude searches the index, ranks results using its own reasoning, and returns matches with ready-to-use `claude --resume <id>` commands.

Works naturally with `/rename` — if you rename a session, the name is indexed and searchable too.

```
/plugin install session-finder@claudecodelad
```

### worktree-manager

Manage persistent git worktrees for parallel human+AI development. Unlike Claude's built-in `EnterWorktree` (temporary, session-scoped agent isolation), this plugin creates **persistent sibling directories** for long-lived parallel work across sessions.

**Two skills included:**

- **`/worktree-manager:worktree`** — Create, list, remove, and check status of worktrees
  ```
  /worktree-manager:worktree create feature-auth
  /worktree-manager:worktree list
  /worktree-manager:worktree status
  /worktree-manager:worktree remove feature-auth
  ```

- **`/worktree-manager:merge`** — Merge all worktree branches back with dependency-ordered merges, conflict resolution, auto-detected verification, and cleanup
  ```
  /worktree-manager:merge
  ```

**SessionStart hook** automatically detects if you're inside a worktree and injects context (branch, main repo path, sibling worktrees).

```
/plugin install worktree-manager@claudecodelad
```

### timewatch-fill

Fill TimeWatch attendance via browser automation. Uses claude-in-chrome to log into TimeWatch, navigate to the attendance page, and fill entry/exit times for one or more days.

**Setup:** Each user creates their own credentials file at `~/.config/timewatch-fill/.env` (see plugin docs for details).

```
/timewatch-fill:timewatch-fill                              # Fill today (09:00-18:30, SolugenAI, office)
/timewatch-fill:timewatch-fill tomorrow                     # Fill tomorrow
/timewatch-fill:timewatch-fill today 0830 1730              # Custom times
/timewatch-fill:timewatch-fill this month                   # Fill all unfilled workdays this month
/timewatch-fill:timewatch-fill yesterday 0900 1830 Cinema home  # Custom task + location
```

Requires the `claude-in-chrome` extension in Chrome.

```
/plugin install timewatch-fill@claudecodelad
```
