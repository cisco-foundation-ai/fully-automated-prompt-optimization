<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a Wikipedia search query for the FINAL hop of multi-hop claim verification. Two searches have been done. You must find the ONE remaining entity.

User: Claim: ${claim}

Search history:
${steps.summarize_hop2.output}

Your task:
1. Read the claim carefully. Identify EVERY proper noun (person, place, film, song, band, event, organization).
2. Compare each proper noun against ALL TITLES listed above.
3. If a proper noun from the claim is NOT in the titles, output that exact name.
4. If all named entities ARE found, look at the passages for an indirect reference (e.g., "the director of X" — the passages may reveal the actual name).
5. NEVER output "none" — there is always one more entity to find.
6. NEVER repeat a title that was already found.

Output ONLY the entity name (1-5 words):
