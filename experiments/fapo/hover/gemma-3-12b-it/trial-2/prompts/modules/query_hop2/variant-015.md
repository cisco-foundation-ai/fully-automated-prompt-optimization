<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a short BM25 search query to find a Wikipedia article. Output ONLY the query (3-8 words), nothing else.

User: Claim: ${claim}

Analysis: ${steps.summarize_hop1.output}

Look at NEXT TARGET above. Generate a search query using that entity's Wikipedia article title. Use proper nouns exactly as they'd appear on Wikipedia.
