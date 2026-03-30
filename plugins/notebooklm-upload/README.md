# notebooklm-upload

Batch upload local files from directories to Google NotebookLM notebooks. Supports filtering by file type, multiple directories, and dry-run mode.

## Why This Plugin?

NotebookLM's web UI only allows adding sources one file at a time. If you have a folder of PDFs, transcripts, markdown notes, or research papers that you want to feed into a notebook, you're looking at dozens of manual uploads with no progress tracking and no way to filter by type.

This plugin uploads an entire directory (or multiple directories) in a single command. It validates file sizes, filters by extension, skips hidden files and empty files, and gives you a clear report of what was uploaded, skipped, or failed. Dry-run mode lets you preview before committing.

## Install

```
/plugin install notebooklm-upload@claudecodelad
```

## Setup

First-time setup required. See [Setup Guide](docs/SETUP.md).

## Usage

```
/notebooklm-upload:notebooklm-upload <directory> [--notebook 'Name' | --notebook-id ID] [--include pdf,md] [--dry-run]
```

### Examples

| Command | What it does |
|---------|-------------|
| `/notebooklm-upload:notebooklm-upload ./docs --notebook "Research"` | Upload all files from `./docs` to a new notebook |
| `/notebooklm-upload:notebooklm-upload ./docs --notebook-id <ID>` | Upload to an existing notebook |
| `/notebooklm-upload:notebooklm-upload ./docs --notebook "Papers" --include pdf,md` | Upload only PDFs and markdown files |
| `/notebooklm-upload:notebooklm-upload ./dir1 ./dir2 --notebook "Combined"` | Upload from multiple directories |
| `/notebooklm-upload:notebooklm-upload ./docs --notebook "Test" --dry-run` | Preview what would be uploaded |

## Supported File Types

PDF, TXT, MD, DOCX, PPTX, MP3, WAV, PNG, JPG, JPEG

## Limits

- Max file size: 200MB per file (Google's limit)
- Max sources per notebook: 300 (Pro), 50 (Free)
- Empty files and hidden directories are automatically skipped

## Uninstall

```
/plugin uninstall notebooklm-upload@claudecodelad
```

## How It Works

Authenticates with Google via `notebooklm-py`, scans the target directories for supported files, validates sizes, creates or targets a notebook, and uploads each file as a NotebookLM source with rate-limiting between uploads.

## Prerequisites

- Python 3.10+ with `uv`
- Google account with NotebookLM access
