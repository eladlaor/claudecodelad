---
name: merge
description: >
  Merge multiple git worktree branches into the current branch with conflict-aware resolution.
  Use when the user says "merge worktrees", "merge all worktrees", "combine worktrees",
  "merge branches from worktrees", "merge my feature branches", or wants to integrate
  multiple worktree branches into a single branch. Handles ordered merges, conflict
  resolution, post-merge verification, test fixture fixes, and worktree cleanup.
allowed-tools: Bash Read Edit Write Grep Glob AskUserQuestion TaskCreate TaskUpdate TaskList
---

# Merge Worktrees

Merge all active worktree branches into the current branch with zero-conflict resolution, ordered by dependency, and verified end-to-end.

## Critical Rules

- **NEVER run `git push`.**
- **NEVER auto-commit fixture fixes** — leave them as uncommitted changes for user review.
- **NEVER blindly pick one side of a conflict.** Read the FULL file from BOTH sides before resolving.
- **NEVER use `git merge` without `--no-ff`** — preserve merge commit history.
- Always read `.claude/CLAUDE.md` and architecture docs first to understand the project before merging.

## Step 1 — Understand the Project

1. Read `.claude/CLAUDE.md` to understand architecture, key directories, and conventions.
2. Read any architecture docs referenced in CLAUDE.md (e.g., `knowledge/ARCHITECTURE.md`).
3. Identify the tech stack: backend language, frontend framework, test runner, package manager.

## Step 2 — Discover Worktrees

1. Run `git worktree list` and `git branch | grep worktree` to find all worktree branches.
2. For each worktree branch, run `git log --oneline <base>...<branch>` to see what changed.
3. Run `git diff --stat <base>...<branch>` for each to understand file-level scope.
4. **Categorize each branch by actual file changes** — use `git diff --stat` output to determine dominant patterns:
   - **Infrastructure/config**: Changes predominantly in config files (`pyproject.toml`, `Cargo.toml`, `package.json`, `.gitignore`, CI/CD files, docker files, logger/provider setup)
   - **Backend logic**: Changes predominantly in backend source files (API endpoints, services, models, DB)
   - **Frontend**: Changes predominantly in frontend source files (components, hooks, styles, pages)
   - **Tests**: Changes predominantly in test files (`test_*`, `*_test.*`, `*.spec.*`, `conftest.py`)

   Do NOT assume categories from directory names alone — infer from actual changed file paths and extensions.

## Step 3 — Plan Merge Order

Present the proposed merge order to the user using `AskUserQuestion`. Default ordering:

1. Infrastructure/config changes first (least likely to conflict)
2. Backend logic changes (may depend on infrastructure)
3. Frontend changes (large refactors become canonical base for smaller additions)
4. Backend flow/routing changes (may touch files from step 2-3)
5. Tests LAST (fixtures can be adjusted for all prior changes)

Explain the rationale. Let the user confirm or reorder.

## Step 4 — Pre-Merge Setup

1. Check `git status` — working tree must be clean. If dirty:
   - If only files under `.claude/` are modified, run `git checkout -- .claude/` to discard session-local changes
   - If other files are dirty, ask the user what to do (stash, commit, or discard)
2. Record the current HEAD commit: `git rev-parse HEAD`

## Step 5 — Merge Each Branch

For each branch in the planned order:

### 5a — Attempt Merge

```bash
git checkout -- .claude/ 2>/dev/null
git merge <branch> --no-ff -m "merge <branch>: <brief description of changes>"
```

### 5b — If Clean Merge

Move to verification (Step 5d).

### 5c — If Conflicts

1. Run `git diff --name-only --diff-filter=U` to list conflicted files.
2. For EACH conflicted file:

   **Any file under `.claude/`** — ALWAYS resolve by keeping HEAD's version:
   - Read the file, find the conflict markers
   - Keep everything from HEAD, discard worktree-specific entries
   - These are session-specific files that don't need to be preserved across merges

   **All other files** — Resolve mindfully:
   - Read the FULL file with conflict markers
   - Read the file from HEAD: `git show HEAD:<path>`
   - Read the file from the merging branch: `git show <branch>:<path>`
   - Understand what EACH side changed and WHY
   - Prefer the current branch's structure as the base (it has all prior merges)
   - Surgically add the incoming branch's NEW functionality
   - Watch for:
     - Import conflicts (combine both sides' imports)
     - Function body conflicts (understand which version has more recent logic)
     - State/constant additions (keep both)
     - Structural refactors (if one side refactored, use refactored version + apply other's changes)

3. Stage resolved files: `git add <file>`
4. Complete the merge: `git commit --no-edit -m "merge <branch>: <description>"`

### 5d — Post-Merge Verification (Auto-Detected)

After each merge, detect the tech stack and run appropriate verification:

**Tech stack detection** (check in order, use first match):

1. Check `.claude/CLAUDE.md` for explicit build/test commands — prefer these over auto-detection
2. `pyproject.toml` exists -> Python project:
   - Import check: `python -c "from src.main import app; print('ok')"` (adjust import path based on project structure)
3. `package.json` exists -> Node/JS project:
   - Build check: `npm run build` (or `yarn build` if `yarn.lock` exists, `pnpm build` if `pnpm-lock.yaml` exists)
4. `Cargo.toml` exists -> Rust project:
   - Build check: `cargo check`
5. `go.mod` exists -> Go project:
   - Build check: `go build ./...`
6. If none detected, ask the user what verification command to run.

If verification fails, investigate and fix before proceeding to the next merge.

## Step 6 — Run Tests (Auto-Detected)

After ALL merges are complete, detect and run the appropriate test suite:

**Test command detection** (check in order):

1. Check `.claude/CLAUDE.md` for explicit test commands — prefer these
2. `pyproject.toml` exists -> `uv run pytest tests/ -v --tb=short`
3. `package.json` exists -> `npm test` (or `yarn test` / `pnpm test` based on lockfile)
4. `Cargo.toml` exists -> `cargo test`
5. `go.mod` exists -> `go test ./...`
6. If none detected, ask the user

### If Tests Fail

Failures are likely caused by cross-feature interactions. Common patterns:

- **New mandatory fields** (e.g., a merge added a required field, but test fixtures don't include it) — add the field to test factories/fixtures
- **Changed routing logic** — update test assertions
- **New imports or constants** — add missing imports to test files
- **Changed function signatures** — update test calls

Fix the fixtures but **DO NOT commit them** — leave as uncommitted changes for user review.

Re-run tests until all pass.

## Step 7 — Clean Up Worktrees

Use `git worktree list --porcelain` to get actual worktree paths, then remove each:

```bash
git worktree list --porcelain
```

Parse the output to extract the actual filesystem path for each worktree, then:

```bash
git worktree remove <actual-worktree-path>
```

For each worktree. If removal fails (e.g., dirty worktree), use `--force` after confirming with the user.

**Do NOT hardcode paths like `.claude/worktrees/<name>`** — always use `git worktree list` output for the real path.

## Step 8 — Final Report

Show the user:

1. `git log --oneline` showing all merge commits since the base
2. `git diff --stat` showing any uncommitted changes (fixture fixes)
3. `git status --short` for full picture
4. Summary: how many worktrees merged, how many conflicts resolved, test results
