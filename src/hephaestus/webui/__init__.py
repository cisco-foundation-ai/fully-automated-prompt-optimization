# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Local web UI for browsing tenant eval runs, iterations, prompts, and outputs."""

from src.hephaestus.webui.server import serve

__all__ = ["serve"]
