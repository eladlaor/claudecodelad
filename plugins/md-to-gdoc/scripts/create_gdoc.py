#!/usr/bin/env python3
"""
End-to-end markdown to Google Doc pipeline.

Single command that:
1. Parses a markdown file into structured blocks
2. Generates Google Docs API batchUpdate JSON
3. Creates a new Google Doc via gws CLI
4. Applies all formatting via batchUpdate chunks
5. Optionally moves the doc to a Drive folder
6. Prints the Google Doc URL

Usage:
    python3 create_gdoc.py <markdown-file> [--profile <profile-json>] [--folder-id <drive-folder-id>]

Examples:
    python3 create_gdoc.py /path/to/SOW.md
    python3 create_gdoc.py /path/to/SOW.md --profile ../profiles/my-format.json
    python3 create_gdoc.py /path/to/SOW.md --folder-id 1a2B3cD4eF5gH6iJ7kL8mN
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

# Ensure sibling modules are importable regardless of caller's cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from format_profile import FormatProfile
from md_to_gdoc import MarkdownParser, DocsRequestBuilder, split_requests


GDOC_BASE_URL = "https://docs.google.com/document/d"


def check_gws() -> None:
    """Verify gws CLI is installed and accessible."""
    if not shutil.which("gws"):
        print("Error: gws CLI not found.", file=sys.stderr)
        print("Install with: npm install -g @googleworkspace/cli", file=sys.stderr)
        print("Then authenticate: gws auth login", file=sys.stderr)
        sys.exit(1)


def run_gws(args: list[str]) -> dict:
    """Run a gws command and return parsed JSON output."""
    cmd = ["gws"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print(f"Error: gws command timed out: {' '.join(cmd)}", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        print(f"Error: gws command failed: {' '.join(cmd)}", file=sys.stderr)
        print(f"stderr: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Error: could not parse gws output as JSON", file=sys.stderr)
        print(f"stdout: {result.stdout[:500]}", file=sys.stderr)
        sys.exit(1)


def create_document(title: str) -> str:
    """Create an empty Google Doc and return its document ID."""
    print(f"Creating Google Doc: \"{title}\"...", file=sys.stderr)
    response = run_gws([
        "docs", "documents", "create",
        "--json", json.dumps({"title": title})
    ])
    doc_id = response.get("documentId")
    if not doc_id:
        print(f"Error: no documentId in response: {json.dumps(response)[:300]}", file=sys.stderr)
        sys.exit(1)
    return doc_id


def apply_batch_update(doc_id: str, json_path: str, chunk_num: int, total_chunks: int) -> None:
    """Apply a single batchUpdate chunk to the document."""
    print(f"Applying formatting chunk {chunk_num + 1}/{total_chunks}...", file=sys.stderr)
    with open(json_path, "r", encoding="utf-8") as f:
        batch_json = f.read()

    run_gws([
        "docs", "documents", "batchUpdate",
        "--params", json.dumps({"documentId": doc_id}),
        "--json", batch_json
    ])


def move_to_folder(doc_id: str, folder_id: str) -> None:
    """Move the document to a specific Drive folder."""
    print(f"Moving doc to folder {folder_id}...", file=sys.stderr)
    run_gws([
        "drive", "files", "update",
        "--params", json.dumps({
            "fileId": doc_id,
            "addParents": folder_id,
            "removeParents": "root"
        })
    ])


def main():
    parser = argparse.ArgumentParser(description="Convert markdown to a formatted Google Doc (end-to-end)")
    parser.add_argument("markdown_file", help="Path to the markdown file")
    parser.add_argument("--profile", "-p", help="Path to a FormatProfile JSON file (default: SOW preset)")
    parser.add_argument("--folder-id", "-f", help="Google Drive folder ID to move the doc into")
    args = parser.parse_args()

    md_path = args.markdown_file
    if not os.path.exists(md_path):
        print(f"Error: file not found: {md_path}", file=sys.stderr)
        sys.exit(1)

    # Check gws
    check_gws()

    # Load profile
    if args.profile:
        if not os.path.exists(args.profile):
            print(f"Error: profile not found: {args.profile}", file=sys.stderr)
            sys.exit(1)
        profile = FormatProfile.from_json(args.profile)
    else:
        profile = FormatProfile.sow_default()

    # Read markdown
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse
    print("Parsing markdown...", file=sys.stderr)
    md_parser = MarkdownParser(content, profile)
    try:
        blocks = md_parser.parse()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    title = md_parser.title or "Untitled Document"
    print(f"Parsed {len(blocks)} blocks. Title: \"{title}\"", file=sys.stderr)

    # Build batchUpdate requests
    builder = DocsRequestBuilder(blocks, profile)
    requests = builder.build()
    chunks = split_requests(requests)
    print(f"Generated {len(requests)} API requests in {len(chunks)} chunk(s).", file=sys.stderr)

    # Write chunks to temp files
    tmp_dir = tempfile.mkdtemp(prefix="md-to-gdoc-")
    chunk_files = []
    for i, chunk in enumerate(chunks):
        path = os.path.join(tmp_dir, f"chunk_{i}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"requests": chunk}, f, ensure_ascii=False)
        chunk_files.append(path)

    # Create the Google Doc
    doc_id = create_document(title)

    # Apply formatting chunks in order
    for i, chunk_path in enumerate(chunk_files):
        apply_batch_update(doc_id, chunk_path, i, len(chunk_files))

    # Move to folder if requested
    if args.folder_id:
        move_to_folder(doc_id, args.folder_id)

    # Clean up temp files
    shutil.rmtree(tmp_dir, ignore_errors=True)

    # Output result
    doc_url = f"{GDOC_BASE_URL}/{doc_id}/edit"
    result = {
        "document_id": doc_id,
        "url": doc_url,
        "title": title,
        "profile": profile.name,
        "blocks": len(blocks),
        "requests": len(requests),
        "chunks": len(chunks),
    }
    print(json.dumps(result, indent=2))
    print(f"\nGoogle Doc created: {doc_url}", file=sys.stderr)


if __name__ == "__main__":
    main()
