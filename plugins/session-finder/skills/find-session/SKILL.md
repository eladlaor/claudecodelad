# Find Session

Search past Claude Code sessions by natural language description.

## Instructions

The user wants to find a past Claude Code session. Their request is: $ARGUMENTS

If the request includes a number like "top 10" or "last 20", use that as the result count. Otherwise default to 5.

### Steps

1. **Check the index exists.** Read `~/.claude/session-index.jsonl`. If it doesn't exist, tell the user: "No session index found yet. The index is built automatically when sessions end. Start and exit a session with the session-finder plugin installed to begin indexing."

2. **Extract search keywords** from the user's description. Identify the most distinctive words (skip common words like "the", "a", "that", "session", "where", "when").

3. **Search the index.** Use `grep` (case-insensitive) on `~/.claude/session-index.jsonl` with the extracted keywords. Try multiple keywords individually and collect all matching lines. Parse each matching line as JSON with `jq`.

4. **Deduplicate.** If the same `session_id` appears multiple times, keep only the latest entry (last occurrence in the file).

5. **Rank results.** Use your reasoning to rank which sessions best match the user's description based on:
   - Summary (LLM-generated one-liner when available)
   - Session name (if renamed via /rename)
   - First and last prompt content
   - Files touched (strong signal for code-related searches)
   - Project path
   - Branch name
   - Recency (prefer recent sessions when relevance is similar)

6. **Present results.** Show the top N matches (where N is the requested count, default 5; fewer if less exist) in this format:

   For each match:
   ```
   **Session:** `<session_id>` (<session_name if available>)
   **Project:** <project path> (branch: <branch>)
   **Date:** <started_at formatted nicely> — <duration if calculable>
   **Summary:** <summary>
   **First prompt:** <first prompt, abbreviated>
   **Last prompt:** <last prompt, abbreviated>
   **Files touched:** <list of files, or "none" if empty>
   **Resume:** `claude --resume <session_id>`
   ```

7. **No matches.** If nothing matches, tell the user and suggest they try broader search terms.

## Example

User runs: `/session-finder:find-session plugin for session indexing`

Claude searches the index, finds matching sessions, and presents ranked results with resume commands.
