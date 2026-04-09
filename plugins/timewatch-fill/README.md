# timewatch-fill

Fill TimeWatch attendance via browser automation. Uses `claude-in-chrome` to log into TimeWatch, navigate to the attendance page, and fill entry/exit times for one or more days.

## Why This Plugin?

TimeWatch requires daily attendance logging: open the browser, log in, click the day, fill in entry time, exit time, task, location, submit. Multiply that by 20+ workdays a month and it becomes a real time sink, especially if you fall behind and need to backfill.

This plugin automates the entire flow. One command fills a single day, a whole week, or an entire month of unfilled workdays. It skips days that are already filled, handles locked-day warnings, and supports configurable work schedules (not just the Israeli Sun-Thu default).

## Install

```
/plugin install timewatch-fill@claudecodelad
```

## Setup

First-time setup required. See [Setup Guide](skills/timewatch-fill/knowledge/USAGE.md#first-time-setup).

## Usage

```
/timewatch-fill:timewatch-fill [date] [entry] [exit] [task] [location]
```

All arguments are positional and optional. Missing arguments fall back to your configured defaults (or built-in defaults if not configured).

### Arguments

| Arg | Name | Format | Default | Description |
|-----|------|--------|---------|-------------|
| 1 | Date | `today` \| `tomorrow` \| `yesterday` \| `this week` \| `this month` \| `YYYY-MM-DD` | `today` | Target day(s) |
| 2 | Entry | `HHMM` (4 digits) | from config or `0900` | Entry time |
| 3 | Exit | `HHMM` (4 digits) | from config or `1830` | Exit time |
| 4 | Task | string (fuzzy match) | first task in dropdown | Task/project name |
| 5 | Location | `office` \| `home` | from config or `office` | Remark field |

- `this week` / `this month` count as a single date value (two words consumed together).
- Task is matched case-insensitively against TimeWatch dropdown options. If no match, the first available task is selected.
- Location maps to a configurable locale string (default: `office` = `משרד`, `home` = `בית`).
- Workdays are configurable (default: Sun-Thu, Israeli schedule). See [Setup Guide](skills/timewatch-fill/knowledge/USAGE.md#defaults) for Mon-Fri and custom schedules.

### Examples

| Command | What it does |
|---------|-------------|
| `/timewatch-fill:timewatch-fill` | Today, 09:00-18:30, default task, office |
| `/timewatch-fill:timewatch-fill tomorrow` | Tomorrow with defaults |
| `/timewatch-fill:timewatch-fill today 0830 1730` | Today, custom times |
| `/timewatch-fill:timewatch-fill this month` | All unfilled workdays this month |
| `/timewatch-fill:timewatch-fill yesterday 0900 1800 MyProject home` | Custom task + location |

## Uninstall

```
/plugin uninstall timewatch-fill@claudecodelad
```

## How It Works

Opens Chrome via `claude-in-chrome`, logs into TimeWatch with your credentials, and navigates to the monthly attendance overview. For each target date, it clicks the row to open the edit modal, checks if the day is already filled, fills entry/exit/task/remark, and clicks update. Already-filled days are skipped. Locked days are reported as errors.

## Prerequisites

- Chrome running with the `claude-in-chrome` extension connected
- Credentials configured (see [Setup Guide](skills/timewatch-fill/knowledge/USAGE.md#first-time-setup))
- Internet access to `c.timewatch.co.il`
