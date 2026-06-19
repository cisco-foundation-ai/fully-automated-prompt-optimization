<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate search queries for multi-hop Wikipedia claim verification. Your query should retrieve the Wikipedia article for the most important entity that hasn't been found yet.

User: Claim: ${claim}

Analysis from first retrieval:
${steps.summarize_hop1.output}

Instructions:
1. From the analysis above, identify entities marked NOT FOUND.
2. Also check the "PROPER NAMES FROM PASSAGES" — if any of those names match indirect references in the claim (e.g., the person who is "the star of X"), that name is high priority.
3. Pick the single most important entity to search for next. Priority order:
   a. A proper name resolved from an indirect reference in the claim (highest value)
   b. An explicitly named entity in the claim that hasn't been found
   c. A bridging entity that connects two found entities

Output ONLY the search query — the entity's proper name, with a disambiguator in parentheses if needed (e.g., "Safelight (film)"). No explanation.
