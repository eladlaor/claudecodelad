# session-finder

Gives Claude Code a searchable memory of past sessions.

## Why This Plugin?

Other session search tools typically grep through raw transcripts. session-finder takes a different approach: it builds a **structured index** on every session exit, with LLM-generated summaries, files touched, git branch, project path, and timestamps. This lets you search by what you *did* (e.g., "database schema setup"), not just what you *said*. The index builds automatically in the background. No manual tagging or configuration needed.

Every time you exit a session, a `SessionEnd` hook automatically extracts the first and last user prompts, files touched, git branch, timestamps, and session name, then generates a one-sentence LLM summary and appends it to `~/.claude/session-index.jsonl`.

## Install

```
/plugin install session-finder@claudecodelad
```

## Setup

No setup required. The index builds automatically as you end sessions.

## Usage

```
/session-finder:find-session <natural language description>
```

### Examples

| Command | What it does |
|---------|-------------|
| `/session-finder:find-session database schema setup` | Find sessions about database work |
| `/session-finder:find-session that session where I configured auth` | Search by topic description |
| `/session-finder:find-session langrag project refactoring` | Search by project name and activity |

Results include session ID, project, branch, date, summary, and a ready-to-use `claude --resume <id>` command. By default shows top 5 results; include a count in your query (e.g., "top 10 sessions about auth") to see more.

## Configuration

Works out of the box with no configuration. Optional environment variable:

| Variable | Description | Default |
|----------|-------------|---------|
| `SESSION_FINDER_MODEL` | Model used for LLM summary generation | `claude-3-5-haiku-latest` |

Set in your shell profile (e.g., `export SESSION_FINDER_MODEL=claude-sonnet-4-20250514`) for higher-quality summaries at higher cost.

## Uninstall

```
/plugin uninstall session-finder@claudecodelad
```

## How It Works

On `SessionEnd`, a hook script indexes key metadata from the session into a JSONL file. When you search, Claude reads the index, ranks matches by relevance (summary, prompts, files, project, branch, recency), and presents the top results. Works naturally with `/rename`. Renamed sessions are indexed and searchable too.
