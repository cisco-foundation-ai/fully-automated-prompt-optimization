<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output a Wikipedia search query for the missing entity. Use the exact name that would be a Wikipedia article title. Do NOT search for anything already in TITLES.

User: Claim: ${claim}

Found so far: ${steps.summarize_hop1.output}

Wikipedia article title to search (1-5 words):
