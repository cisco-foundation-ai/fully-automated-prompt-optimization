<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a BM25 search query. Output ONLY the query (3-8 words), nothing else.

User: Claim: ${claim}

Analysis: ${steps.summarize_hop2.output}

Previous query: ${steps.query_hop2.output}

Generate a DIFFERENT search query for the NEXT TARGET above. If the previous query didn't work, try:
- The entity's full proper name
- Adding a disambiguation term like "(film)", "(song)", "(politician)"
- A related but more specific term found in MENTIONED
