# Markdown to Google Doc Converter

Converts a markdown document into a properly formatted Google Doc.
Formatting is driven by a **FormatProfile** -- either a preset (like the SoluGenAI SOW format)
or extracted from any reference Google Doc.

The user's request is: $ARGUMENTS

## Prerequisites

1. **Google Workspace CLI (`gws`)** is installed and on PATH
2. **Authentication** configured via `gws auth login`
3. **Google Docs API** and **Google Drive API** enabled in the GCP project

Run `which gws` to verify availability. If missing, tell the user:
"Install with: `npm install -g @googleworkspace/cli`, then authenticate: `gws auth login`"

### OAuth Setup (Manual Path)

`gws auth setup` delegates to `gcloud` under the hood. The OAuth callback server on
the localhost port sometimes fails to bind, causing the redirect to fail even though
Google's side succeeds (the auth code appears in the URL but nothing is listening).

If `gws auth setup` fails, set up credentials manually in two steps:

**Step 1 — Create OAuth credentials in the GCP Console (browser):**

1. Go to https://console.cloud.google.com
2. Create a project (or use an existing one)
3. Enable **Google Docs API** and **Google Drive API** (APIs & Services → Library)
4. Create OAuth credentials: APIs & Services → Credentials → Create Credentials → OAuth client ID → **Desktop app**
5. Download the client secret JSON file
6. Save it:
   ```bash
   mkdir -p ~/.config/gws
   cp ~/Downloads/client_secret_*.json ~/.config/gws/client_secret.json
   ```

**Step 2 — Authenticate with `gws` directly:**

```bash
gws auth login
```

This uses `gws`'s own callback server (different port from `gcloud`'s), which avoids
the port-binding issue.

## Locate Scripts

The pipeline scripts are shipped with this plugin. Find them by resolving the path
relative to this SKILL.md file:

```bash
# The scripts directory is two levels up from this SKILL.md
SCRIPTS_DIR="$(cd "$(dirname "$(find ~/.claude/plugins/marketplaces -path '*/md-to-gdoc/scripts/create_gdoc.py' -type f 2>/dev/null | head -1)")" && pwd)"
```

If not found in the marketplace path, fall back to:
```bash
SCRIPTS_DIR="$HOME/.claude/plugins/marketplaces/claudecodelad/plugins/md-to-gdoc/scripts"
```

Verify with: `test -f "$SCRIPTS_DIR/create_gdoc.py"`

## Usage Modes

### Mode A: Convert with default profile (SOW format)

```
/md-to-gdoc path/to/file.md
```

### Mode B: Convert with a saved profile

```
/md-to-gdoc path/to/file.md --profile <name-or-path>
```

### Mode C: Convert with a reference Google Doc (first time)

```
/md-to-gdoc path/to/file.md --reference-doc <google-doc-url-or-id> --save-profile <name>
```

Extracts the formatting from the reference doc, saves the profile, then converts.

## Execution Flow

### Phase 1: Validate Inputs

1. Parse arguments to get the markdown file path and mode.
2. Verify the file exists and is a `.md` file.
3. Verify `gws` CLI is available: `which gws`
4. Locate the scripts directory (see above).

### Phase 2: Resolve Format Profile (if --reference-doc or --profile given)

**If `--reference-doc <url-or-id>` is given:**
```bash
cd "$SCRIPTS_DIR"
python3 format_extractor.py "<url-or-id>" --name "<save-profile-name>"
```

**If `--profile <name>` is given:**
Resolve the profile path. Check `$SCRIPTS_DIR/../profiles/<name>.json` first,
then treat as a direct file path.

### Phase 3: Run the Pipeline

The entire conversion runs as a single command:

```bash
cd "$SCRIPTS_DIR"
python3 create_gdoc.py "<markdown-file>" [--profile "<profile-json-path>"] [--folder-id "<folder-id>"]
```

This single script handles everything:
- Parses the markdown into structured blocks
- Generates Google Docs API batchUpdate requests
- Creates a new Google Doc via `gws`
- Applies all formatting chunks in order
- Moves the doc to a Drive folder (if `--folder-id` given)
- Cleans up temp files
- Prints a JSON result to stdout and the Google Doc URL to stderr

### Phase 4: Present Result

From the JSON output, extract `url` and present it to the user.

## Error Handling

- `gws` not installed: print installation instructions, stop.
- Auth failure (`invalid_grant`): tell the user to run `gws auth login` and re-authenticate. If the localhost callback fails (known bug), use the manual token exchange script at `$SCRIPTS_DIR/../troubleshooting/gws_manual_auth.sh`.
- Malformed markdown: warn and proceed with best-effort conversion.
- `batchUpdate` failure: print error response and request JSON for debugging.
- Profile not found: list available profiles, stop.

## Available Profiles

Profiles are stored in `$SCRIPTS_DIR/../profiles/`. To list:
```bash
ls "$SCRIPTS_DIR/../profiles/"
```

The default SOW profile is built into the code and does not require a JSON file.
