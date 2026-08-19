# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.hephaestus.datasets import embedding_providers
from src.hephaestus.datasets.embedding_providers import (
    OpenAIEmbeddingProvider,
    _extract_embedding_vectors,
)


class DummyEmbeddings:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        rows = []
        for index, text in enumerate(kwargs["input"]):
            rows.append(SimpleNamespace(index=index, embedding=[float(len(text)), float(index)]))
        return SimpleNamespace(data=rows)


class DummyOpenAIClient:
    def __init__(self):
        self.embeddings = DummyEmbeddings()


def test_openai_embedding_provider_batches_and_preserves_order():
    client = DummyOpenAIClient()
    provider = OpenAIEmbeddingProvider(
        model="embedding-model",
        batch_size=2,
        client=client,
    )

    embeddings = provider.embed_texts(["a", "abcd", "xy"])

    assert embeddings == [[1.0, 0.0], [4.0, 1.0], [2.0, 0.0]]
    assert len(client.embeddings.calls) == 2
    assert client.embeddings.calls[0]["model"] == "embedding-model"
    assert client.embeddings.calls[0]["input"] == ["a", "abcd"]
    assert client.embeddings.calls[1]["input"] == ["xy"]


def test_openai_embedding_provider_rejects_cross_batch_dimension_drift() -> None:
    """Successive SDK batches cannot concatenate incompatible vector shapes."""

    class DriftingEmbeddings:
        def __init__(self) -> None:
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            dimension = self.calls + 1
            return SimpleNamespace(
                data=[
                    SimpleNamespace(
                        index=0,
                        embedding=[1.0] + [0.0] * (dimension - 1),
                    )
                ]
            )

    client = SimpleNamespace(embeddings=DriftingEmbeddings())
    provider = OpenAIEmbeddingProvider(batch_size=1, client=client)

    with pytest.raises(ValueError, match="consistent dimension"):
        provider.embed_texts(["first", "second"])


def test_openai_embedding_provider_requires_api_key_without_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIEmbeddingProvider()

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
        provider.embed_texts(["hello"])


def test_openai_embedding_provider_rejects_invalid_batch_size():
    with pytest.raises(ValueError, match="batch_size"):
        OpenAIEmbeddingProvider(batch_size=0)


@pytest.mark.parametrize(
    ("data", "expected_count", "message"),
    [
        (
            [
                {"index": 0, "embedding": [1.0]},
                {"index": 0, "embedding": [2.0]},
            ],
            2,
            "unique indices",
        ),
        (
            [
                {"index": 0, "embedding": [1.0]},
                {"embedding": [2.0]},
            ],
            2,
            "integer index",
        ),
        (
            [
                {"index": 0, "embedding": [1.0]},
                {"index": 2, "embedding": [2.0]},
            ],
            2,
            "indices exactly 0..1",
        ),
        ([{"index": 0, "embedding": [1.0]}], 2, "returned 1 vectors"),
        ([{"index": 0, "embedding": [float("nan")]}], 1, "finite"),
        ([{"index": 0, "embedding": [float("inf")]}], 1, "finite"),
        ([{"index": 0, "embedding": ["1.0"]}], 1, "real numeric"),
        ([{"index": 0, "embedding": [True]}], 1, "real numeric"),
        (
            [
                {"index": 0, "embedding": [1.0, 2.0]},
                {"index": 1, "embedding": [3.0]},
            ],
            2,
            "consistent dimension",
        ),
        ([{"index": 0, "embedding": []}], 1, "positive dimension"),
        ([{"index": 0, "embedding": [0.0, 0.0]}], 1, "nonzero"),
    ],
)
def test_openai_embedding_response_rejects_malformed_batches(
    data,
    expected_count: int,
    message: str,
) -> None:
    """Raw provider batches reject malformed indices and vector values."""
    with pytest.raises(ValueError, match=message):
        _extract_embedding_vectors({"data": data}, expected_count=expected_count)


def test_openai_embedding_response_reorders_only_after_index_validation() -> None:
    response = {
        "data": [
            {"index": 1, "embedding": [0.0, 2.0]},
            {"index": 0, "embedding": [1.0, 0.0]},
        ]
    }

    assert _extract_embedding_vectors(response, expected_count=2) == [
        [1.0, 0.0],
        [0.0, 2.0],
    ]


def test_injected_embedding_vectors_use_the_same_batch_validation() -> None:
    with pytest.raises(ValueError, match="embedding provider.*nonzero"):
        embedding_providers.validate_embedding_vectors(
            [[0.0, 0.0], [1.0, 0.0]],
            expected_count=2,
            source="embedding provider",
        )
