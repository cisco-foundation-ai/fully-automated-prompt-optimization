<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You check which claim entities have their own Wikipedia article retrieved. Look ONLY at the title before the "|" in each passage — if an entity has a passage titled with its name, it is found. If it is only mentioned inside another article's text, it is NOT found.

User: Claim: ${claim}

Passages:
${steps.retrieve_hop1_trunc.output}

List entities from the claim. For each, state whether its own article title appears (FOUND) or not (MISSING).

NEXT SEARCH: the most important MISSING entity to search for next.
