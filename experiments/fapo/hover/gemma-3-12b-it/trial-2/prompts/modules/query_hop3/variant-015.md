<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a short BM25 search query to find a Wikipedia article. Output ONLY the query (3-8 words), nothing else.

User: Claim: ${claim}

Analysis: ${steps.summarize_hop2.output}

Previous query that did NOT find the target: ${steps.query_hop2.output}

Look at NEXT TARGET above. Generate a DIFFERENT search query for that entity. Try an alternative name, a longer form, or include a disambiguation term like "(film)" or "(musician)".
