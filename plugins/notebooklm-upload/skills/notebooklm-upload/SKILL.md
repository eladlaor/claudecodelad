---
name: notebooklm-upload
description: >-
  Batch upload local files from directories to Google NotebookLM notebooks.
  Use when the user says "upload to notebooklm", "notebooklm upload",
  "batch upload notebooklm", "add files to notebooklm", "notebooklm sources",
  or wants to upload a directory of files as NotebookLM sources.
argument-hint: "<directory> [--notebook 'Name' | --notebook-id ID] [--include pdf,md] [--dry-run]"
allowed-tools:
  - Bash(cd * && uv run notebooklm-upload *)
  - Bash(uv run notebooklm-upload *)
  - Bash(uv sync *)
  - Bash(notebooklm login*)
  - Bash(notebooklm list*)
  - Bash(notebooklm status*)
  - Bash(ls *)
  - Bash(find * -type f*)
---

# NotebookLM Batch Upload

Upload all supported files from one or more local directories to a Google NotebookLM notebook.

The user's request is: $ARGUMENTS

## Prerequisites

1. **notebooklm-py** must be installed. The plugin manages this via `uv sync`.
2. **Authentication** must be active. Run `notebooklm login` if needed (opens browser for Google OAuth).
3. Check auth status: `notebooklm status`

## Setup

Locate the installed plugin directory and sync dependencies:

```bash
PLUGIN_DIR="$(find ~/.claude/plugins -path '*/notebooklm-upload/pyproject.toml' -type f 2>/dev/null | head -1 | xargs dirname)"
cd "$PLUGIN_DIR" && uv sync
```

If the user has never logged in:
```bash
notebooklm login
```

## Usage

All commands must run from the plugin directory. First resolve the path:

```bash
PLUGIN_DIR="$(find ~/.claude/plugins -path '*/notebooklm-upload/pyproject.toml' -type f 2>/dev/null | head -1 | xargs dirname)"
```

### Create a new notebook and upload files
```bash
cd "$PLUGIN_DIR" && uv run notebooklm-upload /path/to/dir --notebook "My Notebook"
```

### Upload to an existing notebook
First, list notebooks to get the ID:
```bash
notebooklm list
```
Then upload:
```bash
cd "$PLUGIN_DIR" && uv run notebooklm-upload /path/to/dir --notebook-id <ID>
```

### Filter by file type
```bash
cd "$PLUGIN_DIR" && uv run notebooklm-upload /path/to/dir --notebook "Research" --include pdf,md,txt
```

### Multiple directories
```bash
cd "$PLUGIN_DIR" && uv run notebooklm-upload /path/dir1 /path/dir2 --notebook "Combined"
```

### Dry run (preview without uploading)
```bash
cd "$PLUGIN_DIR" && uv run notebooklm-upload /path/to/dir --notebook "Test" --dry-run
```

## Supported File Types

PDF, TXT, MD, DOCX, PPTX, MP3, WAV, PNG, JPG, JPEG

## Limits

- Max file size: 200MB per file
- Max sources per notebook: 300 (Pro), 50 (Free)
- Empty files and hidden directories are automatically skipped

## Troubleshooting

- **Auth expired**: Run `notebooklm login` again
- **Rate limited**: Increase delay with `--delay 3.0`
- **File not uploading**: Check extension is supported and file is not empty
