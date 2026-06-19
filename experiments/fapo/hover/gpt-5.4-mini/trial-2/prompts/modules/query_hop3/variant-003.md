<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate search queries for multi-hop Wikipedia claim verification. Your query should retrieve the Wikipedia article for the most important entity that hasn't been found yet.

User: Claim: ${claim}

Analysis from retrievals so far:
${steps.summarize_hop2.output}

Instructions:
1. From the "STILL MISSING" list, pick the single most important entity to search for.
2. If a proper name was extracted from passages that resolves an indirect claim reference, prioritize it.
3. If the claim mentions a relationship or property that needs its own article for verification, search for that.

Output ONLY the search query — the entity's proper name, with a disambiguator in parentheses if needed. No explanation.
