# Pinecone vector store
"""
ClientIQ — Pinecone Vector Store
Handles all interactions with Pinecone: index creation,
upsert of embeddings, and filtered similarity search.
"""

from typing import List, Dict, Any, Optional
from backend.utils.config import settings
from backend.utils.logger import logger


class PineconeStore:
    """
    Pinecone vector store client.

    Manages:
    - Index initialization
    - Batch upsert of (id, vector, metadata) triples
    - Filtered top-k similarity search
    - Namespace management (optional, for multi-tenancy)
    """

    def __init__(self):
        self._index = None
        self.index_name = settings.pinecone_index_name
        self.dimension = settings.embedding_dimension

    def _get_index(self):
        """Lazy-initialize Pinecone index connection."""
        if self._index is not None:
            return self._index
        try:
            from pinecone import Pinecone, ServerlessSpec
            pc = Pinecone(api_key=settings.pinecone_api_key)

            # Create index if it doesn't exist
            existing = [idx.name for idx in pc.list_indexes()]
            if self.index_name not in existing:
                logger.info("[Pinecone] Creating index '{}' dim={}", self.index_name, self.dimension)
                pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )
                logger.info("[Pinecone] Index created ✓")
            else:
                logger.info("[Pinecone] Index '{}' already exists ✓", self.index_name)

            self._index = pc.Index(self.index_name)
            return self._index
        except Exception as e:
            logger.error("[Pinecone] Index init failed: {}", e)
            raise

    def upsert(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str = "",
        batch_size: int = 100,
    ) -> int:
        """
        Upsert a list of vectors into Pinecone.

        Each vector dict must have:
        - id: str
        - values: List[float]
        - metadata: Dict[str, Any]

        Returns total upserted count.
        """
        index = self._get_index()
        total = 0

        for i in range(0, len(vectors), batch_size):
            batch = vectors[i: i + batch_size]
            formatted = [
                {
                    "id": v["id"],
                    "values": v["values"],
                    "metadata": v.get("metadata", {}),
                }
                for v in batch
            ]
            try:
                index.upsert(vectors=formatted, namespace=namespace)
                total += len(batch)
                logger.debug("[Pinecone] Upserted batch {}/{}", i + len(batch), len(vectors))
            except Exception as e:
                logger.error("[Pinecone] Upsert batch failed: {}", e)

        logger.info("[Pinecone] Total upserted: {}", total)
        return total

    def query(
        self,
        vector: List[float],
        top_k: int = 5,
        metadata_filter: Optional[Dict] = None,
        namespace: str = "",
        include_metadata: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Query Pinecone for nearest neighbors.

        Returns list of matches with id, score, and metadata.
        """
        index = self._get_index()
        query_params = {
            "vector": vector,
            "top_k": top_k,
            "include_metadata": include_metadata,
            "namespace": namespace,
        }
        if metadata_filter:
            query_params["filter"] = metadata_filter

        try:
            response = index.query(**query_params)
            matches = []
            for m in response.get("matches", []):
                matches.append({
                    "chunk_id": m["id"],
                    "score": float(m["score"]),
                    "source": m.get("metadata", {}).get("source", ""),
                    "source_type": m.get("metadata", {}).get("source_type", ""),
                    "company_id": m.get("metadata", {}).get("company_id", ""),
                    "text": m.get("metadata", {}).get("text", ""),
                    "metadata": m.get("metadata", {}),
                })
            return matches
        except Exception as e:
            logger.error("[Pinecone] Query failed: {}", e)
            return []

    def delete_by_ids(self, ids: List[str], namespace: str = "") -> bool:
        """Delete vectors by ID list."""
        try:
            self._get_index().delete(ids=ids, namespace=namespace)
            return True
        except Exception as e:
            logger.error("[Pinecone] Delete failed: {}", e)
            return False

    def get_stats(self) -> Dict:
        """Return index statistics."""
        try:
            return self._get_index().describe_index_stats()
        except Exception as e:
            logger.error("[Pinecone] Stats failed: {}", e)
            return {}


pinecone_store = PineconeStore()