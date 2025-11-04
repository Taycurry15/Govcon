"""Knowledge management service for document upload and retrieval."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from govcon.models.knowledge import Base, DocumentCategory, KnowledgeDocument
from govcon.services.vector_store import vector_store
from govcon.utils.config import get_settings
from govcon.utils.logger import get_logger
from govcon.utils.parsers import chunk_text, extract_metadata, parse_document

logger = get_logger(__name__)
settings = get_settings()


class KnowledgeService:
    """Service for managing knowledge documents."""

    def __init__(self) -> None:
        """Initialize knowledge service."""
        self.vector_store = vector_store
        self.storage_path = Path("data/knowledge")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Database setup
        engine = create_engine(settings.postgres_url)
        Base.metadata.create_all(bind=engine)
        self.SessionLocal = sessionmaker(bind=engine)

    def upload_document(
        self,
        file_path: str,
        title: str,
        category: str | None = None,
        description: Optional[str] = None,
        agency: Optional[str] = None,
        naics_codes: Optional[str] = None,
        keywords: Optional[str] = None,
        win_status: Optional[str] = None,
        contract_value: Optional[float] = None,
    ) -> KnowledgeDocument:
        """
        Upload a document to the knowledge base.

        Args:
            file_path: Path to the document file
            title: Document title
            category: Document category (from DocumentCategory enum)
            description: Optional description
            agency: Related agency
            naics_codes: Comma-separated NAICS codes
            keywords: Comma-separated keywords
            win_status: Won/lost/pending
            contract_value: Contract value if applicable

        Returns:
            Created KnowledgeDocument
        """
        source_path = Path(file_path)
        if not source_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Uploading document: {title}")

        # Parse document
        try:
            text_content = parse_document(str(source_path))
            logger.info(f"Extracted {len(text_content)} characters from {source_path.name}")
        except Exception as e:
            logger.error(f"Failed to parse document: {e}")
            raise

        # Extract metadata
        metadata = extract_metadata(text_content, source_path.name)
        logger.info(f"Extracted metadata: {metadata}")

        # Determine category if not supplied
        chosen_category = category
        classifier_reason = None
        if not chosen_category:
            chosen_category, classifier_reason = self._classify_document(
                text=text_content,
                metadata=metadata,
                file_name=source_path.name,
            )
            logger.info(
                "Inferred category '%s' for '%s' (%s)",
                chosen_category,
                source_path.name,
                classifier_reason or "no details",
            )

        # Validate category
        try:
            category_enum = DocumentCategory(chosen_category)
        except ValueError:
            valid_categories = [c.value for c in DocumentCategory]
            raise ValueError(f"Invalid category '{chosen_category}'. Must be one of: {', '.join(valid_categories)}")

        category_value = category_enum.value

        # Copy file to storage
        file_type = source_path.suffix.lstrip(".")
        stored_filename = f"{source_path.stem}_{category_value}.{file_type}"
        stored_path = self.storage_path / stored_filename
        shutil.copy2(source_path, stored_path)
        logger.info(f"Copied file to: {stored_path}")

        # Chunk text
        chunks = chunk_text(text_content, chunk_size=1000, overlap=200)
        logger.info(f"Created {len(chunks)} chunks")

        # Create database record
        db = self.SessionLocal()
        try:
            doc = KnowledgeDocument(
                title=title,
                category=category_value,
                file_path=str(stored_path),
                file_type=file_type,
                description=description,
                agency=agency,
                naics_codes=naics_codes,
                keywords=keywords,
                win_status=win_status,
                contract_value=contract_value,
                vector_collection=f"knowledge_{category_value}",
                chunk_count=len(chunks),
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            doc_id = doc.id
            logger.info(f"Created database record with ID: {doc_id}")

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create database record: {e}")
            raise
        finally:
            db.close()

        # Add to vector store
        try:
            collection_name = f"knowledge_{category_value}"
            chunk_metadata = [
                {
                    "title": title,
                    "category": category_value,
                    "agency": agency or "",
                    "file_type": file_type,
                    "chunk_total": len(chunks),
                    "keywords": keywords or "",
                }
                for _ in chunks
            ]

            self.vector_store.add_documents(
                collection_name=collection_name,
                chunks=chunks,
                metadata_list=chunk_metadata,
                document_id=doc_id,
            )
            logger.info(f"Added {len(chunks)} chunks to vector store collection '{collection_name}'")

        except Exception as e:
            logger.error(f"Failed to add to vector store: {e}")
            # Delete database record if vector store upload fails
            db = self.SessionLocal()
            try:
                db.delete(doc)
                db.commit()
            finally:
                db.close()
            raise

        logger.info(f"Successfully uploaded document '{title}' (ID: {doc_id})")
        return doc

    def _classify_document(
        self,
        *,
        text: str,
        metadata: dict,
        file_name: str,
    ) -> tuple[str, Optional[str]]:
        """Heuristic stub for automatic category classification.

        Returns the chosen category value and an optional reason string.
        """
        lowered_name = file_name.lower()
        lowered_text = text.lower()

        keyword_map = {
            DocumentCategory.PROPOSAL_TEMPLATE.value: ["template", "outline", "format", "sample"],
            DocumentCategory.TECHNICAL_APPROACH.value: ["technical", "solution", "architecture", "engineering"],
            DocumentCategory.MANAGEMENT_APPROACH.value: ["management", "staffing", "org chart", "team structure"],
            DocumentCategory.PAST_PROPOSAL.value: ["past performance", "final proposal", "submitted"],
            DocumentCategory.PAST_PERFORMANCE.value: ["cpars", "past performance", "reference"],
            DocumentCategory.CAPABILITY_STATEMENT.value: ["capability statement", "capabilities"],
            DocumentCategory.BOILERPLATE.value: ["boilerplate", "resume", "bio", "cover letter"],
            DocumentCategory.WIN_THEME.value: ["win theme", "theme", "strength", "discriminator"],
            DocumentCategory.COMPLIANCE_MATRIX.value: ["compliance matrix", "rtm", "requirement tracking"],
            DocumentCategory.PRICING_TEMPLATE.value: ["pricing", "cost", "rate", "estimate"],
        }

        for category_value, needles in keyword_map.items():
            for needle in needles:
                if needle in lowered_name or needle in lowered_text:
                    return category_value, f"matched keyword '{needle}'"

        return DocumentCategory.OTHER.value, "defaulted to 'other'"

    def search_knowledge(
        self,
        query: str,
        category: Optional[str] = None,
        agency: Optional[str] = None,
        limit: int = 5,
        score_threshold: float = 0.7,
    ) -> list[dict]:
        """
        Search knowledge base for relevant content.

        Args:
            query: Search query
            category: Optional category filter
            agency: Optional agency filter
            limit: Maximum results
            score_threshold: Minimum similarity score

        Returns:
            List of relevant chunks with metadata
        """
        # Determine which collection(s) to search
        if category:
            collections = [f"knowledge_{category}"]
        else:
            # Search all knowledge collections
            all_collections = self.vector_store.list_collections()
            collections = [c for c in all_collections if c.startswith("knowledge_")]

        if not collections:
            logger.warning("No knowledge collections found")
            return []

        # Build metadata filter
        filter_metadata = {}
        if agency:
            filter_metadata["agency"] = agency

        # Search each collection
        all_results = []
        for collection in collections:
            try:
                results = self.vector_store.search(
                    collection_name=collection,
                    query=query,
                    limit=limit,
                    score_threshold=score_threshold,
                    filter_metadata=filter_metadata if filter_metadata else None,
                )
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Failed to search collection {collection}: {e}")
                continue

        # Sort by score and limit
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:limit]

    def get_document(self, document_id: int) -> Optional[KnowledgeDocument]:
        """
        Get a knowledge document by ID.

        Args:
            document_id: Document ID

        Returns:
            KnowledgeDocument or None
        """
        db = self.SessionLocal()
        try:
            return db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
        finally:
            db.close()

    def list_documents(
        self,
        category: Optional[str] = None,
        agency: Optional[str] = None,
        limit: int = 100,
    ) -> list[KnowledgeDocument]:
        """
        List knowledge documents.

        Args:
            category: Optional category filter
            agency: Optional agency filter
            limit: Maximum results

        Returns:
            List of KnowledgeDocument
        """
        db = self.SessionLocal()
        try:
            query = db.query(KnowledgeDocument)

            if category:
                query = query.filter(KnowledgeDocument.category == category)
            if agency:
                query = query.filter(KnowledgeDocument.agency == agency)

            return query.order_by(KnowledgeDocument.uploaded_at.desc()).limit(limit).all()
        finally:
            db.close()

    def delete_document(self, document_id: int) -> bool:
        """
        Delete a knowledge document.

        Args:
            document_id: Document ID to delete

        Returns:
            True if deleted successfully
        """
        db = self.SessionLocal()
        try:
            doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
            if not doc:
                logger.warning(f"Document {document_id} not found")
                return False

            # Delete from vector store
            collection_name = doc.vector_collection
            if collection_name:
                try:
                    self.vector_store.delete_document(collection_name, document_id)
                except Exception as e:
                    logger.warning(f"Failed to delete from vector store: {e}")

            # Delete file
            file_path = Path(doc.file_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")

            # Delete database record
            db.delete(doc)
            db.commit()
            logger.info(f"Deleted document {document_id}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete document: {e}")
            return False
        finally:
            db.close()


# Shared singleton
knowledge_service = KnowledgeService()

__all__ = ["KnowledgeService", "knowledge_service"]
