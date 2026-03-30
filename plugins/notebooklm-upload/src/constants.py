from enum import StrEnum


class SupportedExtension(StrEnum):
    PDF = ".pdf"
    TXT = ".txt"
    MD = ".md"
    DOCX = ".docx"
    PPTX = ".pptx"
    MP3 = ".mp3"
    WAV = ".wav"
    PNG = ".png"
    JPG = ".jpg"
    JPEG = ".jpeg"


SUPPORTED_EXTENSIONS: set[str] = set(SupportedExtension)

MAX_FILE_SIZE_MB = 200
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

MAX_SOURCES_FREE = 50
MAX_SOURCES_PRO = 300

DEFAULT_EXCLUDE_PATTERNS: list[str] = [
    "__pycache__",
    "node_modules",
]
