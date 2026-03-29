# date-context

Claude Code natively injects today's date (e.g., `2026-03-28`) into the system prompt, but not the day of week, current time, or timezone.

Without these, Claude can't reliably answer "is today a weekday?", reason about whether a deadline is today or tomorrow, or account for your local timezone when generating timestamps or scheduling suggestions.

This plugin fills that gap with a `SessionStart` hook that injects the full temporal context.

**Example context injected:** `Today is Saturday, March 28, 2026. Current time: 14:30 (IST +03:00).`

## When Is This Useful?

- **Deadline reasoning**: "this is due Friday" now means something when Claude knows today is Wednesday
- **Schedule-aware tasks**: "skip weekends" works when Claude knows the day of week
- **Timestamp generation**: logs, filenames, and commit messages can include accurate local time
- **Timezone awareness**: Claude knows your offset for cross-timezone coordination

## Install

```
/plugin install date-context@claudecodelad
```

## Setup

No setup required. Works immediately after install.

## Uninstall

```
/plugin uninstall date-context@claudecodelad
```

## How It Works

A `SessionStart` hook runs a shell script that outputs today's date, day of week, current local time, and timezone. Claude receives it as additional context at the beginning of every session. The hook uses POSIX `date`. No dependencies, no network calls, completes in milliseconds.
