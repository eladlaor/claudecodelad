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
| `$1` | ENTRY_TIME | `HHMM` (exactly 4 digits) | `0900` | Entry time. Split: HH = first 2 digits, MM = last 2 |
| `$2` | EXIT_TIME | `HHMM` (exactly 4 digits) | `1830` | Exit time. Split: HH = first 2 digits, MM = last 2 |
| `$3` | TASK | `string` (case-insensitive substring match against task dropdown) | `SolugenAI` | If no dropdown option contains this string, fall back to SolugenAI |
| `$4` | LOCATION | `office` \| `home` | `office` | Maps to remark: `office` -> `משרד`, `home` -> `בית` |

**Examples:**
- `/timewatch-fill:timewatch-fill` — today, 09:00-18:30, SolugenAI, office
- `/timewatch-fill:timewatch-fill tomorrow` — tomorrow, 09:00-18:30, SolugenAI, office
- `/timewatch-fill:timewatch-fill today 0830 1730` — today, 08:30-17:30, SolugenAI, office
- `/timewatch-fill:timewatch-fill yesterday 0900 1830 Cinema home` — yesterday, 09:00-18:30, Cinema City task, home
- `/timewatch-fill:timewatch-fill this month` — all workdays this month with defaults
- `/timewatch-fill:timewatch-fill this week 0900 1830 Taglit office` — all workdays this week, Taglit task

## Credentials

Load credentials from the user's config directory:

!cat ~/.config/timewatch-fill/.env

This file must define 4 variables:

| Variable | Description | Where to Find |
|----------|-------------|---------------|
| `TIMEWATCH_COMPANY_ID` | Company number | TimeWatch login page, "company number" field |
| `TIMEWATCH_EMPLOYEE_ID` | Employee number | TimeWatch login page, "employee number" field |
| `TIMEWATCH_INTERNAL_EMPLOYEE_ID` | Internal employee ID used in URLs | From the `ee=` param in TimeWatch edit page URL after logging in |
| `TIMEWATCH_PASSWORD` | TimeWatch password | Your TimeWatch login password |

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
- **"this week"** — fill all workdays (Sun-Thu) in the current week up to today
- **"this month"** — fill all workdays (Sun-Thu) in the current month up to today

Israeli workdays: Sunday (isoweekday 7), Monday-Thursday (isoweekday 1-4). Friday and Saturday are NOT workdays.

Use `date` command to resolve dates. Skip any date that is Friday or Saturday.

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
// Find row by date string (DD-MM-YYYY format in the first cell)
const rows = document.querySelectorAll('tr.tr');
let targetRow = null;
for (const row of rows) {
  const firstCell = row.querySelector('td')?.textContent?.trim();
  if (firstCell && firstCell.startsWith('DD-MM-YYYY')) {
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
- Day is Friday (isoweekday 5) or Saturday (isoweekday 6)

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
// Fall back to SolugenAI (81686) if no match
const taskValue = matchedValue || '81686';
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

Where `<REMARK>` is `משרד` for `office` or `בית` for `home`.

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
- Filled: DD-MM-YYYY (09:00-18:30, SolugenAI, office)
- Filled: DD-MM-YYYY (08:30-17:30, Cinema City, home)
- Skipped: DD-MM-YYYY (already filled: 09:00-18:30)
- Skipped: DD-MM-YYYY (Friday - not a workday)
- Error: DD-MM-YYYY (day is locked)
```

## Edge Cases

- **Already filled** — skip without modifying, report existing times
- **Friday/Saturday** — skip immediately
- **Locked day (data-error)** — skip, report "day is locked"
- **Task not found** — fall back to SolugenAI (81686), report the fallback
- **Retroactive warning popup** — click confirm to dismiss and continue
- **Login failed** — stop and report the error, do not retry
- **Modal doesn't open** — take screenshot, report error, do not retry
- **Holiday/special row** — skip if row is not clickable (no onclick)

## Form Field Reference

See `references/form-fields.md` for the complete field mapping. Key defaults:

| Field | Name | Default Value |
|-------|------|---------------|
| Entry hour | `ehh0` | `09` |
| Entry minute | `emm0` | `00` |
| Exit hour | `xhh0` | `18` |
| Exit minute | `xmm0` | `30` |
| Task | `task0` | `81686` (SolugenAI 223) |
| Remark | `remark` | `משרד` (office) / `בית` (home) |
