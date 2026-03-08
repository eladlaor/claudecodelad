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

# Extract metadata in a single jq pass over the transcript
metadata=$(jq -sc '
  {
    session_name: (map(select(.slug != null) | .slug) | last // ""),
    branch: (map(select(.gitBranch != null) | .gitBranch) | first // "unknown"),
    started_at: (map(select(.timestamp != null) | .timestamp) | first // ""),
    ended_at: (map(select(.timestamp != null) | .timestamp) | last // ""),
    first_prompt: ([.[] | select(.type == "user" and (.message.content | type) == "string") | .message.content[:200]] | first // ""),
    last_prompt: ([.[] | select(.type == "user" and (.message.content | type) == "string") | .message.content[:200]] | last // ""),
    files_touched: [.[] | select(.type == "assistant") | .message.content[]? | select(.type == "tool_use" and (.name == "Write" or .name == "Edit")) | .input.file_path] | unique
  }
' "$transcript_path" 2>/dev/null)

session_name=$(echo "$metadata" | jq -r '.session_name')
branch=$(echo "$metadata" | jq -r '.branch')
started_at=$(echo "$metadata" | jq -r '.started_at')
ended_at=$(echo "$metadata" | jq -r '.ended_at')
first_prompt=$(echo "$metadata" | jq -r '.first_prompt')
last_prompt=$(echo "$metadata" | jq -r '.last_prompt')
files_touched_json=$(echo "$metadata" | jq -c '.files_touched')

# Guard: skip if no user messages found
if [[ -z "$first_prompt" ]]; then
  exit 0
fi

# Generate LLM summary using Haiku (cheap and fast)
# Falls back to first prompt if claude CLI unavailable or fails
summary=""
if command -v claude &>/dev/null; then
  all_user_prompts=$(jq -sc '[.[] | select(.type == "user" and (.message.content | type) == "string") | .message.content[:200]]' "$transcript_path" 2>/dev/null)
  summary=$(echo "$all_user_prompts" | env -u CLAUDECODE claude -p \
    --model claude-haiku-4-5-20251001 \
    --max-turns 1 \
    "Summarize this Claude Code session in one sentence (max 120 chars). These are the user prompts. Output ONLY the summary, no quotes, no preamble:" 2>/dev/null || true)
fi
if [[ -z "$summary" ]]; then
  summary="${first_prompt:0:120}"
fi

# Ensure index directory exists
mkdir -p "$(dirname "$INDEX_FILE")"

# Append index entry as a single JSON line
jq -nc \
  --arg sid "$session_id" \
  --arg name "$session_name" \
  --arg project "$cwd" \
  --arg branch "$branch" \
  --arg started "$started_at" \
  --arg ended "$ended_at" \
  --arg reason "$end_reason" \
  --arg summary "$summary" \
  --arg first_prompt "$first_prompt" \
  --arg last_prompt "$last_prompt" \
  --argjson files "$files_touched_json" \
  '{
    session_id: $sid,
    session_name: $name,
    project: $project,
    branch: $branch,
    started_at: $started,
    ended_at: $ended,
    end_reason: $reason,
    summary: $summary,
    first_prompt: $first_prompt,
    last_prompt: $last_prompt,
    files_touched: $files
  }' >> "$INDEX_FILE"
