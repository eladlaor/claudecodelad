---
name: worktree
description: Create and manage persistent git worktrees for parallel Claude Code development on separate branches. Enables running multiple Claude Code sessions on different feature branches simultaneously.
allowed-tools: Bash(*), Read
---

# Git Worktree Manager

Manage persistent git worktrees to enable parallel Claude Code sessions working on different branches.

## Important: This Is NOT Claude's Built-in Worktree

Claude Code has built-in `EnterWorktree`/`ExitWorktree` that create **temporary, session-scoped** worktrees inside `.claude/worktrees/` for agent isolation. Those are automatically cleaned up when the agent finishes.

This skill manages **persistent** worktrees as **sibling directories** for parallel human+AI development across sessions. Completely different use case.

## Why Worktrees?

Running multiple Claude Code sessions from the same directory on different branches causes conflicts — they share the same `.git` state and working tree. Git worktrees solve this by creating separate working directories for each branch, all sharing the same repository history.

## Directory Pattern: Sibling Directories

This skill uses **sibling directory** naming: `../<project>-<branch>`

Example:
```
~/Code/
├── langrag/                    # Main repo (main branch)
├── langrag-slm-integration/    # Worktree (slm-integration branch)
└── langrag-feature-xyz/        # Worktree (feature-xyz branch)
```

**Why sibling directories (not hidden `.worktrees/` or centralized `~/worktrees/`)?**

1. **IDE/Editor friendly**: Each worktree appears as a first-class project directory
2. **Natural navigation**: `cd ../langrag-slm-integration && claude` just works
3. **Claude Code clarity**: No nested path confusion — each worktree is clearly its own project root
4. **Visual proximity**: `ls ~/Code/` shows main repo and all feature worktrees together
5. **Community standard**: Most git worktree guides recommend this pattern

## Git Operations in Worktrees

When working in a worktree (not the main repository):
- `git add`, `git commit`, `git push` are ALLOWED
- Push to the worktree's feature branch
- NEVER force push
- NEVER push to main/master from a worktree

## Commands

Parse the user's argument: `/worktree-manager:worktree <command> [branch-name]`

Commands:
- `create <branch-name>` — Create a new worktree for a branch
- `list` — List all active worktrees
- `remove <branch-name>` — Remove a worktree
- `status` — Show status of all worktrees (uncommitted changes, etc.)

If no command is provided, show usage help.

---

## Step 1: Determine Context

First, get the repository root and current branch:

```bash
git rev-parse --show-toplevel
git branch --show-current
```

Store the project root path and project name (last segment of path).

**Worktree-inception guard:** If the current directory is itself a worktree (check: `git rev-parse --git-common-dir` differs from `--git-dir`), and the user runs `create`, warn them:

> You're currently inside worktree `<branch>`. Creating from here will branch off `<branch>`, not `main`. To branch from `main`, run this from the main repository at `<main-repo-path>`.

Proceed only if the user confirms.

---

## Step 2: Execute Command

### CREATE Command

When user runs `create <branch-name>`:

1. **Validate branch name**: Ensure it's a valid git branch name (no spaces, special chars)

2. **Determine worktree path**: Use sibling directory pattern `../<project-name>-<branch-name>`
   - Get project name: `basename $(git rev-parse --show-toplevel)`
   - Get parent dir: `dirname $(git rev-parse --show-toplevel)`
   - Worktree path: `<parent-dir>/<project-name>-<branch-name>`
   - Example: `/home/user/Code/langrag` + `slm-integration` -> `/home/user/Code/langrag-slm-integration`
   - Branch names with `/` get flattened: `feature/auth` -> `langrag-feature-auth`

3. **Check if worktree already exists**:
   ```bash
   git worktree list | grep "<branch-name>"
   ```
   If exists, inform user and show the existing path.

4. **Check if branch exists**:
   ```bash
   git branch --list <branch-name>
   git branch -r --list "origin/<branch-name>"
   ```

5. **Create the worktree**:
   - If local branch exists:
     ```bash
     git worktree add <worktree-path> <branch-name>
     ```
   - If only remote branch exists:
     ```bash
     git worktree add <worktree-path> <branch-name>
     ```
   - If branch doesn't exist (create new):
     ```bash
     git worktree add -b <branch-name> <worktree-path>
     ```

6. **Output success message**:
   ```
   Worktree created successfully!

   Branch: <branch-name>
   Path: <full-worktree-path>

   To start a parallel Claude Code session:
   1. Open a NEW terminal window/tab
   2. cd <full-worktree-path>
   3. claude

   The new session will work on '<branch-name>' independently.
   ```

### LIST Command

When user runs `list`:

1. Get all worktrees:
   ```bash
   git worktree list
   ```

2. Format output as a table showing path, branch, and whether it's the main worktree.

### REMOVE Command

When user runs `remove <branch-name>`:

1. **Find the worktree path** for the branch using `git worktree list --porcelain`:
   ```bash
   git worktree list --porcelain
   ```
   Parse the output to find the worktree entry matching the branch name and extract its actual path.

2. **Check for uncommitted changes** in that worktree:
   ```bash
   git -C <worktree-path> status --porcelain
   ```

3. **If dirty (has changes)**: STOP and warn the user:
   ```
   Worktree has uncommitted changes!

   Path: <worktree-path>
   Changes:
   <list of changed files>

   Please commit or stash changes before removing, or explicitly confirm deletion.
   ```

4. **If clean or user confirms**: Remove the worktree:
   ```bash
   git worktree remove <worktree-path>
   ```

5. **Ask if user wants to delete the branch too**:
   ```bash
   git branch -d <branch-name>  # safe delete (only if merged)
   ```

### STATUS Command

When user runs `status`:

1. List all worktrees with their status:
   ```bash
   git worktree list
   ```

2. For each worktree, check status:
   ```bash
   git -C <path> status --porcelain | wc -l
   ```

3. Output formatted table:
   ```
   | Path                          | Branch          | Status        |
   |-------------------------------|-----------------|---------------|
   | /home/user/Code/langrag       | main            | clean         |
   | /home/user/Code/langrag-slm   | slm-integration | 3 uncommitted |
   ```

---

## Error Handling

- If not in a git repository: "Error: Not in a git repository"
- If worktree creation fails: Show the git error message
- If branch name invalid: "Error: Invalid branch name"
- If trying to remove main worktree: "Error: Cannot remove the main worktree"

---

## Examples

**Create a worktree for SLM integration work:**
```
/worktree-manager:worktree create slm-integration
```

**List all active worktrees:**
```
/worktree-manager:worktree list
```

**Clean up a feature branch worktree:**
```
/worktree-manager:worktree remove feature-xyz
```
