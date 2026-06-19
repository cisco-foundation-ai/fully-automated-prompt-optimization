<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract information from retrieved passages to help verify a claim.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

From the passages above, extract:
1. All proper nouns (people, places, organizations, titles of works) mentioned in the passages.
2. Which proper nouns from the claim appear in the passages.
3. Which proper nouns from the claim do NOT appear in any passage.

Be brief. Preserve all names exactly.
