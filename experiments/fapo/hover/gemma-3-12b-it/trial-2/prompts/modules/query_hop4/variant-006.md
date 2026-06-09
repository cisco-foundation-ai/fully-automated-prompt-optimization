<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a final BM25 search query to find the last missing Wikipedia article for claim verification. The query will be used for keyword-based retrieval, so use specific entity names and distinctive terms. Do NOT output "N/A" or refuse — always generate a query.

User: Claim: ${claim}

What we found so far: ${steps.summarize_hop3.output}

Generate a short, specific search query (3-8 words) targeting the entity or topic from the claim that is STILL MISSING. Use the exact name as it would appear as a Wikipedia article title. If all entities seem found, try an alternative name or related concept.
