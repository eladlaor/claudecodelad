#!/bin/bash
# SessionStart hook: detect if user is inside a git worktree and inject context.

# Exit silently if not in a git repo
git rev-parse --git-dir >/dev/null 2>&1 || { echo '{}'; exit 0; }

GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)
GIT_COMMON_DIR=$(git rev-parse --git-common-dir 2>/dev/null)
BRANCH=$(git branch --show-current 2>/dev/null)

# Normalize paths for comparison
GIT_DIR_REAL=$(cd "$GIT_DIR" 2>/dev/null && pwd)
GIT_COMMON_DIR_REAL=$(cd "$GIT_COMMON_DIR" 2>/dev/null && pwd)

# Collect all worktrees (excluding bare entries)
WORKTREE_COUNT=$(git worktree list 2>/dev/null | wc -l)
# Subtract 1 for the main worktree
EXTRA_WORKTREES=$((WORKTREE_COUNT - 1))

if [ "$GIT_DIR_REAL" != "$GIT_COMMON_DIR_REAL" ]; then
  # We are inside a worktree (not the main repo)
  MAIN_REPO=$(git -C "$GIT_COMMON_DIR_REAL" rev-parse --show-toplevel 2>/dev/null || dirname "$GIT_COMMON_DIR_REAL")
  CURRENT_DIR=$(pwd)

  # List sibling worktrees (excluding current and main)
  SIBLINGS=""
  while IFS= read -r line; do
    WT_PATH=$(echo "$line" | awk '{print $1}')
    WT_BRANCH=$(echo "$line" | sed -n 's/.*\[\(.*\)\].*/\1/p')
    [ "$WT_PATH" = "$CURRENT_DIR" ] && continue
    [ "$WT_PATH" = "$MAIN_REPO" ] && continue
    if [ -n "$SIBLINGS" ]; then
      SIBLINGS="${SIBLINGS}, ${WT_BRANCH} (${WT_PATH})"
    else
      SIBLINGS="${WT_BRANCH} (${WT_PATH})"
    fi
  done < <(git worktree list 2>/dev/null)

  CONTEXT="You are working inside a git WORKTREE (not the main repository).\\n"
  CONTEXT="${CONTEXT}Branch: ${BRANCH}\\n"
  CONTEXT="${CONTEXT}Worktree path: ${CURRENT_DIR}\\n"
  CONTEXT="${CONTEXT}Main repository: ${MAIN_REPO}\\n"
  if [ -n "$SIBLINGS" ]; then
    CONTEXT="${CONTEXT}Other active worktrees: ${SIBLINGS}\\n"
  fi
  CONTEXT="${CONTEXT}\\nThis is a persistent worktree for parallel development — NOT a temporary Claude agent worktree."

  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "${CONTEXT}"
  }
}
EOF

elif [ "$EXTRA_WORKTREES" -gt 0 ]; then
  # We are in the main repo, but worktrees exist
  WORKTREE_LIST=""
  COUNT=0
  while IFS= read -r line; do
    WT_PATH=$(echo "$line" | awk '{print $1}')
    WT_BRANCH=$(echo "$line" | sed -n 's/.*\[\(.*\)\].*/\1/p')
    MAIN_TOPLEVEL=$(git rev-parse --show-toplevel 2>/dev/null)
    [ "$WT_PATH" = "$MAIN_TOPLEVEL" ] && continue
    COUNT=$((COUNT + 1))
    [ "$COUNT" -gt 5 ] && { WORKTREE_LIST="${WORKTREE_LIST} (and more...)"; break; }
    if [ -n "$WORKTREE_LIST" ]; then
      WORKTREE_LIST="${WORKTREE_LIST}, ${WT_BRANCH}"
    else
      WORKTREE_LIST="${WT_BRANCH}"
    fi
  done < <(git worktree list 2>/dev/null)

  CONTEXT="This repo has ${EXTRA_WORKTREES} active worktree(s): ${WORKTREE_LIST}. Use /worktree-manager:worktree to manage them or /worktree-manager:merge to merge them back."

  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "${CONTEXT}"
  }
}
EOF

else
  # No worktrees — output empty JSON, no context injected
  echo '{}'
fi

exit 0
