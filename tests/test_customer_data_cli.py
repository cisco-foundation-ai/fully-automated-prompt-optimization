# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from src.hephaestus.cli import build_parser


def test_parser_accepts_customer_data_push():
    parser = build_parser()
    args = parser.parse_args(
        [
            "customer-data",
            "push",
            "--tenant",
            "demo",
            "--scope",
            "raw",
            "--force",
        ]
    )
    assert args.command == "customer-data"
    assert args.customer_data_command == "push"
    assert args.force is True


def test_parser_push_force_defaults_false():
    parser = build_parser()
    args = parser.parse_args(
        [
            "customer-data",
            "push",
            "--tenant",
            "demo",
        ]
    )
    assert args.force is False


def test_parser_accepts_assets_intent_inventory():
    parser = build_parser()
    args = parser.parse_args(
        [
            "assets",
            "intent-inventory",
            "--records",
            "records.jsonl",
            "--trusted-intents",
            "trusted.jsonl",
            "--output-dir",
            "out",
            "--id-field",
            "record_id",
            "--text-field",
            "canonical_intent_text",
            "--text-field",
            "tool_summary",
            "--vectorizer",
            "openai",
            "--embedding-model",
            "custom-embedding",
            "--embedding-batch-size",
            "64",
            "--embedding-timeout-seconds",
            "30",
            "--embedding-max-retries",
            "4",
            "--embedding-retry-backoff-seconds",
            "3",
            "--min-trusted-examples",
            "3",
            "--min-trusted-groups",
            "2",
            "--large-cluster-size",
            "50",
            "--min-trusted-examples-for-large-cluster",
            "5",
            "--max-unlabeled-to-trusted-ratio",
            "20",
        ]
    )
    assert args.command == "assets"
    assert args.assets_command == "intent-inventory"
    assert args.text_field == ["canonical_intent_text", "tool_summary"]
    assert args.vectorizer == "openai"
    assert args.embedding_model == "custom-embedding"
    assert args.embedding_batch_size == 64
    assert args.embedding_timeout_seconds == 30
    assert args.embedding_max_retries == 4
    assert args.embedding_retry_backoff_seconds == 3
    assert args.min_trusted_examples == 3
    assert args.min_trusted_groups == 2
    assert args.large_cluster_size == 50
    assert args.min_trusted_examples_for_large_cluster == 5
    assert args.max_unlabeled_to_trusted_ratio == 20


def test_parser_assets_intent_inventory_defaults_to_openai_vectorizer():
    parser = build_parser()
    args = parser.parse_args(
        [
            "assets",
            "intent-inventory",
            "--records",
            "records.jsonl",
            "--trusted-intents",
            "trusted.jsonl",
            "--output-dir",
            "out",
            "--id-field",
            "record_id",
            "--text-field",
            "canonical_intent_text",
        ]
    )
    assert args.vectorizer == "openai"


def test_parser_accepts_assets_assemble():
    parser = build_parser()
    args = parser.parse_args(
        [
            "assets",
            "assemble",
            "--trusted-cases",
            "trusted.jsonl",
            "--synthetic-cases",
            "synthetic.jsonl",
            "--output-dir",
            "out",
            "--dataset-version",
            "v1",
        ]
    )
    assert args.command == "assets"
    assert args.assets_command == "assemble"
    assert args.dataset_version == "v1"
