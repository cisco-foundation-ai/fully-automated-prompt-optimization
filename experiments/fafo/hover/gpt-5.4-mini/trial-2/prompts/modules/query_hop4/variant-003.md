<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate search queries for multi-hop Wikipedia claim verification. This is your LAST standard search opportunity before rescue. Choose carefully.

User: Claim: ${claim}

Analysis from retrievals so far:
${steps.summarize_hop3.output}

Instructions:
1. From the "STILL MISSING" list, pick the single most important entity whose Wikipedia article is needed.
2. Prioritize proper names that were extracted from previously retrieved passages (they are more likely to be exact Wikipedia titles).
3. If all explicitly named entities are found, search for a bridging entity that the claim references indirectly.

Output ONLY the search query — the entity's proper name, with a disambiguator in parentheses if needed. No explanation.
