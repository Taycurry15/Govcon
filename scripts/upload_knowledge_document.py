"""CLI helper to upload documents or entire folders into the knowledge base."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

from govcon.models.knowledge import DocumentCategory
from govcon.services.knowledge import KnowledgeService
from govcon.utils.logger import get_logger

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md"}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Upload documents into the knowledge base.")
    parser.add_argument(
        "path",
        help="File or directory path to upload. When a directory is supplied, all supported files are processed.",
    )
    parser.add_argument("--title", help="Override title (single file uploads). Defaults to filename.")
    parser.add_argument("--category", help="Category to apply to uploads (fallback when inferring).")
    parser.add_argument(
        "--infer-category",
        action="store_true",
        help="When uploading a directory, infer the category from the immediate parent folder name.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recurse into subdirectories when uploading from a directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which files would be uploaded without persisting anything.",
    )
    parser.add_argument("--description", help="Optional short description for the upload(s).")
    parser.add_argument("--agency", help="Associated agency for the upload(s).")
    parser.add_argument("--naics", help="Comma separated NAICS codes.")
    parser.add_argument("--keywords", help="Comma separated keywords.")
    parser.add_argument("--win-status", choices=["won", "lost", "pending"], help="Opportunity outcome.")
    parser.add_argument("--contract-value", type=float, help="Contract value in USD.")
    return parser.parse_args()


def normalize_category(raw: str) -> str:
    """Map arbitrary category strings to DocumentCategory values."""
    candidate = raw.strip().lower().replace(" ", "_").replace("-", "_")
    for option in DocumentCategory:
        if candidate in {option.value, option.name.lower()}:
            return option.value
    raise ValueError(
        f"Unknown category '{raw}'. Expected one of: {', '.join(cat.value for cat in DocumentCategory)}."
    )


def discover_files(base_path: Path, recursive: bool) -> list[Path]:
    """Collect supported files beneath the provided path."""
    if base_path.is_file():
        return [base_path]

    pattern = "**/*" if recursive else "*"
    return sorted(
        file_path
        for file_path in base_path.glob(pattern)
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def resolve_category(
    file_path: Path,
    category_flag: Optional[str],
    infer_category: bool,
) -> str:
    """Determine which category to apply to a file."""
    if category_flag:
        return normalize_category(category_flag)

    if infer_category:
        parent_name = file_path.parent.name
        return normalize_category(parent_name)

    raise ValueError(
        f"No category provided for {file_path}. Use --category or pass --infer-category for folders."
    )


def ensure_title(file_path: Path, explicit_title: Optional[str]) -> str:
    """Derive a human-friendly title for the file."""
    if explicit_title:
        stripped = explicit_title.strip()
        if stripped:
            return stripped
    return file_path.stem.replace("_", " ").replace("-", " ").title()


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    target_path = Path(args.path).expanduser()

    if not target_path.exists():
        logger.error("Path '%s' does not exist.", target_path)
        return 1

    files = discover_files(target_path, recursive=args.recursive)
    if not files:
        logger.warning("No supported documents found at %s.", target_path)
        return 0

    service = KnowledgeService()

    attempted = 0
    stored = 0
    skipped: list[tuple[Path, str]] = []

    for file_path in files:
        attempted += 1
        try:
            category = resolve_category(file_path, args.category, args.infer_category)
        except ValueError as exc:
            skipped.append((file_path, str(exc)))
            continue

        title = ensure_title(file_path, args.title if target_path.is_file() else None)

        logger.info("Prepared upload: %s (category=%s, title='%s')", file_path, category, title)

        if args.dry_run:
            continue

        try:
            document = service.upload_document(
                file_path=str(file_path),
                title=title,
                category=category,
                description=args.description,
                agency=args.agency,
                naics_codes=args.naics,
                keywords=args.keywords,
                win_status=args.win_status,
                contract_value=args.contract_value,
            )
            stored += 1
            logger.info(
                "Uploaded document id=%s stored at %s (source=%s)",
                document.id,
                document.file_path,
                file_path,
            )
        except Exception as exc:  # pragma: no cover - depends on runtime services
            skipped.append((file_path, f"Upload failed: {exc}"))

    logger.info(
        "Upload summary: %s processed, %s stored, %s skipped.",
        attempted,
        stored,
        len(skipped),
    )

    for skipped_path, reason in skipped:
        logger.warning("Skipped %s (%s)", skipped_path, reason)

    return 0 if stored or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
