# BGE embeddings
"""
ClientIQ — Embedder
Generates dense embeddings using sentence-transformers (BGE-small-en).
Supports batch processing with progress reporting.
"""

from typing import List, Optional
import numpy as np
from backend.utils.config import settings
from backend.utils.logger import logger


class Embedder:
    """
    Wrapper around SentenceTransformer for generating text embeddings.

    Model default: BAAI/bge-small-en-v1.5 (384 dim, fast + accurate)
    Alternative:   sentence-transformers/all-MiniLM-L6-v2 (384 dim)
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.embedding_model
        self.dimension = settings.embedding_dimension
        self._model = None

    def _load(self):
        """Lazy-load the model on first use."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("[Embedder] Loading model: {}", self.model_name)
                self._model = SentenceTransformer(self.model_name)
                logger.info("[Embedder] Model loaded | dim={}", self.dimension)
            except Exception as e:
                logger.error("[Embedder] Failed to load model: {}", e)
                raise

    def embed(self, text: str) -> List[float]:
        """Embed a single string. Returns list of floats."""
        self._load()
        # BGE models benefit from instruction prefix
        if "bge" in self.model_name.lower():
            text = f"Represent this sentence for searching relevant passages: {text}"
        vec = self._model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def embed_batch(self, texts: List[str], batch_size: int = 64, show_progress: bool = True) -> List[List[float]]:
        """
        Embed a list of texts in batches.
        Returns a list of embedding vectors.
        """
        self._load()
        if not texts:
            return []

        # Apply BGE instruction prefix
        if "bge" in self.model_name.lower():
            texts = [f"Represent this sentence for searching relevant passages: {t}" for t in texts]

        logger.info("[Embedder] Embedding {} texts in batches of {}", len(texts), batch_size)

        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i: i + batch_size]
            vecs = self._model.encode(
                batch,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=show_progress,
            )
            all_embeddings.extend(vecs.tolist())

        logger.info("[Embedder] Done — {} embeddings generated", len(all_embeddings))
        return all_embeddings

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        va = np.array(a)
        vb = np.array(b)
        denom = np.linalg.norm(va) * np.linalg.norm(vb)
        if denom == 0:
            return 0.0
        return float(np.dot(va, vb) / denom)


# Module-level singleton
embedder = Embedder()