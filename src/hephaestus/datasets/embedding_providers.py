# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Embedding providers for evaluation asset creation."""

from __future__ import annotations

import math
import os
import time
from numbers import Real
from typing import Any, Callable, List, Optional, Sequence

DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 2
DEFAULT_BATCH_SIZE = 128


class OpenAIEmbeddingProvider:
    """OpenAI embeddings backend for intent clustering and matching."""

    def __init__(
        self,
        model: str = DEFAULT_OPENAI_EMBEDDING_MODEL,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff_seconds: int = DEFAULT_RETRY_BACKOFF_SECONDS,
        batch_size: int = DEFAULT_BATCH_SIZE,
        client: Optional[Any] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.batch_size = batch_size
        self._client = client
        self._sleep_fn = sleep_fn

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        """Embed text strings, preserving input order."""
        if not texts:
            return []

        client = self._get_client()
        embeddings: List[List[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = [str(text) for text in texts[start : start + self.batch_size]]
            embeddings.extend(self._embed_batch(client, batch))
        return embeddings

    def _create_client(self) -> Any:
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        # try:
        #     import truststore
        #     truststore.inject_into_ssl()
        # except ImportError:
        #     pass
        return OpenAI(
            api_key=api_key,
            timeout=self.timeout_seconds,
        )

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _embed_batch(self, client: Any, batch: Sequence[str]) -> List[List[float]]:
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = client.embeddings.create(model=self.model, input=list(batch))
                return _extract_embedding_vectors(response, expected_count=len(batch))
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= self.max_retries:
                    break
                self._sleep_fn(self.retry_backoff_seconds)
        raise RuntimeError("OpenAI embedding call failed after retries") from last_error


def _extract_embedding_vectors(response: Any, expected_count: int) -> List[List[float]]:
    data = getattr(response, "data", None)
    if data is None and isinstance(response, dict):
        data = response.get("data")
    if not isinstance(data, list):
        raise ValueError("OpenAI embedding response missing data list")
    if len(data) != expected_count:
        raise ValueError(
            f"OpenAI embedding response returned {len(data)} vectors; "
            f"expected {expected_count}"
        )

    indexed: List[tuple[int, Sequence[float]]] = []
    for item in data:
        index = _item_value(item, "index", None)
        if not isinstance(index, int) or isinstance(index, bool):
            raise ValueError(
                "OpenAI embedding response items require an integer index"
            )
        embedding = _item_value(item, "embedding", None)
        if not isinstance(embedding, list):
            raise ValueError("OpenAI embedding response item missing embedding list")
        indexed.append((index, embedding))

    indices = [index for index, _ in indexed]
    if len(set(indices)) != len(indices):
        raise ValueError("OpenAI embedding response requires unique indices")
    expected_indices = set(range(expected_count))
    if set(indices) != expected_indices:
        raise ValueError(
            "OpenAI embedding response requires indices exactly "
            f"0..{expected_count - 1}"
        )
    indexed.sort(key=lambda item: item[0])
    vectors = [embedding for _, embedding in indexed]
    return validate_embedding_vectors(
        vectors,
        expected_count=expected_count,
        source="OpenAI embedding response",
    )


def validate_embedding_vectors(
    vectors: Sequence[Sequence[float]],
    *,
    expected_count: int,
    source: str,
) -> List[List[float]]:
    """Validate one embedding batch and return normalized float vectors."""
    if isinstance(vectors, (str, bytes)) or not isinstance(vectors, Sequence):
        raise ValueError(f"{source} must return a sequence of vectors")
    if len(vectors) != expected_count:
        raise ValueError(
            f"{source} returned {len(vectors)} vectors; expected {expected_count}"
        )
    if not vectors:
        return []

    dimension: Optional[int] = None
    normalized: List[List[float]] = []
    for vector_index, vector in enumerate(vectors):
        if isinstance(vector, (str, bytes)) or not isinstance(vector, Sequence):
            raise ValueError(f"{source} vector {vector_index} must be a sequence")
        if dimension is None:
            dimension = len(vector)
            if dimension < 1:
                raise ValueError(f"{source} vectors must have positive dimension")
        elif len(vector) != dimension:
            raise ValueError(f"{source} vectors must have one consistent dimension")

        normalized_vector: List[float] = []
        for coordinate in vector:
            if isinstance(coordinate, bool) or not isinstance(coordinate, Real):
                raise ValueError(
                    f"{source} coordinates must be real numeric values"
                )
            numeric = float(coordinate)
            if not math.isfinite(numeric):
                raise ValueError(f"{source} coordinates must be finite")
            normalized_vector.append(numeric)
        if not any(value != 0.0 for value in normalized_vector):
            raise ValueError(f"{source} vector {vector_index} must be nonzero")
        normalized.append(normalized_vector)
    return normalized


def _item_value(item: Any, key: str, default: Any) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)
