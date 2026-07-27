# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.hephaestus.datasets.embedding_providers import OpenAIEmbeddingProvider


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


def test_openai_embedding_provider_requires_api_key_without_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIEmbeddingProvider()

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
        provider.embed_texts(["hello"])


def test_openai_embedding_provider_rejects_invalid_batch_size():
    with pytest.raises(ValueError, match="batch_size"):
        OpenAIEmbeddingProvider(batch_size=0)
