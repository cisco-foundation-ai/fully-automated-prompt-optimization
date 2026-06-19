<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You check which claim entities have their own Wikipedia article retrieved. Look ONLY at the title before the "|" in each passage — if an entity has a passage titled with its name, it is found. If it is only mentioned inside another article's text, it is NOT found.

User: Claim: ${claim}

Prior findings: ${steps.summarize_hop1.output}

New passages:
${steps.retrieve_hop2_trunc.output}

Combining all passages retrieved so far, which entities from the claim now have their own article title found? Which are still MISSING?

NEXT SEARCH: the most important MISSING entity to search for next.
