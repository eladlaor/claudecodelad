# TIMEWATCH-FILL PLUGIN USAGE

## Table of Contents

- [Summary](#summary)
- [First-Time Setup](#first-time-setup)
- [Quick Start](#quick-start)
- [Arguments](#arguments)
- [Examples](#examples)
- [Defaults](#defaults)
- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Troubleshooting](#troubleshooting)

## Summary

Claude Code plugin that fills TimeWatch attendance via browser automation (claude-in-chrome). Supports filling a single day or a range of days with configurable entry/exit times, task, and location.

## First-Time Setup

### 1. Install the plugin

```
/plugin install timewatch-fill@claudecodelad
```

### 2. Create your credentials file

```bash
mkdir -p ~/.config/timewatch-fill
cat > ~/.config/timewatch-fill/.env << 'EOF'
TIMEWATCH_COMPANY_ID=
TIMEWATCH_EMPLOYEE_ID=
TIMEWATCH_INTERNAL_EMPLOYEE_ID=
TIMEWATCH_PASSWORD=

# Optional defaults (uncomment to customize):
# TIMEWATCH_DEFAULT_ENTRY=0900
# TIMEWATCH_DEFAULT_EXIT=1830
# TIMEWATCH_DEFAULT_LOCATION=office
# TIMEWATCH_WORKDAYS=7,1,2,3,4
# TIMEWATCH_LOCALE_OFFICE=משרד
# TIMEWATCH_LOCALE_HOME=בית
EOF
```

Edit `~/.config/timewatch-fill/.env` and fill in your credentials. Optionally uncomment and customize the defaults.

### 3. Where to find your credentials

| Variable | Where to Find |
|----------|---------------|
| `TIMEWATCH_COMPANY_ID` | The "company number" field on the TimeWatch login page (`c.timewatch.co.il`). Ask your HR/admin if unsure. |
| `TIMEWATCH_EMPLOYEE_ID` | The "employee number" field on the TimeWatch login page. This is your personal employee number. |
| `TIMEWATCH_INTERNAL_EMPLOYEE_ID` | Log into TimeWatch manually, click "update attendance data", and look at the URL bar. It's the `ee=` parameter value (e.g., `editwh.php?ee=890123&e=1234...`). |
| `TIMEWATCH_PASSWORD` | Your TimeWatch login password. |

### 4. Verify Chrome extension

Make sure you have:
- Chrome running with the `claude-in-chrome` extension installed and connected
- Internet access to `c.timewatch.co.il`

## Quick Start

```
/timewatch-fill:timewatch-fill                          # Fill today with defaults (09:00-18:30, first task, office)
/timewatch-fill:timewatch-fill tomorrow                 # Fill tomorrow
/timewatch-fill:timewatch-fill today 0830 1730          # Custom times
/timewatch-fill:timewatch-fill this month               # Fill all unfilled workdays this month
```

## Arguments

All arguments are positional and optional. Missing arguments fall back to defaults.

```
/timewatch-fill:timewatch-fill $0 $1 $2 $3 $4
```

| Arg | Name | Type | Default | Description |
|-----|------|------|---------|-------------|
| `$0` | DATE | `today` \| `tomorrow` \| `yesterday` \| `this week` \| `this month` \| `YYYY-MM-DD` | `today` | Target day(s) |
| `$1` | ENTRY | `HHMM` (4 digits) | from config or `0900` | Entry time |
| `$2` | EXIT | `HHMM` (4 digits) | from config or `1830` | Exit time |
| `$3` | TASK | string (fuzzy match) | first task in dropdown | Task/project name |
| `$4` | LOCATION | `office` \| `home` | from config or `office` | Remark field |

**Notes:**
- `this week` / `this month` count as a single `$0` value (two words consumed together).
- TASK is matched case-insensitively against TimeWatch dropdown options. If no match, the first available task is selected.
- LOCATION maps to a locale string from config (default: `office` = `משרד`, `home` = `בית`).
- Workdays are configurable via `TIMEWATCH_WORKDAYS` in `.env` (default: Sun-Thu). Non-workdays are always skipped.

## Examples

| Command | Result |
|---------|--------|
| `/timewatch-fill:timewatch-fill` | Today, 09:00-18:30, default task, office |
| `/timewatch-fill:timewatch-fill tomorrow` | Tomorrow, 09:00-18:30, default task, office |
| `/timewatch-fill:timewatch-fill yesterday` | Yesterday, 09:00-18:30, default task, office |
| `/timewatch-fill:timewatch-fill 2026-03-20` | Specific date, defaults |
| `/timewatch-fill:timewatch-fill today 0830 1730` | Today, 08:30-17:30, default task, office |
| `/timewatch-fill:timewatch-fill today 0900 1830 Cinema` | Today, Cinema task |
| `/timewatch-fill:timewatch-fill yesterday 0900 1800 Taglit home` | Yesterday, Taglit task, home |
| `/timewatch-fill:timewatch-fill this week` | All unfilled workdays this week |
| `/timewatch-fill:timewatch-fill this month 0900 1830 MyProject office` | All unfilled workdays this month |

## Defaults

All defaults can be overridden in `~/.config/timewatch-fill/.env`.

| Setting | Config Variable | Fallback |
|---------|----------------|----------|
| Entry time | `TIMEWATCH_DEFAULT_ENTRY` | `0900` |
| Exit time | `TIMEWATCH_DEFAULT_EXIT` | `1830` |
| Task | — | first available in dropdown |
| Location | `TIMEWATCH_DEFAULT_LOCATION` | `office` |
| Workdays | `TIMEWATCH_WORKDAYS` | `7,1,2,3,4` (Sun-Thu) |
| Office remark | `TIMEWATCH_LOCALE_OFFICE` | `משרד` |
| Home remark | `TIMEWATCH_LOCALE_HOME` | `בית` |

## How It Works

1. Opens Chrome via claude-in-chrome browser automation
2. Navigates to TimeWatch and logs in using your credentials from `~/.config/timewatch-fill/.env`
3. Opens the monthly attendance overview
4. For each target date: clicks the row to open the edit modal, checks if already filled, fills entry/exit/task/remark, clicks update
5. Reports results (filled / skipped / errors)

Days that are already filled are skipped. Locked days (too old for retroactive edits) are reported as errors.

## Prerequisites

- Chrome running with the `claude-in-chrome` extension connected
- Credentials configured in `~/.config/timewatch-fill/.env` (see [First-Time Setup](#first-time-setup))
- Internet access to `c.timewatch.co.il`

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| "Credentials not configured" | `.env` file missing or empty | Follow [First-Time Setup](#first-time-setup) above |
| "day is locked" | TimeWatch blocks retroactive edits beyond a certain window | Contact HR/admin to unlock |
| Login fails | Wrong credentials | Check `~/.config/timewatch-fill/.env` values |
| Task not found | Fuzzy match failed | Use a more specific substring, or check the dropdown in TimeWatch |
| Modal doesn't open | Row is not editable (weekend/holiday) | Verify the date is a workday |
| Browser not responding | Chrome or extension disconnected | Restart Chrome and reconnect the extension |
