#!/bin/bash
# SessionStart hook: inject today's date, time, and timezone into Claude's context.

today_dow=$(date +"%A")
today_full=$(date +"%B %d, %Y")
current_time=$(date +"%H:%M")
timezone=$(date +"%Z %:z")

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Today is ${today_dow}, ${today_full}. Current time: ${current_time} (${timezone})."
  }
}
EOF

exit 0
