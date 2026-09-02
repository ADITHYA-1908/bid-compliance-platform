"""
Embedding Service for Part 7E: RAG + AI Recommendation & Evidence-Based Explanation
Provides dense vector generation across OpenAI, Gemini, and deterministic local fallback providers.
"""

import hashlib
import logging
import math
import re
from typing import List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating dense vector embeddings for RAG knowledge chunks and search queries.
    """

    DIMENSION = settings.EMBEDDING_DIMENSION

    @classmethod
    def generate_embedding(cls, text: str) -> List[float]:
        """Generates a normalized dense vector embedding for a single text."""
        results = cls.generate_embeddings_batch([text])
        return results[0]

    @classmethod
    def generate_embeddings_batch(cls, texts: List[str]) -> List[List[float]]:
        """Generates normalized vector embeddings for a batch of texts."""
        if not texts:
            return []

        provider = (settings.EMBEDDING_PROVIDER or "local_fallback").lower().strip()

        if provider == "openai" and settings.OPENAI_API_KEY:
            try:
                return cls._generate_openai_embeddings(texts)
            except Exception as err:
                logger.warning(f"OpenAI embedding call failed, falling back to local: {err}")

        elif provider == "gemini" and settings.GEMINI_API_KEY:
            try:
                return cls._generate_gemini_embeddings(texts)
            except Exception as err:
                logger.warning(f"Gemini embedding call failed, falling back to local: {err}")

        return [cls._generate_deterministic_vector(t) for t in texts]

    @classmethod
    def _generate_openai_embeddings(cls, texts: List[str]) -> List[List[float]]:
        """Calls OpenAI Embeddings API."""
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.EMBEDDING_MODEL,
            "input": texts,
            "dimensions": cls.DIMENSION,
        }
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            embeddings = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
            return [cls._normalize_vector(vec) for vec in embeddings]

    @classmethod
    def _generate_gemini_embeddings(cls, texts: List[str]) -> List[List[float]]:
        """Calls Google Gemini Embeddings API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents?key={settings.GEMINI_API_KEY}"
        requests = [{"model": "models/text-embedding-004", "content": {"parts": [{"text": t}]}} for t in texts]
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json={"requests": requests})
            resp.raise_for_status()
            data = resp.json()
            embeddings = [item["values"] for item in data.get("embeddings", [])]
            # Pad or truncate to configured dimension if needed
            return [cls._normalize_vector(cls._adjust_dimension(vec, cls.DIMENSION)) for vec in embeddings]

    @classmethod
    def _generate_deterministic_vector(cls, text: str) -> List[float]:
        """
        Fast, deterministic dense vector generator for test suites and offline operation.
        Uses token hashing, character n-grams, and semantic feature projections to create
        a unit-normalized 1536-dimensional dense vector preserving semantic clustering.
        """
        clean_text = (text or "").lower()
        tokens = re.findall(r"\w+", clean_text)

        dim = cls.DIMENSION
        vec = [0.0] * dim

        if not tokens:
            # Baseline unit vector
            vec[0] = 1.0
            return vec

        # 1. Word token hashing with frequency weights
        for token in tokens:
            token_hash = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            idx = token_hash % dim
            sign = 1.0 if ((token_hash >> 16) & 1) == 1 else -1.0
            weight = math.log1p(len(token))
            vec[idx] += sign * weight

            # Secondary projection
            idx2 = (token_hash >> 8) % dim
            vec[idx2] += sign * (weight * 0.5)

        # 2. Character 3-gram hashing for subword similarity
        for i in range(len(clean_text) - 2):
            trigram = clean_text[i : i + 3]
            tri_hash = int(hashlib.md5(trigram.encode("utf-8")).hexdigest(), 16)
            idx = tri_hash % dim
            sign = 1.0 if (tri_hash & 1) == 1 else -1.0
            vec[idx] += sign * 0.25

        # 3. Specific procurement domain keyword clustering projections
        domain_anchors = [
            ("gst", 10),
            ("pan", 20),
            ("tax", 25),
            ("turnover", 50),
            ("financial", 55),
            ("crore", 60),
            ("oem", 100),
            ("authorization", 105),
            ("manufacturer", 110),
            ("local_content", 150),
            ("make in india", 155),
            ("percentage", 160),
            ("blacklist", 200),
            ("debar", 205),
            ("integrity", 210),
            ("bis", 250),
            ("standard", 255),
            ("compliance", 300),
            ("pass", 310),
            ("fail", 320),
            ("review", 330),
            ("risk", 400),
            ("critical", 410),
        ]
        for keyword, anchor_idx in domain_anchors:
            if keyword in clean_text:
                for offset in range(10):
                    vec[(anchor_idx + offset) % dim] += 2.0

        return cls._normalize_vector(vec)

    @classmethod
    def _normalize_vector(cls, vec: List[float]) -> List[float]:
        """Normalizes a float vector to Euclidean unit length (L2 norm = 1.0)."""
        norm = math.sqrt(sum(x * x for x in vec))
        if norm < 1e-9:
            vec[0] = 1.0
            return vec
        return [x / norm for x in vec]

    @classmethod
    def _adjust_dimension(cls, vec: List[float], target_dim: int) -> List[float]:
        """Pads or truncates a vector to target dimension."""
        if len(vec) == target_dim:
            return vec
        if len(vec) > target_dim:
            return vec[:target_dim]
        return vec + [0.0] * (target_dim - len(vec))
