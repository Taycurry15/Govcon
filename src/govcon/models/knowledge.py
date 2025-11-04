"""Knowledge document database models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DocumentCategory(str, Enum):
    """Categories for knowledge documents."""

    PAST_PERFORMANCE = "past_performance"
    PROPOSAL_TEMPLATE = "proposal_template"
    TECHNICAL_APPROACH = "technical_approach"
    MANAGEMENT_APPROACH = "management_approach"
    PAST_PROPOSAL = "past_proposal"
    CAPABILITY_STATEMENT = "capability_statement"
    BOILERPLATE = "boilerplate"
    WIN_THEME = "win_theme"
    COMPLIANCE_MATRIX = "compliance_matrix"
    PRICING_TEMPLATE = "pricing_template"
    OTHER = "other"


class KnowledgeDocument(Base):
    """Knowledge document for RAG-enhanced proposal generation."""

    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    category = Column(String(50), nullable=False)  # DocumentCategory
    file_path = Column(String(1000), nullable=False)  # Path in MinIO/local storage
    file_type = Column(String(20), nullable=False)  # pdf, docx, txt, md
    description = Column(Text, nullable=True)

    # Metadata
    agency = Column(String(200), nullable=True)  # Which agency this relates to
    naics_codes = Column(String(500), nullable=True)  # Comma-separated NAICS codes
    keywords = Column(Text, nullable=True)  # Comma-separated keywords
    win_status = Column(String(20), nullable=True)  # won, lost, pending
    contract_value = Column(Float, nullable=True)

    # Vector store info
    vector_collection = Column(String(100), nullable=True)  # Qdrant collection name
    chunk_count = Column(Integer, default=0)

    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    uploaded_by = Column(String(200), nullable=True)

    # Quality metrics
    relevance_score = Column(Float, nullable=True)  # For ranking documents
    usage_count = Column(Integer, default=0)  # Track how often this is used

    def __repr__(self) -> str:
        """String representation."""
        return f"<KnowledgeDocument(id={self.id}, title='{self.title}', category='{self.category}')>"
