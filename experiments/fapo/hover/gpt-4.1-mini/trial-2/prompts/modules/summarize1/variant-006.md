<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract relevant information from Wikipedia search results to help verify a multi-hop claim.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

From the passages above, identify which articles are relevant to the claim.

RELEVANT TITLES: [only titles of articles that contain information about the claim, comma-separated]
FACTS: [key facts from relevant articles that help verify the claim, 1-3 sentences]
MISSING: [one specific person, place, work, or event referenced in the claim that was NOT found in any passage]
