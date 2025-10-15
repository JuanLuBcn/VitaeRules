"""Long-term memory (LTM) implementation with Chroma vector store."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

from ..config import get_settings
from ..tracing import get_tracer
from .schemas import MemoryItem, MemoryQuery, MemorySearchResult, MemorySection, MemoryStatus


class LongTermMemory:
    """
    Long-term memory with vector embeddings.

    Uses Chroma for semantic search and stores metadata for filtering.
    """

    def __init__(self, store_path: Path | None = None):
        """
        Initialize long-term memory.

        Args:
            store_path: Path to vector store (default: from settings)
        """
        self.settings = get_settings()
        self.tracer = get_tracer()
        self.store_path = store_path or self.settings.vector_store_path

        if not CHROMA_AVAILABLE:
            raise ImportError(
                "chromadb not installed. Install with: pip install chromadb"
            )

        self._init_store()

    def _init_store(self) -> None:
        """Initialize the Chroma vector store."""
        self.store_path.mkdir(parents=True, exist_ok=True)

        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=str(self.store_path),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="memories",
            metadata={"description": "Long-term memory items"},
        )

        self.tracer.debug(f"LTM initialized at {self.store_path}")

    def add(self, item: MemoryItem) -> None:
        """
        Add a memory item to long-term memory.

        Args:
            item: Memory item to add
        """
        # Prepare document text for embedding
        document_text = self._prepare_document(item)

        # Prepare metadata (Chroma only supports simple types)
        metadata = self._prepare_metadata(item)

        # Add to collection
        self.collection.add(
            ids=[str(item.id)],
            documents=[document_text],
            metadatas=[metadata],
        )

        self.tracer.debug(
            f"Added item to LTM: id={item.id} section={item.section} title={item.title[:50]}"
        )

    def get(self, item_id: UUID | str) -> MemoryItem | None:
        """
        Get a memory item by ID.

        Args:
            item_id: Item identifier

        Returns:
            Memory item or None if not found
        """
        item_id_str = str(item_id)

        result = self.collection.get(ids=[item_id_str], include=["documents", "metadatas"])

        if not result["ids"]:
            return None

        # Reconstruct MemoryItem from stored data
        metadata = result["metadatas"][0]
        return self._reconstruct_item(metadata)

    def search(self, query: MemoryQuery) -> list[MemorySearchResult]:
        """
        Search for relevant memories.

        Args:
            query: Search query with filters

        Returns:
            List of search results with scores
        """
        # Build where filter for metadata
        where_filter = self._build_where_filter(query)

        # Query collection
        results = self.collection.query(
            query_texts=[query.query],
            n_results=query.top_k,
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"],
        )

        # Convert to search results
        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, item_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i] if results["distances"] else 1.0

                # Convert distance to similarity score (0-1, higher is better)
                # Chroma uses L2 distance, smaller is better
                score = 1.0 / (1.0 + distance)

                item = self._reconstruct_item(metadata)
                search_results.append(
                    MemorySearchResult(
                        item=item,
                        score=score,
                        highlights=[],  # TODO: Extract matching snippets
                    )
                )

        self.tracer.debug(f"LTM search returned {len(search_results)} results")
        return search_results

    def update(self, item: MemoryItem) -> None:
        """
        Update an existing memory item.

        Args:
            item: Updated memory item
        """
        item.updated_at = datetime.now(UTC)

        # Update in collection (Chroma updates by deleting and re-adding)
        self.delete(item.id)
        self.add(item)

        self.tracer.debug(f"Updated item in LTM: id={item.id}")

    def delete(self, item_id: UUID | str) -> None:
        """
        Delete a memory item.

        Args:
            item_id: Item identifier
        """
        self.collection.delete(ids=[str(item_id)])
        self.tracer.debug(f"Deleted item from LTM: id={item_id}")

    def count(self, section: MemorySection | None = None) -> int:
        """
        Count memory items.

        Args:
            section: Optional section filter

        Returns:
            Number of items
        """
        if section:
            where_filter = {"section": section.value}
            result = self.collection.get(where=where_filter, include=[])
            return len(result["ids"])
        else:
            return self.collection.count()

    def _prepare_document(self, item: MemoryItem) -> str:
        """Prepare document text for embedding."""
        parts = [item.title, item.content]

        if item.people:
            parts.append(f"People: {', '.join(item.people)}")

        if item.tags:
            parts.append(f"Tags: {', '.join(item.tags)}")

        if item.location:
            parts.append(f"Location: {item.location}")

        return "\n".join(parts)

    def _prepare_metadata(self, item: MemoryItem) -> dict[str, Any]:
        """Prepare metadata for Chroma (only simple types)."""
        # Note: source, section, status are already strings due to use_enum_values=True
        metadata: dict[str, Any] = {
            "id": str(item.id),
            "source": item.source if isinstance(item.source, str) else item.source.value,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
            "title": item.title,
            "section": item.section if isinstance(item.section, str) else item.section.value,
            "status": item.status if isinstance(item.status, str) else item.status.value,
        }

        # Add optional fields
        if item.chat_id:
            metadata["chat_id"] = item.chat_id
        if item.user_id:
            metadata["user_id"] = item.user_id
        if item.date_bucket:
            metadata["date_bucket"] = item.date_bucket
        if item.list_name:
            metadata["list_name"] = item.list_name
        if item.event_start_at:
            metadata["event_start_at"] = item.event_start_at.isoformat()

        # Store complex fields as JSON strings
        metadata["_full_data"] = item.model_dump_json()

        return metadata

    def _reconstruct_item(self, metadata: dict[str, Any]) -> MemoryItem:
        """Reconstruct MemoryItem from metadata."""
        # Use full data if available
        if "_full_data" in metadata:
            return MemoryItem.model_validate_json(metadata["_full_data"])

        # Fallback: reconstruct from simple metadata
        return MemoryItem(
            id=UUID(metadata["id"]),
            source=metadata["source"],
            created_at=datetime.fromisoformat(metadata["created_at"]),
            updated_at=datetime.fromisoformat(metadata["updated_at"]),
            title=metadata["title"],
            content="",  # Not stored in simple metadata
            section=MemorySection(metadata["section"]),
            status=MemoryStatus(metadata["status"]),
            chat_id=metadata.get("chat_id"),
            user_id=metadata.get("user_id"),
        )

    def _build_where_filter(self, query: MemoryQuery) -> dict[str, Any] | None:
        """Build Chroma where filter from query."""
        where: dict[str, Any] = {}

        if query.section:
            # section is already a string due to use_enum_values=True
            where["section"] = (
                query.section if isinstance(query.section, str) else query.section.value
            )

        if query.filters:
            where.update(query.filters)

        return where if where else None
