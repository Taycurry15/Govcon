"""Reclassify existing knowledge documents using heuristic categorisation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

from govcon.models.knowledge import DocumentCategory, KnowledgeDocument  # noqa: E402
from govcon.services.knowledge import KnowledgeService  # noqa: E402
from govcon.utils.logger import get_logger  # noqa: E402
from govcon.utils.parsers import chunk_text, extract_metadata, parse_document  # noqa: E402

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reclassify knowledge documents using heuristic category detection."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without modifying the database or vector store.",
    )
    parser.add_argument(
        "--only",
        choices=[c.value for c in DocumentCategory],
        help="Restrict reclassification to documents currently in the given category.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process at most this many documents.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    service = KnowledgeService()
    session = service.SessionLocal()

    try:
        query = session.query(KnowledgeDocument)
        if args.only:
            query = query.filter(KnowledgeDocument.category == args.only)
        if args.limit:
            query = query.limit(args.limit)

        docs = query.all()
        logger.info("Loaded %s knowledge documents for reclassification", len(docs))

        updated = 0
        skipped = 0

        for doc in docs:
            source_path = Path(doc.file_path)
            if not source_path.exists():
                logger.warning("File missing on disk: %s (ID %s)", doc.file_path, doc.id)
                skipped += 1
                continue

            try:
                text = parse_document(str(source_path))
            except Exception as exc:  # pragma: no cover - best effort
                logger.error("Failed to parse %s (ID %s): %s", doc.file_path, doc.id, exc)
                skipped += 1
                continue

            metadata = extract_metadata(text, source_path.name)
            new_category, reason = service._classify_document(  # type: ignore[attr-defined]
                text=text,
                metadata=metadata,
                file_name=source_path.name,
            )

            if new_category == doc.category:
                logger.info(
                    "ID %s already classified as '%s' (reason: %s); skipping.",
                    doc.id,
                    doc.category,
                    reason,
                )
                skipped += 1
                continue

            logger.info(
                "Reclassifying ID %s: %s -> %s (%s)",
                doc.id,
                doc.category,
                new_category,
                reason,
            )

            if args.dry_run:
                updated += 1
                continue

            new_category_enum = DocumentCategory(new_category)
            chunks = chunk_text(text, chunk_size=1000, overlap=200)
            old_collection = doc.vector_collection or f"knowledge_{doc.category}"
            new_collection = f"knowledge_{new_category_enum.value}"

            if old_collection:
                try:
                    service.vector_store.delete_document(old_collection, doc.id)
                except Exception as exc:  # pragma: no cover - guard
                    logger.warning(
                        "Failed to delete document %s from collection %s: %s",
                        doc.id,
                        old_collection,
                        exc,
                    )

            chunk_metadata = [
                {
                    "title": doc.title,
                    "category": new_category_enum.value,
                    "agency": doc.agency or "",
                    "file_type": doc.file_type,
                    "chunk_total": len(chunks),
                    "keywords": doc.keywords or "",
                }
                for _ in chunks
            ]
            service.vector_store.add_documents(
                collection_name=new_collection,
                chunks=chunks,
                metadata_list=chunk_metadata,
                document_id=doc.id,
            )

            src = Path(doc.file_path)
            new_name = f"{src.stem.split('_')[0]}_{new_category_enum.value}{src.suffix}"
            dest = src.with_name(new_name)
            if dest != src:
                dest.parent.mkdir(parents=True, exist_ok=True)
                src.rename(dest)

            doc.category = new_category_enum.value
            doc.vector_collection = new_collection
            doc.chunk_count = len(chunks)
            doc.file_path = str(dest)
            session.add(doc)
            session.commit()
            updated += 1

        logger.info("Reclassification complete. Updated=%s, Skipped=%s", updated, skipped)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
