# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Build evaluation datasets from agent traces and feedback.

Plain code prepares the inputs and publishes the cases. Between them run
three model steps:

1. observe: extract lessons, with verbatim evidence, from train episodes.
2. synthesize: group the lessons into a guideline catalog for each route.
3. rubric: write a rubric for every episode from the catalog.
"""
