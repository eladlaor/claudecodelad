#!/usr/bin/env python3
"""
Format Extractor: Extract a FormatProfile from a reference Google Doc.

Uses the Google Workspace CLI (gws) to fetch the full document structure,
then analyzes paragraph styles, text styles, table formatting, and named
styles to build a reusable FormatProfile.

Usage:
    python3 format_extractor.py <document-id-or-url> [--output <profile-path>] [--name <profile-name>]

Examples:
    python3 format_extractor.py 1FUDKLNT3p6GGfIFaymiL_SauQYWlQpgeWNnmejN9mag --name default-sow
    python3 format_extractor.py "https://docs.google.com/document/d/1FUDKLNT3p6.../edit" --output profiles/my-format.json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Optional

# Ensure sibling modules are importable regardless of caller's cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from format_profile import (
    FormatProfile,
    CoverPageConfig,
    HeadingConfig,
    BodyConfig,
    TableConfig,
    TocConfig,
    HorizontalRuleConfig,
    PlaceholderConfig,
    RGBColor,
)


PROFILES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profiles")


def extract_doc_id(input_str: str) -> str:
    """Extract a Google Doc ID from a URL or return the raw ID."""
    # Match URLs like https://docs.google.com/document/d/<ID>/edit...
    match = re.search(r"/document/d/([a-zA-Z0-9_-]+)", input_str)
    if match:
        return match.group(1)
    # Assume it's already a raw ID
    return input_str.strip()


def fetch_document(doc_id: str) -> dict:
    """Fetch the full document structure via gws CLI."""
    cmd = [
        "gws", "docs", "documents", "get",
        "--params", json.dumps({"documentId": doc_id})
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        print(json.dumps({"error": "gws CLI not found. Install with: npm install -g @googleworkspace/cli"}))
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(json.dumps({"error": "gws command timed out after 30 seconds"}))
        sys.exit(1)

    if result.returncode != 0:
        print(json.dumps({"error": f"gws command failed: {result.stderr.strip()}"}))
        sys.exit(1)

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Failed to parse gws output: {e}"}))
        sys.exit(1)


def extract_rgb(color_obj: Optional[dict]) -> Optional[dict]:
    """Extract RGB dict from a Google Docs color object."""
    if not color_obj:
        return None
    rgb = color_obj.get("color", {}).get("rgbColor", {})
    if not rgb:
        return None
    return {
        "red": rgb.get("red", 0.0),
        "green": rgb.get("green", 0.0),
        "blue": rgb.get("blue", 0.0),
    }


def extract_font_size(text_style: dict) -> Optional[float]:
    """Extract font size in points from a text style."""
    fs = text_style.get("fontSize")
    if fs and fs.get("unit") == "PT":
        return fs.get("magnitude")
    return None


def extract_spacing(dimension: Optional[dict]) -> Optional[float]:
    """Extract spacing value in points."""
    if not dimension:
        return None
    if dimension.get("unit") == "PT":
        return dimension.get("magnitude")
    return None


class FormatExtractor:
    """Analyzes a Google Doc's structure to build a FormatProfile."""

    def __init__(self, doc: dict):
        self.doc = doc
        self.body = doc.get("body", {})
        self.named_styles = doc.get("namedStyles", {}).get("styles", [])
        # For tab-based documents
        if not self.body and "tabs" in doc:
            first_tab = doc["tabs"][0] if doc["tabs"] else {}
            tab_body = first_tab.get("documentTab", {})
            self.body = tab_body.get("body", {})
            self.named_styles = tab_body.get("namedStyles", {}).get("styles", [])

        self.content_elements = self.body.get("content", [])

    def extract(self, profile_name: str = "extracted") -> FormatProfile:
        """Extract a complete FormatProfile from the document."""
        profile = FormatProfile(name=profile_name)

        # Extract from named styles (most reliable source)
        self._extract_named_styles(profile)

        # Extract from actual document content (fills in what named styles miss)
        self._extract_from_content(profile)

        return profile

    def _extract_named_styles(self, profile: FormatProfile) -> None:
        """Extract heading/body styles from the document's named style definitions."""
        for style in self.named_styles:
            style_type = style.get("namedStyleType", "")
            text_style = style.get("textStyle", {})
            para_style = style.get("paragraphStyle", {})

            font_size = extract_font_size(text_style)
            bold = text_style.get("bold")
            font_family = text_style.get("weightedFontFamily", {}).get("fontFamily")

            alignment = para_style.get("alignment")
            space_above = extract_spacing(para_style.get("spaceAbove"))
            space_below = extract_spacing(para_style.get("spaceBelow"))

            if style_type == "HEADING_1":
                if font_size is not None:
                    profile.heading_1.font_size = font_size
                if bold is not None:
                    profile.heading_1.bold = bold
                if alignment:
                    profile.heading_1.alignment = alignment
                if space_above is not None:
                    profile.heading_1.space_before = space_above
                if space_below is not None:
                    profile.heading_1.space_after = space_below

            elif style_type == "HEADING_2":
                if font_size is not None:
                    profile.heading_2.font_size = font_size
                if bold is not None:
                    profile.heading_2.bold = bold
                if alignment:
                    profile.heading_2.alignment = alignment
                if space_above is not None:
                    profile.heading_2.space_before = space_above
                if space_below is not None:
                    profile.heading_2.space_after = space_below

            elif style_type == "NORMAL_TEXT":
                if font_size is not None:
                    profile.body.font_size = font_size
                if font_family:
                    profile.font_family = font_family
                line_spacing = para_style.get("lineSpacing")
                if line_spacing:
                    profile.body.line_spacing = line_spacing / 100.0
                if space_below is not None:
                    profile.body.space_after = space_below

    def _extract_from_content(self, profile: FormatProfile) -> None:
        """Walk the document content to extract styles not captured by named styles."""
        cover_paragraphs = []
        found_first_heading = False
        found_table = False

        for element in self.content_elements:
            if "paragraph" in element:
                para = element["paragraph"]
                para_style = para.get("paragraphStyle", {})
                style_type = para_style.get("namedStyleType", "")

                # Collect cover page paragraphs (before first heading)
                if not found_first_heading and style_type not in ("HEADING_1", "HEADING_2"):
                    cover_paragraphs.append(para)
                elif style_type in ("HEADING_1", "HEADING_2"):
                    found_first_heading = True

                # Extract TOC link colors
                for elem in para.get("elements", []):
                    text_style = elem.get("textRun", {}).get("textStyle", {})
                    link = text_style.get("link")
                    if link and link.get("bookmarkId"):
                        color = extract_rgb(text_style.get("foregroundColor"))
                        if color:
                            profile.toc.link_color = color

            elif "table" in element and not found_table:
                found_table = True
                self._extract_table_styles(element["table"], profile)

        # Analyze cover page paragraphs
        self._extract_cover_styles(cover_paragraphs, profile)

    def _extract_cover_styles(self, paragraphs: list, profile: FormatProfile) -> None:
        """Extract cover page formatting from the first few paragraphs."""
        for i, para in enumerate(paragraphs):
            elements = para.get("elements", [])
            if not elements:
                continue

            first_run = elements[0].get("textRun", {})
            text_style = first_run.get("textStyle", {})
            para_style = para.get("paragraphStyle", {})

            font_size = extract_font_size(text_style)
            alignment = para_style.get("alignment", "START")
            bold = text_style.get("bold", False)
            italic = text_style.get("italic", False)

            # Heuristic: largest centered bold text is the title
            if font_size and font_size >= 20 and alignment == "CENTER" and bold:
                profile.cover.title_size = font_size
                profile.cover.title_alignment = alignment
                profile.cover.title_bold = bold
            elif font_size and font_size >= 14 and alignment == "CENTER" and bold:
                profile.cover.subtitle_size = font_size
                profile.cover.subtitle_alignment = alignment
            elif font_size and font_size >= 12 and alignment == "CENTER":
                profile.cover.project_size = font_size
                profile.cover.project_alignment = alignment
            elif italic and font_size and font_size <= 10:
                profile.cover.confidentiality_size = font_size
                profile.cover.confidentiality_italic = True
                profile.cover.confidentiality_alignment = alignment

    def _extract_table_styles(self, table: dict, profile: FormatProfile) -> None:
        """Extract table formatting from the first table in the document."""
        rows = table.get("tableRows", [])
        if not rows:
            return

        # Header row (first row)
        header_row = rows[0]
        for cell in header_row.get("tableCells", []):
            cell_style = cell.get("tableCellStyle", {})

            # Background color
            bg = extract_rgb(cell_style.get("backgroundColor"))
            if bg:
                profile.table.header_bg_color = bg

            # Border
            for border_key in ("borderBottom", "borderTop", "borderLeft", "borderRight"):
                border = cell_style.get(border_key)
                if border:
                    border_color = extract_rgb(border.get("color"))
                    if border_color:
                        profile.table.border_color = border_color
                    width = border.get("width", {})
                    if width.get("unit") == "PT" and width.get("magnitude"):
                        profile.table.border_width = width["magnitude"]
                    break  # one border is enough

            # Padding
            for pad_key in ("paddingTop", "paddingBottom", "paddingLeft", "paddingRight"):
                pad = cell_style.get(pad_key)
                if pad and pad.get("unit") == "PT":
                    profile.table.cell_padding = pad["magnitude"]
                    break

            # Header text style
            for content_elem in cell.get("content", []):
                para = content_elem.get("paragraph", {})
                for elem in para.get("elements", []):
                    ts = elem.get("textRun", {}).get("textStyle", {})
                    fs = extract_font_size(ts)
                    if fs:
                        profile.table.cell_font_size = fs
                    if ts.get("bold") is not None:
                        profile.table.header_bold = ts["bold"]
            break  # first header cell is enough


def main():
    parser = argparse.ArgumentParser(description="Extract a FormatProfile from a reference Google Doc")
    parser.add_argument("document", help="Google Doc ID or URL")
    parser.add_argument("--output", "-o", help="Output path for the profile JSON (default: profiles/<name>.json)")
    parser.add_argument("--name", "-n", default="extracted", help="Profile name (default: extracted)")
    args = parser.parse_args()

    doc_id = extract_doc_id(args.document)
    print(f"Fetching document {doc_id}...", file=sys.stderr)

    doc = fetch_document(doc_id)
    print(f"Document title: {doc.get('title', 'Unknown')}", file=sys.stderr)

    extractor = FormatExtractor(doc)
    profile = extractor.extract(profile_name=args.name)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        os.makedirs(PROFILES_DIR, exist_ok=True)
        output_path = os.path.join(PROFILES_DIR, f"{args.name}.json")

    profile.to_json(output_path)

    result = {
        "profile_name": profile.name,
        "profile_path": output_path,
        "source_doc_id": doc_id,
        "source_doc_title": doc.get("title", "Unknown"),
        "font_family": profile.font_family,
        "heading_1_size": profile.heading_1.font_size,
        "heading_2_size": profile.heading_2.font_size,
        "body_size": profile.body.font_size,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
