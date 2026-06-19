<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Extract proper nouns from passages that could be Wikipedia article titles. Focus on names related to the claim.

User: Claim: ${claim}

Passages retrieved so far:
${steps.retrieve_hop1.output}

${steps.retrieve_hop2.output}

The claim mentions entities that need their own Wikipedia articles. Scan the passage text above and list every proper noun (person, place, film, book, organization, event, species) that:
1. Appears in the passage TEXT (not just as a passage title)
2. Relates to the claim
3. Could be its own Wikipedia article

Output just the names, one per line. Maximum 10 names.
