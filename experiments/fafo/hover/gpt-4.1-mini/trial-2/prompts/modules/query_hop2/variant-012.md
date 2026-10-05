<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant. Use the MISSING entity identified below as your search query, unless you can identify a better entity from the claim. Output 1-5 words only.

User: Claim: ${claim}

Analysis: ${steps.summarize_hop1.output}

The analysis identifies a MISSING entity above. If that entity name would make a good Wikipedia search query, output it. Otherwise, find another entity from the claim not in TITLES FOUND.

Search query (1-5 words):
