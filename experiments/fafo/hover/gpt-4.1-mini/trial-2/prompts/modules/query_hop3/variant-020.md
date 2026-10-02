<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant finding the LAST missing article for multi-hop claim verification.

User: Claim: ${claim}

What we found so far:
${steps.summarize_hop2.output}

The claim mentions or implies entities that need their own Wikipedia articles. Two articles have been found. You need the THIRD.

Think about what the claim is really asking:
- Does the claim reference someone by description rather than name? (e.g., "the star of X" — look in the facts above for who that is)
- Does the claim reference a specific event, place, or work that hasn't been found?
- Is there a category or concept that links the claim's entities?

Output ONLY the missing entity name to search (1-5 words):
