# md-to-gdoc

Convert markdown documents into properly formatted Google Docs using the Google Workspace CLI (`gws`). Supports custom format profiles extracted from reference Google Docs.

## Why This Plugin?

Markdown is the natural output format for Claude Code, but deliverables often need to be Google Docs. The alternatives all have problems:

- **Copy-paste into Google Docs**: loses heading hierarchy, breaks tables, drops formatting
- **Export to HTML then import**: partial formatting, manual cleanup still needed
- **Pandoc to DOCX then upload**: no Google Docs API integration, can't match an existing doc's style

This plugin converts markdown to a fully formatted Google Doc via the Docs API, with proper heading styles, tables with borders, bullet/numbered lists, cover pages, and a table of contents. The key differentiator is **format profiles**. Point it at any existing Google Doc, and it extracts the formatting rules (fonts, sizes, spacing, colors) into a reusable profile. Every future conversion matches that style automatically.

## Install

```
/plugin install md-to-gdoc@claudecodelad
```

## Setup

First-time setup required. See [Setup Guide](docs/SETUP.md).

## Usage

### Convert with default profile (SOW format)

```
/md-to-gdoc:md-to-gdoc path/to/file.md
```

### Convert with a saved profile

```
/md-to-gdoc:md-to-gdoc path/to/file.md --profile <name-or-path>
```

### Convert with a reference Google Doc

```
/md-to-gdoc:md-to-gdoc path/to/file.md --reference-doc <google-doc-url-or-id> --save-profile <name>
```

Extracts the formatting from the reference doc, saves the profile for reuse, then converts.

### Examples

| Command | What it does |
|---------|-------------|
| `/md-to-gdoc:md-to-gdoc report.md` | Convert with default SOW formatting |
| `/md-to-gdoc:md-to-gdoc report.md --profile corporate` | Convert with a saved profile |
| `/md-to-gdoc:md-to-gdoc report.md --reference-doc <url> --save-profile corporate` | Extract format from a Google Doc, save it, and convert |

## Uninstall

```
/plugin uninstall md-to-gdoc@claudecodelad
```

## How It Works

Parses markdown into structured blocks, generates Google Docs API `batchUpdate` requests, creates a new Google Doc via `gws`, applies all formatting in chunked batches, and returns the document URL. No external Python dependencies. Uses only the standard library and the `gws` CLI.

## Prerequisites

- Google Workspace CLI (`gws`) installed and authenticated
- Google Docs API and Google Drive API enabled in your GCP project
