# notebooklm-upload — Setup Guide

## Table of Contents

- [Prerequisites](#prerequisites)
- [Step 1 — Install Dependencies](#step-1--install-dependencies)
- [Step 2 — Authenticate with Google](#step-2--authenticate-with-google)
- [Verify Installation](#verify-installation)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Python 3.10+
- `uv` package manager
- A Google account with NotebookLM access
- A browser for OAuth consent

## Step 1 — Install Dependencies

Navigate to the plugin directory and sync:

```bash
cd "$(find ~/.claude/plugins -path '*/notebooklm-upload/pyproject.toml' -type f 2>/dev/null | head -1 | xargs dirname)"
uv sync
```

## Step 2 — Authenticate with Google

```bash
notebooklm login
```

This opens a browser window for Google OAuth consent. Once authenticated, verify with:

```bash
notebooklm status
```

## Verify Installation

List your existing notebooks to confirm everything works:

```bash
notebooklm list
```

Then try a dry run:

```
/notebooklm-upload:notebooklm-upload ./some-directory --notebook "Test" --dry-run
```

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Auth expired | Google OAuth token expired | Run `notebooklm login` again |
| Rate limited | Too many uploads too fast | Increase delay with `--delay 3.0` |
| File not uploading | Unsupported extension or empty file | Check file type is in the supported list and file is non-empty |
| `uv sync` fails | Missing Python version | Install Python 3.10+ and retry |
