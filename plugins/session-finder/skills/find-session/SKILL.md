# Find Session

Search past Claude Code sessions by natural language description.

## Instructions

The user wants to find a past Claude Code session. Their search description is: $ARGUMENTS

### Steps

1. **Check the index exists.** Read `~/.claude/session-index.jsonl`. If it doesn't exist, tell the user: "No session index found yet. The index is built automatically when sessions end. Start and exit a session with the session-finder plugin installed to begin indexing."

2. **Extract search keywords** from the user's description. Identify the most distinctive words (skip common words like "the", "a", "that", "session", "where", "when").

3. **Search the index.** Use `grep` (case-insensitive) on `~/.claude/session-index.jsonl` with the extracted keywords. Try multiple keywords individually and collect all matching lines. Parse each matching line as JSON with `jq`.

4. **Deduplicate.** If the same `session_id` appears multiple times, keep only the latest entry (last occurrence in the file).

5. **Rank results.** Use your reasoning to rank which sessions best match the user's description based on:
   - Summary text relevance
   - User prompts content
   - Project path
   - Branch name
   - Recency (prefer recent sessions when relevance is similar)

6. **Present results.** Show the top 5 matches (or fewer if less exist) in this format:

   For each match:
   ```
   **Session:** `<session_id>`
   **Project:** <project path> (branch: <branch>)
   **Date:** <started_at formatted nicely> — <duration if calculable>
   **Summary:** <summary text>
   **Key prompts:** <first 2-3 user prompts, abbreviated>
   **Resume:** `claude --resume <session_id>`
   ```

7. **No matches.** If nothing matches, tell the user and suggest they try broader search terms.

## Example

User runs: `/session-finder:find-session plugin for session indexing`

Claude searches the index, finds matching sessions, and presents ranked results with resume commands.
