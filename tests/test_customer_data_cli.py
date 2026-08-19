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
