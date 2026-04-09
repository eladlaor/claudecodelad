---
name: timewatch-fill
description: >-
  Fill TimeWatch attendance via browser automation with claude-in-chrome.
  Use when the user says "fill timewatch", "fill attendance", "log my hours",
  "timewatch", "fill today", "fill this week", "fill this month",
  or wants to submit work hours on TimeWatch.
  Supports filling a single day, today, or a range of days.
argument-hint: "[today|tomorrow|yesterday|this week|this month|YYYY-MM-DD] [HHMM] [HHMM] [task] [office|home]"
allowed-tools:
  - Bash(date *)
  - Bash(cat *)
  - Bash(mkdir *)
  - mcp__claude-in-chrome__*
---

# TimeWatch Browser Auto-Fill

Fill attendance on TimeWatch (c.timewatch.co.il) using `claude-in-chrome` browser automation.

## Positional Arguments

Parse `$ARGUMENTS` into positional args `$0` through `$4`. All are optional — if missing, use the default.

**IMPORTANT:** `this week` and `this month` are two-word `$0` values — consume both words as `$0`, then shift remaining positions accordingly.

```
/timewatch-fill:timewatch-fill $0 $1 $2 $3 $4
```

| Arg | Name | Type | Default | Description |
|-----|------|------|---------|-------------|
| `$0` | DATE | `today` \| `tomorrow` \| `yesterday` \| `this week` \| `this month` \| `YYYY-MM-DD` | `today` | Which day(s) to fill |
| `$1` | ENTRY_TIME | `HHMM` (exactly 4 digits) | `TIMEWATCH_DEFAULT_ENTRY` or `0900` | Entry time. Split: HH = first 2 digits, MM = last 2 |
| `$2` | EXIT_TIME | `HHMM` (exactly 4 digits) | `TIMEWATCH_DEFAULT_EXIT` or `1830` | Exit time. Split: HH = first 2 digits, MM = last 2 |
| `$3` | TASK | `string` (case-insensitive substring match against task dropdown) | first option in dropdown | If no match found, select the first non-empty option |
| `$4` | LOCATION | `office` \| `home` | `TIMEWATCH_DEFAULT_LOCATION` or `office` | Maps to remark using locale strings from config |

**Examples:**
- `/timewatch-fill:timewatch-fill` — today, 09:00-18:30, first task, office
- `/timewatch-fill:timewatch-fill tomorrow` — tomorrow, 09:00-18:30, first task, office
- `/timewatch-fill:timewatch-fill today 0830 1730` — today, 08:30-17:30, first task, office
- `/timewatch-fill:timewatch-fill yesterday 0900 1830 Cinema home` — yesterday, 09:00-18:30, Cinema task, home
- `/timewatch-fill:timewatch-fill this month` — all workdays this month with defaults
- `/timewatch-fill:timewatch-fill this week 0900 1830 MyProject office` — all workdays this week, MyProject task

## Configuration

Load credentials and preferences from the user's config directory:

!cat ~/.config/timewatch-fill/.env

### Required Variables

| Variable | Description | Where to Find |
|----------|-------------|---------------|
| `TIMEWATCH_COMPANY_ID` | Company number | TimeWatch login page, "company number" field |
| `TIMEWATCH_EMPLOYEE_ID` | Employee number | TimeWatch login page, "employee number" field |
| `TIMEWATCH_INTERNAL_EMPLOYEE_ID` | Internal employee ID used in URLs | From the `ee=` param in TimeWatch edit page URL after logging in |
| `TIMEWATCH_PASSWORD` | TimeWatch password | Your TimeWatch login password |

### Optional Defaults (override with positional arguments)

| Variable | Description | Default if unset |
|----------|-------------|------------------|
| `TIMEWATCH_DEFAULT_ENTRY` | Default entry time (HHMM) | `0900` |
| `TIMEWATCH_DEFAULT_EXIT` | Default exit time (HHMM) | `1830` |
| `TIMEWATCH_DEFAULT_LOCATION` | Default location (`office` or `home`) | `office` |
| `TIMEWATCH_WORKDAYS` | Comma-separated workday numbers (ISO: 1=Mon .. 7=Sun) | `7,1,2,3,4` (Sun-Thu) |
| `TIMEWATCH_LOCALE_OFFICE` | Remark string for "office" | `משרד` |
| `TIMEWATCH_LOCALE_HOME` | Remark string for "home" | `בית` |

**Examples:**
- Israeli schedule (default): `TIMEWATCH_WORKDAYS=7,1,2,3,4`
- US/EU Mon-Fri schedule: `TIMEWATCH_WORKDAYS=1,2,3,4,5`
- Custom 4-day week: `TIMEWATCH_WORKDAYS=1,2,3,4`

**If the `.env` file is missing or empty, STOP and tell the user:**

> TimeWatch credentials not configured. Run the following to set up:
>
> ```bash
> mkdir -p ~/.config/timewatch-fill
> cat > ~/.config/timewatch-fill/.env << 'EOF'
> TIMEWATCH_COMPANY_ID=your_company_id
> TIMEWATCH_EMPLOYEE_ID=your_employee_id
> TIMEWATCH_INTERNAL_EMPLOYEE_ID=your_internal_id
> TIMEWATCH_PASSWORD=your_password
>
> # Optional defaults (uncomment to customize):
> # TIMEWATCH_DEFAULT_ENTRY=0900
> # TIMEWATCH_DEFAULT_EXIT=1830
> # TIMEWATCH_DEFAULT_LOCATION=office
> # TIMEWATCH_WORKDAYS=7,1,2,3,4
> # TIMEWATCH_LOCALE_OFFICE=משרד
> # TIMEWATCH_LOCALE_HOME=בית
> EOF
> ```
>
> See `knowledge/USAGE.md` in this plugin for how to find each value.

## Determine Target Dates

After parsing the DATE argument:

- **"today"** — fill today only
- **"tomorrow"** — fill tomorrow only
- **"yesterday"** — fill yesterday only
- **"YYYY-MM-DD"** — fill that specific date
- **"this week"** — fill all workdays in the current week up to today
- **"this month"** — fill all workdays in the current month up to today

**Workdays** are determined by `TIMEWATCH_WORKDAYS` from the `.env` config. The value is a comma-separated list of ISO weekday numbers (1=Monday, 2=Tuesday, ..., 7=Sunday). Default if unset: `7,1,2,3,4` (Sun-Thu, Israeli schedule).

Use `date` command to resolve dates. For each date, get its ISO weekday number (`date +%u`) and skip if not in the workdays list.

## Step 1 — Get Browser Context

Call `mcp__claude-in-chrome__tabs_context_mcp` with `createIfEmpty: true`.

Create a new tab with `mcp__claude-in-chrome__tabs_create_mcp`.

## Step 2 — Navigate and Login

Navigate to `https://c.timewatch.co.il/punch/editwh.php`.

The site will redirect to the login page (punch.php) if not authenticated. Take a screenshot to check.

**If login form is visible** (fields for company/employee/password), fill and submit via JavaScript:

```javascript
document.querySelector('[name="comp"]').value = '<COMPANY_ID>';
document.querySelector('[name="name"]').value = '<EMPLOYEE_ID>';
document.querySelector('[name="pw"]').value = '<PASSWORD>';
document.querySelector('form').submit();
```

Wait 3 seconds, then take a screenshot to confirm login succeeded (should show the punch page with user name).

**If already logged in**, continue.

## Step 3 — Navigate to Monthly Overview

Navigate to the attendance edit page with the correct URL params:

```
https://c.timewatch.co.il/punch/editwh.php?ee=<INTERNAL_EMPLOYEE_ID>&e=<COMPANY_ID>&m=<MONTH>&y=<YEAR>
```

Where `<MONTH>` is numeric (1-12, no zero-padding) and `<YEAR>` is 4-digit.

Wait 2 seconds, take a screenshot to confirm the table loaded.

## Step 4 — Check Day Status Before Editing

For each target date, use JavaScript to inspect the table row:

```javascript
// Find row by the target date (DD-MM-YYYY format in the first cell).
// Replace <TARGET_DATE> with the actual date string, e.g., '28-03-2026'.
const targetDate = '<TARGET_DATE>';  // e.g., '28-03-2026'
const rows = document.querySelectorAll('tr.tr');
let targetRow = null;
for (const row of rows) {
  const firstCell = row.querySelector('td')?.textContent?.trim();
  if (firstCell && firstCell.startsWith(targetDate)) {
    targetRow = row;
    break;
  }
}
// Check if editable
if (targetRow) {
  const hasOnclick = targetRow.hasAttribute('onclick');
  const dataType = targetRow.getAttribute('data-type');
  const hasError = targetRow.hasAttribute('data-error');
  // hasOnclick=true and dataType="0" means editable
  // hasError=true means cannot edit (too old or future)
}
```

**Skip conditions** (report and move to next date):
- Row has `data-error` attribute — day is locked (too old or too far in future)
- Row has `data-type="1"` and no `onclick` — not editable
- Day's ISO weekday number is not in the `TIMEWATCH_WORKDAYS` list

## Step 5 — Open Edit Modal

Click the target row to open the edit modal:

```javascript
targetRow.click();
```

Wait 2 seconds for the modal to load. Take a screenshot to confirm the modal is visible.

## Step 6 — Check If Already Filled

Read the current form values:

```javascript
const ehh0 = document.querySelector('[name="ehh0"]')?.value;
const emm0 = document.querySelector('[name="emm0"]')?.value;
const xhh0 = document.querySelector('[name="xhh0"]')?.value;
const xmm0 = document.querySelector('[name="xmm0"]')?.value;
const hasBothTimes = ehh0 && emm0 && xhh0 && xmm0;
```

**If `hasBothTimes` is true** — the day already has entry and exit times. Close the modal and skip:

```javascript
document.querySelector('.modal-popup-btn-close').click();
```

Report: "Day DD-MM-YYYY already filled (HH:MM-HH:MM). Skipping."

## Step 7 — Resolve Task Value and Fill the Form

First, resolve the TASK argument to a numeric value by searching the dropdown:

```javascript
const taskSelect = document.querySelector('[name="task0"]');
const searchStr = '<TASK_ARG>'.toLowerCase();
let matchedValue = null;
for (const opt of taskSelect.options) {
  if (opt.text.toLowerCase().includes(searchStr)) {
    matchedValue = opt.value;
    break;
  }
}
// Fall back to first non-empty option if no match
if (!matchedValue) {
  for (const opt of taskSelect.options) {
    if (opt.value && opt.value !== '0') {
      matchedValue = opt.value;
      break;
    }
  }
}
const taskValue = matchedValue || taskSelect.options[1]?.value || '0';
```

Then set all fields:

```javascript
document.querySelector('[name="ehh0"]').value = '<ENTRY_HH>';
document.querySelector('[name="emm0"]').value = '<ENTRY_MM>';
document.querySelector('[name="xhh0"]').value = '<EXIT_HH>';
document.querySelector('[name="xmm0"]').value = '<EXIT_MM>';
taskSelect.value = taskValue;
taskSelect.dispatchEvent(new Event('change', { bubbles: true }));
document.querySelector('[name="remark"]').value = '<REMARK>';
```

Where `<REMARK>` is the locale string for the resolved location:
- `office` → value of `TIMEWATCH_LOCALE_OFFICE` from `.env` (default: `משרד`)
- `home` → value of `TIMEWATCH_LOCALE_HOME` from `.env` (default: `בית`)

**IMPORTANT:** The `dispatchEvent` call on the task select is required — without it the form may submit the wrong value.

Take a screenshot to visually confirm the values are set correctly before submitting.

## Step 8 — Submit

Click the update button:

```javascript
document.querySelector('.modal-popup-btn-confirm').click();
```

Wait 3 seconds for the AJAX save to complete. The modal may show a retroactive warning prompt — if so, click the confirm button on that prompt:

```javascript
const confirmBtn = document.querySelector('div.jqi .btn.confirmBtn');
if (confirmBtn) confirmBtn.click();
```

Wait 2 seconds, then take a screenshot.

## Step 9 — Verify Success

After submit, the modal should close and the monthly table should reload. Check that the target row now shows the entry/exit times. If the modal is still open, something went wrong.

**For multi-day fills:** After the modal closes, click the next target row and repeat Steps 5-8. Do NOT use the "next day" / "previous day" buttons in the modal — always close and click the correct row from the table to avoid navigation confusion.

## Step 10 — Report Results

After all target dates are processed, report a summary:

```
TimeWatch Fill Results:
- Filled: DD-MM-YYYY (09:00-18:30, MyProject, office)
- Filled: DD-MM-YYYY (08:30-17:30, Cinema City, home)
- Skipped: DD-MM-YYYY (already filled: 09:00-18:30)
- Skipped: DD-MM-YYYY (not a workday)
- Error: DD-MM-YYYY (day is locked)
```

## Edge Cases

- **Already filled** — skip without modifying, report existing times
- **Non-workday** — skip immediately (days not in `TIMEWATCH_WORKDAYS`)
- **Locked day (data-error)** — skip, report "day is locked"
- **Task not found** — fall back to first non-empty dropdown option, report the fallback
- **Retroactive warning popup** — click confirm to dismiss and continue
- **Login failed** — stop and report the error, do not retry
- **Modal doesn't open** — take screenshot, report error, do not retry
- **Holiday/special row** — skip if row is not clickable (no onclick)

## Form Field Reference

See `knowledge/FORM_FIELDS.md` for the complete field mapping. Key defaults:

| Field | Name | Default Value |
|-------|------|---------------|
| Entry hour | `ehh0` | First 2 digits of resolved entry time |
| Entry minute | `emm0` | Last 2 digits of resolved entry time |
| Exit hour | `xhh0` | First 2 digits of resolved exit time |
| Exit minute | `xmm0` | Last 2 digits of resolved exit time |
| Task | `task0` | first non-empty option in dropdown |
| Remark | `remark` | Locale string from config (default: `משרד` / `בית`) |
