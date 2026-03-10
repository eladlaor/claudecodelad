#!/bin/bash
# SessionEnd hook: index session metadata for later searching.

set -euo pipefail

# Fail fast if jq is not available
if ! command -v jq &>/dev/null; then
  echo "ERROR: jq is required but not installed." >&2
  exit 1
fi

INDEX_FILE="$HOME/.claude/session-index.jsonl"
CLEANUP_MARKER="$HOME/.claude/.session-index-cleaned"

# --- Fix 4: One-time cleanup of leaked summarization entries ---
if [[ -f "$INDEX_FILE" ]] && [[ ! -f "$CLEANUP_MARKER" ]]; then
  leaked_count=$(grep -c "Summarize this Claude Code session" "$INDEX_FILE" 2>/dev/null || echo "0")
  if [[ "$leaked_count" -gt 0 ]]; then
    tmp_index="${INDEX_FILE}.cleanup.$$"
    grep -v "Summarize this Claude Code session" "$INDEX_FILE" > "$tmp_index" 2>/dev/null || true
    mv "$tmp_index" "$INDEX_FILE"
  fi
  touch "$CLEANUP_MARKER"
fi

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

# Guard: skip sessions spawned by this hook's own LLM summarization call.
# The `claude -p` summarizer produces a session whose only user prompt starts
# with our known summarization instruction.
first_user_msg=$(jq -sc '[.[] | select(.type == "user" and (.message.content | type) == "string") | .message.content][0] // ""' "$transcript_path" 2>/dev/null || echo "")
if [[ "$first_user_msg" == *"Summarize this Claude Code session"* ]]; then
  exit 0
fi

# --- Fix 2: Defensive metadata extraction ---
# Wrap in a subshell so failures don't kill the hook
metadata=$(jq -sc '
  # --- Fix 1: Reusable filter for "real" user prompts ---
  # Excludes: isMeta messages, XML-tag hook injections, summarization prompts
  def real_prompt:
    select(
      .type == "user"
      and (.message.content | type) == "string"
      and (.isMeta | not)
      and (.message.content | startswith("<") | not)
      and (.message.content | test("Summarize this Claude Code session") | not)
    ) | .message.content[:200];

  {
    session_name: (map(select(.slug != null) | .slug) | last // ""),
    branch: (map(select(.gitBranch != null) | .gitBranch) | first // "unknown"),
    started_at: (map(select(.timestamp != null) | .timestamp) | first // ""),
    ended_at: (map(select(.timestamp != null) | .timestamp) | last // ""),
    all_real_prompts: [.[] | real_prompt],
    first_prompt: ([.[] | real_prompt] | first // ""),
    last_prompt: ([.[] | real_prompt] | last // ""),
    files_touched: [.[] | select(.type == "assistant") | .message.content[]? | select(.type == "tool_use" and (.name == "Write" or .name == "Edit")) | .input.file_path] | unique
  }
' "$transcript_path" 2>/dev/null || true)

# If metadata extraction failed, exit gracefully
if [[ -z "$metadata" ]] || ! echo "$metadata" | jq -e . &>/dev/null; then
  exit 0
fi

session_name=$(echo "$metadata" | jq -r '.session_name')
branch=$(echo "$metadata" | jq -r '.branch')
started_at=$(echo "$metadata" | jq -r '.started_at')
ended_at=$(echo "$metadata" | jq -r '.ended_at')
first_prompt=$(echo "$metadata" | jq -r '.first_prompt')
last_prompt=$(echo "$metadata" | jq -r '.last_prompt')
files_touched_json=$(echo "$metadata" | jq -c '.files_touched')

# Guard: skip if no real user messages found
if [[ -z "$first_prompt" ]]; then
  exit 0
fi

# --- Fix 3: Strengthened summarization session detection ---
# Secondary guard: if there's exactly 1 real prompt and it matches the
# summarization pattern, this is a summarizer session that slipped through.
prompt_count=$(echo "$metadata" | jq -r '.all_real_prompts | length')
if [[ "$prompt_count" -eq 1 ]]; then
  only_prompt=$(echo "$metadata" | jq -r '.all_real_prompts[0]')
  if [[ "$only_prompt" == *"Summarize this Claude Code session"* ]]; then
    exit 0
  fi
fi

# Generate LLM summary using Haiku (cheap and fast)
# Falls back to first prompt if claude CLI unavailable or fails
summary=""
if command -v claude &>/dev/null; then
  all_user_prompts=$(echo "$metadata" | jq -c '.all_real_prompts')
  summary=$(echo "$all_user_prompts" | env -u CLAUDECODE claude -p \
    --no-session-persistence \
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
