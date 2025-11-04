"""Vector store service using Qdrant for RAG."""

from __future__ import annotations

from urllib.parse import urlparse
from typing import Any, Optional

from govcon.utils.config import Settings, get_settings
from govcon.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStoreService:
    """Service for storing and retrieving document embeddings in Qdrant."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize vector store service."""
        self.settings = settings or get_settings()
        self._qdrant_client = None
        self._openai_client = None

    def _get_qdrant_client(self):
        """Get or create Qdrant client."""
        if self._qdrant_client is None:
            try:
                from qdrant_client import QdrantClient
            except ImportError:
                logger.error("qdrant-client not installed. Install with: pip install qdrant-client")
                raise

            qdrant_url = getattr(self.settings, "qdrant_url", None) or "http://localhost:6333"
            parsed = urlparse(qdrant_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 6333
            is_https = parsed.scheme == "https"

            self._qdrant_client = QdrantClient(
                host=host,
                port=port,
                api_key=getattr(self.settings, "qdrant_api_key", None),
                https=is_https,
            )
            logger.info("Connected to Qdrant at %s:%s", host, port)
        return self._qdrant_client

    def _get_openai_client(self):
        """Get or create OpenAI client for embeddings."""
        if self._openai_client is None:
            from openai import OpenAI

            api_key = self.settings.openai_api_key
            if not api_key:
                raise RuntimeError("OpenAI API key required for embeddings")
            self._openai_client = OpenAI(api_key=api_key)
        return self._openai_client

    def create_collection(self, collection_name: str, vector_size: int = 1536) -> None:
        """
        Create a new collection in Qdrant.

        Args:
            collection_name: Name of the collection
            vector_size: Dimension of vectors (1536 for OpenAI text-embedding-3-small)
        """
        from qdrant_client.models import Distance, VectorParams

        client = self._get_qdrant_client()

        # Check if collection exists
        collections = client.get_collections().collections
        if any(col.name == collection_name for col in collections):
            logger.info(f"Collection '{collection_name}' already exists")
            return

        # Create collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info(f"Created collection '{collection_name}' with vector size {vector_size}")

    def generate_embedding(self, text: str, model: str = "text-embedding-3-small") -> list[float]:
        """
        Generate embedding for text using OpenAI.

        Args:
            text: Text to embed
            model: OpenAI embedding model to use

        Returns:
            Embedding vector
        """
        client = self._get_openai_client()

        # Truncate text if too long (8191 tokens max for text-embedding-3-small)
        # Rough estimate: ~4 chars per token
        max_chars = 8191 * 4
        if len(text) > max_chars:
            text = text[:max_chars]
            logger.warning(f"Text truncated to {max_chars} characters for embedding")

        response = client.embeddings.create(input=text, model=model)
        return response.data[0].embedding

    def add_documents(
        self,
        collection_name: str,
        chunks: list[str],
        metadata_list: list[dict[str, Any]],
        document_id: int,
    ) -> int:
        """
        Add document chunks to vector store.

        Args:
            collection_name: Qdrant collection name
            chunks: List of text chunks
            metadata_list: List of metadata dicts (one per chunk)
            document_id: ID of the parent document

        Returns:
            Number of chunks added
        """
        from qdrant_client.models import PointStruct

        if len(chunks) != len(metadata_list):
            raise ValueError("Number of chunks must match number of metadata entries")

        client = self._get_qdrant_client()

        # Ensure collection exists
        self.create_collection(collection_name)

        points = []
        for idx, (chunk, metadata) in enumerate(zip(chunks, metadata_list)):
            # Generate embedding
            embedding = self.generate_embedding(chunk)

            # Create point
            from uuid import uuid4

            point_id = str(uuid4())
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "document_id": document_id,
                    "chunk_index": idx,
                    "text": chunk,
                    **metadata,
                },
            )
            points.append(point)

            # Upload in batches of 100
            if len(points) >= 100:
                client.upsert(collection_name=collection_name, points=points)
                logger.info(f"Uploaded batch of {len(points)} chunks")
                points = []

        # Upload remaining points
        if points:
            client.upsert(collection_name=collection_name, points=points)
            logger.info(f"Uploaded final batch of {len(points)} chunks")

        logger.info(f"Added {len(chunks)} chunks from document {document_id} to '{collection_name}'")
        return len(chunks)

    def search(
        self,
        collection_name: str,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.7,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict]:
        """
        Search for relevant documents.

        Args:
            collection_name: Qdrant collection to search
            query: Search query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            filter_metadata: Optional metadata filters

        Returns:
            List of search results with text, metadata, and scores
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        client = self._get_qdrant_client()

        # Generate query embedding
        query_embedding = self.generate_embedding(query)

        # Build filter if provided
        search_filter = None
        if filter_metadata:
            conditions = []
            for key, value in filter_metadata.items():
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            if conditions:
                search_filter = Filter(must=conditions)

        # Search
        results = client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=search_filter,
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "text": result.payload.get("text", ""),
                    "score": result.score,
                    "document_id": result.payload.get("document_id"),
                    "chunk_index": result.payload.get("chunk_index"),
                    "metadata": {
                        k: v for k, v in result.payload.items() if k not in ["text", "document_id", "chunk_index"]
                    },
                }
            )

        logger.info(f"Found {len(formatted_results)} results for query: '{query[:50]}...'")
        return formatted_results

    def delete_document(self, collection_name: str, document_id: int) -> int:
        """
        Delete all chunks for a document.

        Args:
            collection_name: Qdrant collection
            document_id: Document ID to delete

        Returns:
            Number of chunks deleted
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        client = self._get_qdrant_client()

        # Create filter for document_id
        delete_filter = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])

        # Delete points
        result = client.delete(collection_name=collection_name, points_selector=delete_filter)

        logger.info(f"Deleted chunks for document {document_id} from '{collection_name}'")
        return result.status if hasattr(result, "status") else 0

    def list_collections(self) -> list[str]:
        """
        List all collections in Qdrant.

        Returns:
            List of collection names
        """
        client = self._get_qdrant_client()
        collections = client.get_collections().collections
        return [col.name for col in collections]


# Shared singleton
vector_store = VectorStoreService()

__all__ = ["VectorStoreService", "vector_store"]
