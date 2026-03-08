#!/bin/bash
# SessionEnd hook: index session metadata for later searching.

set -euo pipefail

# Fail fast if jq is not available
if ! command -v jq &>/dev/null; then
  echo "ERROR: jq is required but not installed." >&2
  exit 1
fi

INDEX_FILE="$HOME/.claude/session-index.jsonl"

# Read hook input from stdin
input=$(cat)

session_id=$(echo "$input" | jq -r '.session_id // empty')
transcript_path=$(echo "$input" | jq -r '.transcript_path // empty')
cwd=$(echo "$input" | jq -r '.cwd // empty')
end_reason=$(echo "$input" | jq -r '.reason // empty')

# Guard: transcript must exist and be non-empty
if [[ -z "$transcript_path" ]] || [[ ! -f "$transcript_path" ]] || [[ ! -s "$transcript_path" ]]; then
  exit 0
fi

# Extract git branch from first entry that has one
branch=$(jq -r 'select(.gitBranch != null) | .gitBranch' "$transcript_path" 2>/dev/null | head -n 1)
branch="${branch:-unknown}"

# Extract first and last timestamps
started_at=$(jq -r 'select(.timestamp != null) | .timestamp' "$transcript_path" 2>/dev/null | head -n 1)
ended_at=$(jq -r 'select(.timestamp != null) | .timestamp' "$transcript_path" 2>/dev/null | tail -n 1)

# Extract first 5 user messages (string content only, truncated to 200 chars each)
user_prompts_json=$(jq -c '
  select(.type == "user" and (.message.content | type) == "string")
  | .message.content[:200]
' "$transcript_path" 2>/dev/null | head -n 5 | jq -sc '.')

# Guard: skip if no user messages found
prompt_count=$(echo "$user_prompts_json" | jq 'length')
if [[ "$prompt_count" -eq 0 ]]; then
  exit 0
fi

# Build summary from first user message, truncated to 150 chars
summary=$(echo "$user_prompts_json" | jq -r '.[0][:150]')

# Ensure index directory exists
mkdir -p "$(dirname "$INDEX_FILE")"

# Append index entry as a single JSON line
jq -nc \
  --arg sid "$session_id" \
  --arg project "$cwd" \
  --arg branch "$branch" \
  --arg started "$started_at" \
  --arg ended "$ended_at" \
  --arg reason "$end_reason" \
  --arg summary "$summary" \
  --argjson prompts "$user_prompts_json" \
  '{
    session_id: $sid,
    project: $project,
    branch: $branch,
    started_at: $started,
    ended_at: $ended,
    end_reason: $reason,
    summary: $summary,
    user_prompts: $prompts
  }' >> "$INDEX_FILE"

