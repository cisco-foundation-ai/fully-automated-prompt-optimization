<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You check which claim entities have their own Wikipedia article retrieved. An entity is FOUND only if a passage title (the text before "|") exactly matches that entity's article name. Being mentioned in passage text does NOT count.

User: Claim: ${claim}

Passages (format: [N] «Title | text»):
${steps.retrieve_hop1_trunc.output}

List each entity/person/place from the claim. Mark FOUND only if its Wikipedia article title appears before a "|" above. Mark MISSING otherwise.

NEXT SEARCH: the single most important MISSING entity. If the claim refers to someone indirectly (e.g. "the director of X"), try to identify who that is from the passage text and search for them by name.
