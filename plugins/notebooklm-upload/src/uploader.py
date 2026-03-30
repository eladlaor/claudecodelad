import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

from notebooklm import NotebookLMClient

from .constants import (
    DEFAULT_EXCLUDE_PATTERNS,
    MAX_FILE_SIZE_BYTES,
    MAX_FILE_SIZE_MB,
    MAX_SOURCES_PRO,
    SUPPORTED_EXTENSIONS,
)

logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    file: Path
    success: bool
    error: str | None = None


@dataclass
class BatchUploadReport:
    notebook_id: str
    notebook_name: str
    results: list[UploadResult] = field(default_factory=list)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.success)

    def summary(self) -> str:
        lines = [
            f"Notebook: {self.notebook_name} ({self.notebook_id})",
            f"Uploaded: {self.succeeded}/{len(self.results)} files",
        ]
        if self.failed > 0:
            lines.append(f"Failed: {self.failed}")
            for r in self.results:
                if not r.success:
                    lines.append(f"  - {r.file.name}: {r.error}")
        return "\n".join(lines)


def collect_files(
    directories: list[Path],
    include_extensions: set[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> list[Path]:
    extensions = include_extensions or SUPPORTED_EXTENSIONS
    excludes = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS

    files: list[Path] = []
    for directory in directories:
        if not directory.is_dir():
            raise FileNotFoundError(f"Directory not found: {directory}")

        for file_path in sorted(directory.rglob("*")):
            if not file_path.is_file():
                continue
            if any(part.startswith(".") or part in excludes for part in file_path.relative_to(directory).parts):
                continue
            if file_path.suffix.lower() not in extensions:
                continue
            files.append(file_path)

    return files


def validate_files(files: list[Path]) -> tuple[list[Path], list[UploadResult]]:
    valid: list[Path] = []
    skipped: list[UploadResult] = []

    for f in files:
        size = f.stat().st_size
        if size > MAX_FILE_SIZE_BYTES:
            skipped.append(UploadResult(
                file=f,
                success=False,
                error=f"File exceeds {MAX_FILE_SIZE_MB}MB limit ({size / 1024 / 1024:.1f}MB)",
            ))
            continue
        if size == 0:
            skipped.append(UploadResult(file=f, success=False, error="Empty file"))
            continue
        valid.append(f)

    return valid, skipped


async def batch_upload(
    directories: list[Path],
    notebook_name: str | None = None,
    notebook_id: str | None = None,
    include_extensions: set[str] | None = None,
    exclude_patterns: list[str] | None = None,
    delay_seconds: float = 1.0,
    timeout_seconds: float = 90.0,
) -> BatchUploadReport:
    files = collect_files(directories, include_extensions, exclude_patterns)
    if not files:
        raise ValueError(f"No supported files found in: {[str(d) for d in directories]}")

    valid_files, skipped = validate_files(files)

    if len(valid_files) > MAX_SOURCES_PRO:
        raise ValueError(
            f"Found {len(valid_files)} files, exceeds Pro limit of {MAX_SOURCES_PRO}. "
            "Filter with --include or --exclude."
        )

    logger.info(
        "upload_batch_start",
        extra={
            "file_count": len(valid_files),
            "skipped_count": len(skipped),
            "directories": [str(d) for d in directories],
        },
    )

    async with await NotebookLMClient.from_storage(timeout=timeout_seconds) as client:
        if notebook_id:
            nb_id = notebook_id
            nb_name = notebook_name or notebook_id
        elif notebook_name:
            nb = await client.notebooks.create(notebook_name)
            nb_id = nb.id
            nb_name = notebook_name
            logger.info("notebook_created", extra={"notebook_id": nb_id, "notebook_name": nb_name})
        else:
            raise ValueError("Provide either --notebook (name to create) or --notebook-id (existing)")

        report = BatchUploadReport(notebook_id=nb_id, notebook_name=nb_name, results=list(skipped))

        for i, file_path in enumerate(valid_files, 1):
            logger.info(
                "uploading_file",
                extra={"file": str(file_path), "progress": f"{i}/{len(valid_files)}"},
            )
            try:
                await client.sources.add_file(nb_id, file_path)
                report.results.append(UploadResult(file=file_path, success=True))
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e}"
                logger.error(
                    "upload_failed",
                    extra={"file": str(file_path), "error": error_msg},
                )
                report.results.append(UploadResult(file=file_path, success=False, error=error_msg))

            if i < len(valid_files):
                await asyncio.sleep(delay_seconds)

    if report.succeeded == 0 and report.failed > 0:
        first_error = next((r.error for r in report.results if not r.success), "unknown")
        raise RuntimeError(
            f"All {report.failed} upload(s) failed. First error: {first_error}"
        )

    return report
