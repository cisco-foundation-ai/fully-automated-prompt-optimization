<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate Wikipedia search queries to find missing evidence for a multi-hop claim. Output exactly 3 search queries, one per line. Each query should be a specific entity name or Wikipedia article title (2-5 words). Do NOT output explanations, numbering, or anything else — just the 3 queries, one per line.

User: Claim: ${claim}

Analysis from first retrieval:
${steps.summarize_hop1.output}

Output 3 search queries (one per line) targeting the entities listed under STILL NEEDED above. Each query should be a likely Wikipedia article title.
