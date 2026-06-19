<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a BM25 search query. Output ONLY the query (3-8 words), nothing else.

User: Claim: ${claim}

Analysis: ${steps.summarize_hop1.output}

Generate a search query for the NEXT TARGET above. Use the exact entity name as it would appear as a Wikipedia article title.
