#!/usr/bin/env python3
"""
Markdown to Google Docs batchUpdate JSON converter.

Parses a markdown file and generates Google Docs API batchUpdate request JSON
needed to create a properly formatted Google Doc. Formatting is driven by a
FormatProfile (extracted from a reference Google Doc or using a preset).

Usage:
    python3 md_to_gdoc.py <markdown-file> [--profile <profile-json>] [--output <dir-or-file>]

Output:
    - Writes JSON file(s) containing batchUpdate requests
    - Prints metadata JSON to stdout: {"title": "...", "batch_update_files": [...], ...}
"""

import json
import re
import sys
import os
import argparse
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional

from format_profile import FormatProfile


# ---------------------------------------------------------------------------
# Constants (non-formatting)
# ---------------------------------------------------------------------------

MAX_REQUESTS_PER_CHUNK = 200


# ---------------------------------------------------------------------------
# Block types and data structures
# ---------------------------------------------------------------------------

class BlockType(StrEnum):
    COVER_TITLE = "cover_title"
    COVER_SUBTITLE = "cover_subtitle"
    COVER_PROJECT = "cover_project"
    COVER_META = "cover_meta"
    COVER_CONFIDENTIALITY = "cover_confidentiality"
    TOC_HEADING = "toc_heading"
    TOC_ENTRY = "toc_entry"
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    PARAGRAPH = "paragraph"
    BULLET = "bullet"
    NUMBERED = "numbered"
    TABLE = "table"
    HORIZONTAL_RULE = "horizontal_rule"
    PLACEHOLDER = "placeholder"
    EMPTY_LINE = "empty_line"


@dataclass
class InlineSpan:
    """A span of text with optional inline formatting."""
    text: str
    bold: bool = False
    italic: bool = False


@dataclass
class Block:
    """A parsed block of content."""
    block_type: BlockType
    text: str = ""
    spans: list[InlineSpan] = field(default_factory=list)
    level: int = 0
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    link_target: str = ""


# ---------------------------------------------------------------------------
# Markdown Parser
# ---------------------------------------------------------------------------

class MarkdownParser:
    """
    Parses markdown into structured blocks.

    The parser is format-agnostic for body content (headings, paragraphs,
    tables, lists). Cover page and TOC parsing use configurable patterns
    from the FormatProfile.
    """

    def __init__(self, content: str, profile: FormatProfile):
        self.lines = content.split("\n")
        self.blocks: list[Block] = []
        self.title = ""
        self.profile = profile

    def parse(self) -> list[Block]:
        sections = self._split_by_horizontal_rules()
        if not sections:
            raise ValueError("Markdown has no content")

        # Section 0: Cover page
        self._parse_cover_page(sections[0])

        # Section 1: TOC (if it looks like a TOC)
        if len(sections) > 1 and self._is_toc_section(sections[1]):
            self._parse_toc(sections[1])
            body_start = 2
        else:
            body_start = 1

        # Remaining sections: body
        for section in sections[body_start:]:
            self.blocks.append(Block(block_type=BlockType.HORIZONTAL_RULE))
            self._parse_body_section(section)

        return self.blocks

    def _split_by_horizontal_rules(self) -> list[list[str]]:
        """Split markdown into sections delimited by --- lines."""
        sections: list[list[str]] = []
        current: list[str] = []
        for line in self.lines:
            if line.strip() == "---":
                sections.append(current)
                current = []
            else:
                current.append(line)
        if current:
            sections.append(current)
        return sections

    def _is_toc_section(self, lines: list[str]) -> bool:
        """Check if a section looks like a Table of Contents."""
        toc_heading = self.profile.toc.heading_text.lower()
        for line in lines:
            stripped = line.strip().lower()
            if toc_heading in stripped:
                return True
            # Also detect by link patterns
            if re.match(r"\[.+\]\(#.+\)", stripped):
                return True
        return False

    def _parse_cover_page(self, lines: list[str]):
        """Parse the cover page section."""
        non_empty = [l for l in lines if l.strip()]
        if not non_empty:
            return

        confidentiality_pattern = self.profile.cover.confidentiality_pattern

        # Line 1: Main title
        self.title = non_empty[0].strip()
        self.blocks.append(Block(block_type=BlockType.COVER_TITLE, text=self.title))

        # Line 2: Subtitle (if present)
        if len(non_empty) > 1:
            self.blocks.append(Block(
                block_type=BlockType.COVER_SUBTITLE,
                text=non_empty[1].strip()
            ))

        # Line 3: Project name (if present)
        if len(non_empty) > 2:
            self.blocks.append(Block(
                block_type=BlockType.COVER_PROJECT,
                text=non_empty[2].strip()
            ))

        # Remaining lines: meta (version, date) then confidentiality
        if len(non_empty) > 3:
            remaining = non_empty[3:]
            confidentiality_idx = None
            for i, line in enumerate(remaining):
                if re.match(confidentiality_pattern, line.strip()):
                    confidentiality_idx = i
                    break

            meta_lines = remaining[:confidentiality_idx] if confidentiality_idx is not None else remaining
            for ml in meta_lines:
                self.blocks.append(Block(block_type=BlockType.COVER_META, text=ml.strip()))

            self.blocks.append(Block(block_type=BlockType.EMPTY_LINE))

            if confidentiality_idx is not None:
                conf_text = " ".join(
                    l.strip() for l in remaining[confidentiality_idx:]
                ).strip()
                self.blocks.append(Block(
                    block_type=BlockType.COVER_CONFIDENTIALITY,
                    text=conf_text
                ))

        self.blocks.append(Block(block_type=BlockType.HORIZONTAL_RULE))

    def _parse_toc(self, lines: list[str]):
        """Parse the Table of Contents section."""
        toc_heading = self.profile.toc.heading_text
        self.blocks.append(Block(block_type=BlockType.TOC_HEADING, text=toc_heading))
        self.blocks.append(Block(block_type=BlockType.EMPTY_LINE))

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Skip the TOC heading itself
            if line.lower().replace("*", "").strip() == toc_heading.lower():
                continue
            # Match [Title](#anchor)
            match = re.match(r"\[(.+?)\]\(#(.+?)\)", line)
            if match:
                self.blocks.append(Block(
                    block_type=BlockType.TOC_ENTRY,
                    text=match.group(1),
                    link_target=match.group(2)
                ))

    def _parse_body_section(self, lines: list[str]):
        """Parse a body section into heading, paragraph, table, list blocks."""
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                i += 1
                continue

            # H1: any line starting with "# "
            if stripped.startswith("# ") and not stripped.startswith("## "):
                text = stripped[2:].strip()
                self.blocks.append(Block(block_type=BlockType.HEADING_1, text=text))
                i += 1
                continue

            # H2: starts with "## "
            if stripped.startswith("## "):
                text = stripped[3:].strip()
                self.blocks.append(Block(block_type=BlockType.HEADING_2, text=text))
                i += 1
                continue

            # Screenshot placeholder
            if stripped.startswith("[Screenshot placeholder:") or stripped.startswith("[screenshot placeholder:"):
                self.blocks.append(Block(block_type=BlockType.PLACEHOLDER, text=stripped))
                i += 1
                continue

            # Table
            if stripped.startswith("|"):
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i].strip())
                    i += 1
                self._parse_table(table_lines)
                continue

            # Bullet list: * or -
            if re.match(r"^(\s*)[*\-]\s", line):
                indent = len(line) - len(line.lstrip())
                level = indent // self.profile.body.indent_per_level
                text = re.sub(r"^\s*[*\-]\s+", "", line).strip()
                spans = self._parse_inline(text)
                self.blocks.append(Block(
                    block_type=BlockType.BULLET, text=text, spans=spans, level=level
                ))
                i += 1
                continue

            # Numbered list
            if re.match(r"^(\s*)\d+\.\s", line):
                indent = len(line) - len(line.lstrip())
                level = indent // self.profile.body.indent_per_level
                text = re.sub(r"^\s*\d+\.\s+", "", line).strip()
                spans = self._parse_inline(text)
                self.blocks.append(Block(
                    block_type=BlockType.NUMBERED, text=text, spans=spans, level=level
                ))
                i += 1
                continue

            # Regular paragraph
            spans = self._parse_inline(stripped)
            self.blocks.append(Block(
                block_type=BlockType.PARAGRAPH, text=stripped, spans=spans
            ))
            i += 1

    def _parse_table(self, lines: list[str]):
        """Parse a markdown table into a Block."""
        if len(lines) < 2:
            return

        def split_cells(line: str) -> list[str]:
            cells = line.strip("|").split("|")
            return [c.strip() for c in cells]

        headers = split_cells(lines[0])
        data_start = 1
        if len(lines) > 1 and re.match(r"^[\s|:\-]+$", lines[1]):
            data_start = 2

        rows = [split_cells(lines[j]) for j in range(data_start, len(lines))]
        self.blocks.append(Block(
            block_type=BlockType.TABLE,
            headers=headers,
            rows=rows
        ))

    @staticmethod
    def _parse_inline(text: str) -> list[InlineSpan]:
        """Parse inline bold/italic markers into spans."""
        spans: list[InlineSpan] = []
        pattern = re.compile(r"(\*\*(.+?)\*\*|\*(.+?)\*|([^*]+))")
        for match in pattern.finditer(text):
            if match.group(2):
                spans.append(InlineSpan(text=match.group(2), bold=True))
            elif match.group(3):
                spans.append(InlineSpan(text=match.group(3), italic=True))
            elif match.group(4):
                spans.append(InlineSpan(text=match.group(4)))
        return spans if spans else [InlineSpan(text=text)]


# ---------------------------------------------------------------------------
# Google Docs API Request Builder
# ---------------------------------------------------------------------------

class DocsRequestBuilder:
    """
    Builds Google Docs API batchUpdate requests from parsed blocks.

    All formatting is driven by a FormatProfile instance.
    The Google Docs API is index-based: we track the current insertion
    index and build insert + style requests sequentially.
    """

    def __init__(self, blocks: list[Block], profile: FormatProfile):
        self.blocks = blocks
        self.profile = profile
        self.requests: list[dict] = []
        self.index = 1  # Google Docs body starts at index 1
        self.bookmarks: dict[str, int] = {}
        self.toc_entries: list[dict] = []

    def build(self) -> list[dict]:
        """Build all batchUpdate requests."""
        text_requests: list[dict] = []
        style_requests: list[dict] = []

        for block in self.blocks:
            method_name = f"_build_{block.block_type}"
            method = getattr(self, method_name, None)
            if method is None:
                continue
            txt_reqs, sty_reqs = method(block)
            text_requests.extend(txt_reqs)
            style_requests.extend(sty_reqs)

        # Build TOC bookmark links
        link_requests = self._build_toc_links()

        return text_requests + style_requests + link_requests

    def _build_toc_links(self) -> list[dict]:
        """Create link requests connecting TOC entries to heading bookmarks."""
        requests = []
        for entry in self.toc_entries:
            target = entry["target"]
            if target in self.bookmarks:
                # Create bookmark at the heading
                bookmark_id = f"bm_{target}"
                heading_index = self.bookmarks[target]
                requests.append({
                    "createNamedRange": {
                        "name": bookmark_id,
                        "range": {
                            "startIndex": heading_index,
                            "endIndex": heading_index + 1
                        }
                    }
                })
        return requests

    # --- Helper methods ---

    def _insert_text(self, text: str) -> tuple[int, int]:
        start = self.index
        self.index += len(text)
        return start, self.index

    def _make_insert_text(self, text: str, index: int) -> dict:
        return {"insertText": {"location": {"index": index}, "text": text}}

    def _make_text_style(
        self,
        start: int,
        end: int,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        font_size: Optional[float] = None,
        foreground_color: Optional[dict] = None,
        font_family: Optional[str] = None,
        link_bookmark: Optional[str] = None,
    ) -> dict:
        style: dict = {}
        fields: list[str] = []

        if bold is not None:
            style["bold"] = bold
            fields.append("bold")
        if italic is not None:
            style["italic"] = italic
            fields.append("italic")
        if font_size is not None:
            style["fontSize"] = {"magnitude": font_size, "unit": "PT"}
            fields.append("fontSize")
        if foreground_color is not None:
            style["foregroundColor"] = {"color": {"rgbColor": foreground_color}}
            fields.append("foregroundColor")
        if font_family is not None:
            style["weightedFontFamily"] = {"fontFamily": font_family}
            fields.append("weightedFontFamily")
        if link_bookmark is not None:
            style["link"] = {"bookmarkId": link_bookmark}
            fields.append("link")

        return {
            "updateTextStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "textStyle": style,
                "fields": ",".join(fields)
            }
        }

    def _make_paragraph_style(
        self,
        start: int,
        end: int,
        named_style: Optional[str] = None,
        alignment: Optional[str] = None,
        space_above: Optional[float] = None,
        space_below: Optional[float] = None,
        line_spacing: Optional[float] = None,
        border_bottom: Optional[dict] = None,
    ) -> dict:
        style: dict = {}
        fields: list[str] = []

        if named_style is not None:
            style["namedStyleType"] = named_style
            fields.append("namedStyleType")
        if alignment is not None:
            style["alignment"] = alignment
            fields.append("alignment")
        if space_above is not None:
            style["spaceAbove"] = {"magnitude": space_above, "unit": "PT"}
            fields.append("spaceAbove")
        if space_below is not None:
            style["spaceBelow"] = {"magnitude": space_below, "unit": "PT"}
            fields.append("spaceBelow")
        if line_spacing is not None:
            style["lineSpacing"] = line_spacing * 100
            fields.append("lineSpacing")
        if border_bottom is not None:
            style["borderBottom"] = border_bottom
            fields.append("borderBottom")

        return {
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "paragraphStyle": style,
                "fields": ",".join(fields)
            }
        }

    def _make_bullet(self, start: int, end: int, preset: str, level: int) -> dict:
        return {
            "createParagraphBullets": {
                "range": {"startIndex": start, "endIndex": end},
                "bulletPreset": preset
            }
        }

    # --- Block builders (each returns (text_requests, style_requests)) ---

    def _build_cover_title(self, block: Block):
        p = self.profile
        text = block.text + "\n"
        start, end = self._insert_text(text)
        txt = [self._make_insert_text(text, start)]
        sty = [
            self._make_paragraph_style(start, end, named_style="HEADING_1", alignment=p.cover.title_alignment),
            self._make_text_style(start, end - 1, bold=p.cover.title_bold, font_size=p.cover.title_size, font_family=p.font_family),
        ]
        return txt, sty

    def _build_cover_subtitle(self, block: Block):
        p = self.profile
        text = block.text + "\n"
        start, end = self._insert_text(text)
        txt = [self._make_insert_text(text, start)]
        sty = [
            self._make_paragraph_style(start, end, named_style="HEADING_2", alignment=p.cover.subtitle_alignment),
            self._make_text_style(start, end - 1, bold=p.cover.subtitle_bold, font_size=p.cover.subtitle_size, font_family=p.font_family),
        ]
        return txt, sty

    def _build_cover_project(self, block: Block):
        p = self.profile
        text = block.text + "\n"
        start, end = self._insert_text(text)
        txt = [self._make_insert_text(text, start)]
        sty = [
            self._make_paragraph_style(start, end, named_style="HEADING_3", alignment=p.cover.project_alignment),
            self._make_text_style(start, end - 1, font_size=p.cover.project_size, font_family=p.font_family),
        ]
        return txt, sty

    def _build_cover_meta(self, block: Block):
        p = self.profile
        text = block.text + "\n"
        start, end = self._insert_text(text)
        txt = [self._make_insert_text(text, start)]
        sty = [
            self._make_paragraph_style(start, end, alignment=p.cover.meta_alignment),
            self._make_text_style(start, end - 1, font_size=p.cover.meta_size, font_family=p.font_family),
        ]
        return txt, sty

    def _build_cover_confidentiality(self, block: Block):
        p = self.profile
        text = block.text + "\n"
        start, end = self._insert_text(text)
        txt = [self._make_insert_text(text, start)]
        sty = [
            self._make_paragraph_style(start, end, alignment=p.cover.confidentiality_alignment),
            self._make_text_style(
                start, end - 1,
                italic=p.cover.confidentiality_italic or None,
                font_size=p.cover.confidentiality_size,
                font_family=p.font_family
            ),
        ]
        return txt, sty

    def _build_toc_heading(self, block: Block):
        p = self.profile
        text = block.text + "\n"
        start, end = self._insert_text(text)
        txt = [self._make_insert_text(text, start)]
        sty = [
            self._make_text_style(
                start, end - 1,
                bold=p.toc.heading_bold or None,
                font_size=p.toc.heading_size,
                font_family=p.font_family
            ),
        ]
        return txt, sty

    def _build_toc_entry(self, block: Block):
        p = self.profile
        text = block.text + "\n"
        start, end = self._insert_text(text)
        txt = [self._make_insert_text(text, start)]
        sty = [
            self._make_text_style(
                start, end - 1,
                font_size=p.toc.entry_size,
                foreground_color=p.toc.link_color,
                font_family=p.font_family
            ),
            self._make_paragraph_style(start, end, space_below=p.toc.entry_spacing),
        ]
        self.toc_entries.append({
            "start": start,
            "end": end - 1,
            "target": block.link_target
        })
        return txt, sty

    def _build_heading_1(self, block: Block):
        p = self.profile
        h = p.heading_1
        text = block.text + "\n"
        start, end = self._insert_text(text)
        txt = [self._make_insert_text(text, start)]

        bookmark_id = self._heading_to_anchor(block.text)
        self.bookmarks[bookmark_id] = start

        sty = [
            self._make_paragraph_style(start, end, named_style=h.named_style, space_above=h.space_before, space_below=h.space_after),
            self._make_text_style(start, end - 1, bold=h.bold or None, font_size=h.font_size, font_family=p.font_family),
        ]
        return txt, sty

    def _build_heading_2(self, block: Block):
        p = self.profile
        h = p.heading_2
        text = block.text + "\n"
        start, end = self._insert_text(text)
        txt = [self._make_insert_text(text, start)]
        sty = [
            self._make_paragraph_style(start, end, named_style=h.named_style, space_above=h.space_before, space_below=h.space_after),
            self._make_text_style(start, end - 1, bold=h.bold or None, font_size=h.font_size, font_family=p.font_family),
        ]
        return txt, sty

    def _build_paragraph(self, block: Block):
        p = self.profile
        txt_reqs = []
        sty_reqs = []

        start = self.index
        for span in block.spans:
            span_start = self.index
            self.index += len(span.text)
            txt_reqs.append(self._make_insert_text(span.text, span_start))
            if span.bold or span.italic:
                sty_reqs.append(self._make_text_style(
                    span_start, self.index,
                    bold=True if span.bold else None,
                    italic=True if span.italic else None,
                    font_size=p.body.font_size,
                    font_family=p.font_family
                ))

        nl_start = self.index
        self.index += 1
        txt_reqs.append(self._make_insert_text("\n", nl_start))

        end = self.index
        sty_reqs.append(self._make_paragraph_style(
            start, end, space_below=p.body.space_after, line_spacing=p.body.line_spacing
        ))
        sty_reqs.append(self._make_text_style(
            start, end - 1, font_size=p.body.font_size, font_family=p.font_family
        ))
        return txt_reqs, sty_reqs

    def _build_bullet(self, block: Block):
        p = self.profile
        txt_reqs, sty_reqs = self._build_list_item(block)
        para_start = txt_reqs[0]["insertText"]["location"]["index"] if txt_reqs else self.index
        sty_reqs.append(self._make_bullet(para_start, self.index, p.body.bullet_preset, block.level))
        return txt_reqs, sty_reqs

    def _build_numbered(self, block: Block):
        p = self.profile
        txt_reqs, sty_reqs = self._build_list_item(block)
        para_start = txt_reqs[0]["insertText"]["location"]["index"] if txt_reqs else self.index
        sty_reqs.append(self._make_bullet(para_start, self.index, p.body.numbered_preset, block.level))
        return txt_reqs, sty_reqs

    def _build_list_item(self, block: Block):
        p = self.profile
        txt_reqs = []
        sty_reqs = []

        start = self.index
        for span in block.spans:
            span_start = self.index
            self.index += len(span.text)
            txt_reqs.append(self._make_insert_text(span.text, span_start))
            if span.bold or span.italic:
                sty_reqs.append(self._make_text_style(
                    span_start, self.index,
                    bold=True if span.bold else None,
                    italic=True if span.italic else None,
                ))

        nl_start = self.index
        self.index += 1
        txt_reqs.append(self._make_insert_text("\n", nl_start))

        end = self.index
        sty_reqs.append(self._make_text_style(
            start, end - 1, font_size=p.body.font_size, font_family=p.font_family
        ))
        return txt_reqs, sty_reqs

    def _build_table(self, block: Block):
        """Build table insertion requests."""
        p = self.profile
        txt_reqs = []
        sty_reqs = []

        num_rows = 1 + len(block.rows)
        num_cols = len(block.headers)

        if num_rows == 0 or num_cols == 0:
            return txt_reqs, sty_reqs

        table_start = self.index

        txt_reqs.append({
            "insertTable": {
                "rows": num_rows,
                "columns": num_cols,
                "location": {"index": table_start}
            }
        })

        # Index advance from insertTable for an empty table:
        # insertTable at table_start creates:
        #   - 1 pre-table paragraph (table_start .. table_start+1)
        #   - table element: 1 (table) + R * (1 (row) + C * 2 (cell+paragraph))
        #   - 1 trailing paragraph (with newline that becomes the next insert point)
        # The next insertable index = table_start + 1 (pre-para) + 1 (table elem) +
        #   R*(1+2*C) (rows) + 1 (table end) = table_start + 3 + R*(1+2*C)
        # So the effective index advance is 3 + R * (1 + 2*C).
        table_size = 3 + num_rows * (1 + 2 * num_cols)

        cell_contents: list[tuple[int, int, str, bool]] = []
        for c, header in enumerate(block.headers):
            cell_contents.append((0, c, header, True))
        for r, row in enumerate(block.rows):
            for c, cell in enumerate(row):
                if c < num_cols:
                    cell_contents.append((r + 1, c, cell, False))

        # Advance index by empty table structure PLUS all cell text that will be inserted.
        # Cell text insertions add characters inside the table, shifting everything after it.
        total_cell_text_length = sum(len(text) for _, _, text, _ in cell_contents if text)
        self.index += table_size + total_cell_text_length

        cell_insert_requests = []
        cell_style_requests = []

        for row_idx, col_idx, text, is_header in reversed(cell_contents):
            if not text:
                continue

            # Cell content index in an empty table:
            # Each cell has 2 positions: cell structural element + paragraph content.
            # table_start + 2 (first row) + 1 (cell) + 1 (paragraph) = table_start + 4
            # For row r, col c: table_start + 4 + r * (1 + 2*C) + c * 2
            content_index = table_start + 4 + row_idx * (1 + 2 * num_cols) + col_idx * 2

            cell_insert_requests.append(self._make_insert_text(text, content_index))

            text_end = content_index + len(text)
            cell_style_requests.append(self._make_text_style(
                content_index, text_end,
                font_size=p.table.cell_font_size,
                font_family=p.font_family,
                bold=True if is_header and p.table.header_bold else None,
            ))

            if is_header:
                cell_style_requests.append({
                    "updateTableCellStyle": {
                        "tableRange": {
                            "tableCellLocation": {
                                "tableStartLocation": {"index": table_start + 1},
                                "rowIndex": 0,
                                "columnIndex": col_idx
                            },
                            "rowSpan": 1,
                            "columnSpan": 1
                        },
                        "tableCellStyle": {
                            "backgroundColor": {"color": {"rgbColor": p.table.header_bg_color}}
                        },
                        "fields": "backgroundColor"
                    }
                })

        txt_reqs.extend(cell_insert_requests)
        sty_reqs.extend(cell_style_requests)
        return txt_reqs, sty_reqs

    def _build_horizontal_rule(self, block: Block):
        p = self.profile
        text = "\n"
        start, end = self._insert_text(text)
        txt = [self._make_insert_text(text, start)]
        sty = [
            self._make_paragraph_style(
                start, end,
                space_below=p.hr.space_below,
                border_bottom={
                    "color": {"color": {"rgbColor": p.hr.color}},
                    "width": {"magnitude": p.hr.width, "unit": "PT"},
                    "padding": {"magnitude": p.hr.padding, "unit": "PT"},
                    "dashStyle": "SOLID"
                }
            )
        ]
        return txt, sty

    def _build_placeholder(self, block: Block):
        p = self.profile
        text = block.text + "\n"
        start, end = self._insert_text(text)
        txt = [self._make_insert_text(text, start)]
        sty = [
            self._make_paragraph_style(start, end, alignment=p.placeholder.alignment),
            self._make_text_style(
                start, end - 1,
                italic=p.placeholder.italic or None,
                font_size=p.placeholder.font_size,
                foreground_color=p.placeholder.color,
                font_family=p.font_family
            ),
        ]
        return txt, sty

    def _build_empty_line(self, block: Block):
        text = "\n"
        start, end = self._insert_text(text)
        txt = [self._make_insert_text(text, start)]
        return txt, []

    @staticmethod
    def _heading_to_anchor(text: str) -> str:
        """Convert heading text to a markdown-style anchor ID."""
        anchor = text.lower().strip()
        anchor = re.sub(r"[^\w\s-]", "", anchor)
        anchor = re.sub(r"[\s]+", "-", anchor)
        return anchor


# ---------------------------------------------------------------------------
# Chunk splitter
# ---------------------------------------------------------------------------

def split_requests(requests: list[dict], max_per_chunk: int = MAX_REQUESTS_PER_CHUNK) -> list[list[dict]]:
    chunks = []
    for i in range(0, len(requests), max_per_chunk):
        chunks.append(requests[i:i + max_per_chunk])
    return chunks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Convert markdown to Google Docs batchUpdate JSON")
    parser.add_argument("markdown_file", help="Path to the markdown file")
    parser.add_argument("--profile", "-p", help="Path to a FormatProfile JSON file (default: SOW preset)")
    parser.add_argument("--output", "-o", help="Output directory or file path (default: same dir as input)")
    args = parser.parse_args()

    md_path = args.markdown_file
    if not os.path.exists(md_path):
        print(json.dumps({"error": f"File not found: {md_path}"}))
        sys.exit(1)

    # Load format profile
    if args.profile:
        if not os.path.exists(args.profile):
            print(json.dumps({"error": f"Profile not found: {args.profile}"}))
            sys.exit(1)
        profile = FormatProfile.from_json(args.profile)
    else:
        profile = FormatProfile.sow_default()

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse markdown
    md_parser = MarkdownParser(content, profile)
    try:
        blocks = md_parser.parse()
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    # Build requests
    builder = DocsRequestBuilder(blocks, profile)
    requests = builder.build()

    title = md_parser.title or "Untitled Document"
    chunks = split_requests(requests)

    # Output
    base_name = os.path.splitext(os.path.basename(md_path))[0]
    output_dir = args.output if args.output else os.path.dirname(md_path) or "."

    # Treat as directory if: no --output given, path ends with /, or path is existing dir
    is_dir_output = not args.output or output_dir.endswith("/") or os.path.isdir(output_dir)
    if is_dir_output:
        os.makedirs(output_dir, exist_ok=True)
        chunk_files = []
        for i, chunk in enumerate(chunks):
            suffix = f"_chunk{i}" if len(chunks) > 1 else ""
            out_path = os.path.join(output_dir, f"{base_name}_batch_update{suffix}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump({"requests": chunk}, f, ensure_ascii=False, indent=2)
            chunk_files.append(out_path)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_dir)), exist_ok=True)
        chunk_files = [output_dir]
        with open(output_dir, "w", encoding="utf-8") as f:
            json.dump({"requests": requests}, f, ensure_ascii=False, indent=2)

    result = {
        "title": title,
        "profile_used": profile.name,
        "batch_update_files": chunk_files,
        "total_requests": len(requests),
        "num_chunks": len(chunks),
        "blocks_parsed": len(blocks)
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
