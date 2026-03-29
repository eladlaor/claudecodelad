"""
FormatProfile: A structured representation of Google Doc formatting styles.

Decouples document formatting from the conversion logic. Profiles can be:
- Created from a reference Google Doc via format_extractor.py
- Loaded from a saved JSON file
- Used as a preset (e.g., FormatProfile.sow_default())
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# RGB Color helper
# ---------------------------------------------------------------------------

@dataclass
class RGBColor:
    """RGB color with values normalized to 0.0-1.0 (Google Docs API convention)."""
    red: float = 0.0
    green: float = 0.0
    blue: float = 0.0

    def to_dict(self) -> dict:
        return {"red": self.red, "green": self.green, "blue": self.blue}

    @classmethod
    def from_dict(cls, d: dict) -> "RGBColor":
        return cls(red=d.get("red", 0.0), green=d.get("green", 0.0), blue=d.get("blue", 0.0))

    @classmethod
    def from_hex(cls, hex_str: str) -> "RGBColor":
        """Create from hex string like '#1155cc' or '1155cc'."""
        hex_str = hex_str.lstrip("#")
        r = int(hex_str[0:2], 16) / 255
        g = int(hex_str[2:4], 16) / 255
        b = int(hex_str[4:6], 16) / 255
        return cls(red=r, green=g, blue=b)


# ---------------------------------------------------------------------------
# Config dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CoverPageConfig:
    """Formatting for the document cover page section."""
    title_size: float = 26.0
    title_alignment: str = "CENTER"
    title_bold: bool = True
    subtitle_size: float = 18.0
    subtitle_alignment: str = "CENTER"
    subtitle_bold: bool = True
    project_size: float = 14.0
    project_alignment: str = "CENTER"
    meta_size: float = 11.0
    meta_alignment: str = "CENTER"
    confidentiality_size: float = 9.0
    confidentiality_alignment: str = "JUSTIFIED"
    confidentiality_italic: bool = True
    confidentiality_pattern: str = r"(?i)^this document"


@dataclass
class HeadingConfig:
    """Formatting for a heading level."""
    font_size: float = 20.0
    bold: bool = True
    alignment: str = "START"
    space_before: float = 20.0
    space_after: float = 10.0
    named_style: str = "HEADING_1"


@dataclass
class BodyConfig:
    """Formatting for body text, bullets, and numbered lists."""
    font_size: float = 11.0
    line_spacing: float = 1.15
    space_after: float = 8.0
    bullet_preset: str = "BULLET_DISC_CIRCLE_SQUARE"
    numbered_preset: str = "NUMBERED_DECIMAL_ALPHA_ROMAN"
    indent_per_level: int = 2  # spaces per nesting level in markdown


@dataclass
class TableConfig:
    """Formatting for tables."""
    cell_font_size: float = 10.0
    header_bold: bool = True
    header_bg_color: dict = field(default_factory=lambda: RGBColor.from_hex("f3f3f3").to_dict())
    border_width: float = 0.5
    border_color: dict = field(default_factory=lambda: RGBColor.from_hex("999999").to_dict())
    cell_padding: float = 5.0


@dataclass
class TocConfig:
    """Formatting for the Table of Contents section."""
    heading_text: str = "Table of Contents"
    heading_size: float = 14.0
    heading_bold: bool = True
    entry_size: float = 11.0
    entry_spacing: float = 4.0
    link_color: dict = field(default_factory=lambda: RGBColor.from_hex("1155cc").to_dict())


@dataclass
class HorizontalRuleConfig:
    """Formatting for horizontal rule separators."""
    color: dict = field(default_factory=lambda: RGBColor.from_hex("cccccc").to_dict())
    width: float = 1.0
    padding: float = 4.0
    space_below: float = 8.0


@dataclass
class PlaceholderConfig:
    """Formatting for screenshot/image placeholder text."""
    font_size: float = 10.0
    italic: bool = True
    alignment: str = "CENTER"
    color: dict = field(default_factory=lambda: RGBColor.from_hex("999999").to_dict())


# ---------------------------------------------------------------------------
# FormatProfile
# ---------------------------------------------------------------------------

@dataclass
class FormatProfile:
    """
    Complete formatting profile for markdown-to-Google-Doc conversion.

    A profile defines every visual property used during conversion:
    font families, heading styles, body text, tables, lists, cover page, etc.

    Profiles can be:
    - Created programmatically: FormatProfile.sow_default()
    - Extracted from a reference Google Doc: format_extractor.py
    - Loaded from JSON: FormatProfile.from_json("path/to/profile.json")
    - Saved for reuse: profile.to_json("path/to/profile.json")
    """
    name: str = "default"
    font_family: str = "Arial"
    cover: CoverPageConfig = field(default_factory=CoverPageConfig)
    heading_1: HeadingConfig = field(default_factory=lambda: HeadingConfig(
        font_size=20.0, bold=True, alignment="START",
        space_before=20.0, space_after=10.0, named_style="HEADING_1"
    ))
    heading_2: HeadingConfig = field(default_factory=lambda: HeadingConfig(
        font_size=16.0, bold=True, alignment="START",
        space_before=16.0, space_after=8.0, named_style="HEADING_2"
    ))
    body: BodyConfig = field(default_factory=BodyConfig)
    table: TableConfig = field(default_factory=TableConfig)
    toc: TocConfig = field(default_factory=TocConfig)
    hr: HorizontalRuleConfig = field(default_factory=HorizontalRuleConfig)
    placeholder: PlaceholderConfig = field(default_factory=PlaceholderConfig)

    @classmethod
    def sow_default(cls) -> "FormatProfile":
        """Default SOW preset matching a professional Statement of Work format."""
        return cls(name="default-sow")

    @classmethod
    def from_json(cls, path: str) -> "FormatProfile":
        """Load a profile from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> "FormatProfile":
        """Reconstruct a FormatProfile from a dictionary."""
        return cls(
            name=data.get("name", "loaded"),
            font_family=data.get("font_family", "Arial"),
            cover=CoverPageConfig(**data["cover"]) if "cover" in data else CoverPageConfig(),
            heading_1=HeadingConfig(**data["heading_1"]) if "heading_1" in data else HeadingConfig(),
            heading_2=HeadingConfig(**data["heading_2"]) if "heading_2" in data else HeadingConfig(
                font_size=16.0, space_before=16.0, space_after=8.0, named_style="HEADING_2"
            ),
            body=BodyConfig(**data["body"]) if "body" in data else BodyConfig(),
            table=TableConfig(**data["table"]) if "table" in data else TableConfig(),
            toc=TocConfig(**data["toc"]) if "toc" in data else TocConfig(),
            hr=HorizontalRuleConfig(**data["hr"]) if "hr" in data else HorizontalRuleConfig(),
            placeholder=PlaceholderConfig(**data["placeholder"]) if "placeholder" in data else PlaceholderConfig(),
        )

    def to_json(self, path: str) -> None:
        """Save the profile to a JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    def to_dict(self) -> dict:
        """Convert to a plain dictionary."""
        return asdict(self)
