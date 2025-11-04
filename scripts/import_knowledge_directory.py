"\"\"\"Bulk-import documents into the knowledge base with auto classification.\"\"\""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

from govcon.models.knowledge import KnowledgeDocument  # noqa: E402
from govcon.services.knowledge import KnowledgeService  # noqa: E402
from govcon.utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)

SUPPORTED_EXTS = {".pdf", ".txt", ".docx", ".doc", ".md"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a directory of knowledge documents.")
    parser.add_argument(
        "path",
        help="Directory containing documents to ingest.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recurse into subdirectories.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview imports without writing to the database or vector store.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process at most this many files.",
    )
    return parser.parse_args()


def discover_files(root: Path, recursive: bool) -> Iterable[Path]:
    pattern = "**/*" if recursive else "*"
    for candidate in root.glob(pattern):
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTS:
            yield candidate


def main() -> int:
    args = parse_args()
    root = Path(args.path).expanduser()
    if not root.exists():
        logger.error("Path '%s' does not exist.", root)
        return 1

    service = KnowledgeService()
    session = service.SessionLocal()

    processed = 0
    stored = 0
    skipped = 0

    try:
        existing_titles = {
            (doc.title.lower(), doc.category)
            for doc in session.query(KnowledgeDocument.title, KnowledgeDocument.category).all()
        }

        for file_path in discover_files(root, args.recursive):
            if args.limit and processed >= args.limit:
                break

            title = file_path.stem.replace("_", " ").replace("-", " ").strip() or file_path.name
            processed += 1

            logger.info("Prepared import: %s", file_path)

            if args.dry_run:
                stored += 1
                continue

            try:
                doc = service.upload_document(
                    file_path=str(file_path),
                    title=title,
                    category=None,
                )
                stored += 1
                existing_titles.add((doc.title.lower(), doc.category))
            except ValueError as exc:
                logger.warning("Skipped %s (%s)", file_path, exc)
                skipped += 1
            except Exception as exc:  # pragma: no cover - runtime guard
                logger.exception("Failed to ingest %s: %s", file_path, exc)
                skipped += 1

        logger.info(
            "Import complete. Processed=%s Stored=%s Skipped=%s",
            processed,
            stored,
            skipped,
        )
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
