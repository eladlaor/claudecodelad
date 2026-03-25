# TIMEWATCH FORM FIELD REFERENCE

## Table of Contents

- [Summary](#summary)
- [URLs](#urls)
- [Login Form](#login-form)
- [Monthly Overview Table](#monthly-overview-table)
- [Edit Modal Fields](#edit-modal-fields)
- [Modal Buttons](#modal-buttons)
- [Row Data Attributes](#row-data-attributes)

## Summary

Reference for TimeWatch (`c.timewatch.co.il`) UI elements, form fields, and navigation patterns. Used by the `timewatch-fill` skill for claude-in-chrome browser automation.

## URLs

| Page | URL | Notes |
|------|-----|-------|
| Login | `https://c.timewatch.co.il/punch/punch.php` | Redirected here if not authenticated |
| Monthly overview | `https://c.timewatch.co.il/punch/editwh.php?ee={INTERNAL_ID}&e={COMPANY_ID}&m={MONTH}&y={YEAR}` | Main attendance table |

## Login Form

| Field | Name | Description |
|-------|------|-------------|
| Company ID | `comp` | Numeric company identifier |
| Employee ID | `name` | Numeric employee identifier |
| Password | `pw` | Employee password |

Submit by calling `document.querySelector('form').submit()`.

## Monthly Overview Table

- Each day is a `<tr class="tr">` row
- First cell contains date in `DD-MM-YYYY X` format (X = Hebrew day letter)
- Rows have CSS classes `type0` / `type1` for alternating colors
- Editable rows have an `onclick` attribute that calls `showModal('','editwh2.php?...')`
- Non-editable rows have `data-error="show-error"` and a `data-msg` with the reason
- Pencil icon (`pen.png`) in the leftmost column is decorative — clicking the ROW opens the modal

## Edit Modal Fields

The edit modal opens as a Bootstrap-style popup over the table. It contains up to 5 time-entry slots (0-4).

### Time Entry Slots

| Field | Name Pattern | Description | Default Value |
|-------|-------------|-------------|---------------|
| Entry hour | `ehh{N}` | Hour of entry (00-23) | `09` |
| Entry minute | `emm{N}` | Minute of entry (00-59) | `00` |
| Exit hour | `xhh{N}` | Hour of exit (00-23) | `18` |
| Exit minute | `xmm{N}` | Minute of exit (00-59) | `30` |

Where `{N}` is the slot index (0-4). Slot 0 is the primary entry.

### Task Fields

| Field | Name Pattern | Description |
|-------|-------------|-------------|
| Task | `task{N}` | Select dropdown for project |
| Task description | `taskdescr{N}` | Text input for task description |

Key task values:
- `81686` = SolugenAI (223)
- `89833` = SoluGen- infrastructure (290)
- `0` = "choose" (empty/unselected)

### Other Fields

| Field | Name | Description | Default |
|-------|------|-------------|---------|
| Remark | `remark` | Free text notes | `משרד` |
| Absence reason | `excuse` | Select dropdown | `0` (none) |
| Absence type | `atype` | Select dropdown | `0` (none) |

## Modal Buttons

| Button | Selector | Text | Action |
|--------|----------|------|--------|
| Update/Save | `.modal-popup-btn-confirm` | עדכן | Calls `submitPopupModal()` which validates and POSTs via AJAX |
| Close | `.modal-popup-btn-close` | סגור | Closes modal without saving |
| Previous day | `#prevDay` | יום קודם | Saves and navigates to previous day |
| Next day | `#nextDay` | יום הבא | Saves and navigates to next day |
| X (close) | `.close` | x | Closes modal |

## Row Data Attributes

| Attribute | Values | Meaning |
|-----------|--------|---------|
| `data-type` | `0` | Normal editable day |
| `data-type` | `1` | Weekend, holiday, or locked day |
| `data-error` | `show-error` | Day cannot be edited (shows error on click) |
| `data-msg` | Hebrew text | Error message explaining why day is locked |
| `onclick` | `javascript:showModal(...)` | Opens edit modal (only on editable rows) |
