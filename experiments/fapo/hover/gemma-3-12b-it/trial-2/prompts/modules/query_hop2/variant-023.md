<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a BM25 search query to find a Wikipedia article. Output ONLY the query (3-8 words), nothing else.

User: Claim: ${claim}

Hop 1 analysis: ${steps.summarize_hop1.output}

Generate a search query for the entity named in NEXT TARGET above. Use the exact entity name as it would appear as a Wikipedia article title. If NEXT TARGET seems vague, extract the most specific proper noun from the claim that hasn't been found yet.

Output only the search query.
