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
