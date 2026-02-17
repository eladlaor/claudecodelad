#!/bin/bash
# SessionStart hook: inject today's date into Claude's context.

today_dow=$(date +"%A")
today_full=$(date +"%B %d, %Y")

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Today is ${today_dow}, ${today_full}."
  }
}
EOF

exit 0
