import asyncio
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler

from .constants import SUPPORTED_EXTENSIONS
from .uploader import batch_upload

console = Console()


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def parse_extensions(value: str | None) -> set[str] | None:
    if not value:
        return None
    extensions = set()
    for ext in value.split(","):
        ext = ext.strip().lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        extensions.add(ext)
    return extensions


@click.command()
@click.argument("directories", nargs=-1, required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--notebook", "-n", "notebook_name", help="Create a new notebook with this name")
@click.option("--notebook-id", "-id", help="Upload to an existing notebook by ID")
@click.option("--include", "-i", "include_ext", help="Comma-separated extensions to include (e.g. pdf,md,txt)")
@click.option("--exclude", "-e", "exclude_patterns", multiple=True, help="Directory/file patterns to exclude")
@click.option("--delay", "-d", default=1.0, type=float, help="Delay between uploads in seconds (default: 1.0)")
@click.option("--timeout", "-t", default=90.0, type=float, help="HTTP timeout per upload in seconds (default: 90)")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
@click.option("--dry-run", is_flag=True, help="List files that would be uploaded without uploading")
def cli(
    directories: tuple[Path, ...],
    notebook_name: str | None,
    notebook_id: str | None,
    include_ext: str | None,
    exclude_patterns: tuple[str, ...],
    delay: float,
    timeout: float,
    verbose: bool,
    dry_run: bool,
) -> None:
    """Batch upload local files to a Google NotebookLM notebook."""
    setup_logging(verbose)

    if not notebook_name and not notebook_id:
        console.print("[red]Error:[/] Provide --notebook (to create) or --notebook-id (existing)")
        sys.exit(1)

    include_extensions = parse_extensions(include_ext)
    exclude_list = list(exclude_patterns) if exclude_patterns else None

    if dry_run:
        from .uploader import collect_files, validate_files

        files = collect_files(list(directories), include_extensions, exclude_list)
        valid, skipped = validate_files(files)

        console.print(f"\n[bold]Dry run:[/] {len(valid)} files would be uploaded\n")
        for f in valid:
            console.print(f"  [green]+[/] {f}")
        if skipped:
            console.print(f"\n[yellow]Skipped:[/] {len(skipped)}")
            for r in skipped:
                console.print(f"  [red]-[/] {r.file}: {r.error}")

        console.print(f"\n[dim]Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}[/]")
        return

    logger = logging.getLogger(__name__)
    try:
        report = asyncio.run(
            batch_upload(
                directories=list(directories),
                notebook_name=notebook_name,
                notebook_id=notebook_id,
                include_extensions=include_extensions,
                exclude_patterns=exclude_list,
                delay_seconds=delay,
                timeout_seconds=timeout,
            )
        )
    except ValueError as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)
    except RuntimeError as e:
        logger.error("batch_upload_failed", extra={"error": str(e)})
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)
    except Exception as e:
        logger.error("unexpected_error", extra={"error": str(e), "type": type(e).__name__})
        console.print(f"[red]Unexpected error ({type(e).__name__}):[/] {e}")
        sys.exit(1)

    console.print(f"\n[bold green]Done![/]\n{report.summary()}")


if __name__ == "__main__":
    cli()
