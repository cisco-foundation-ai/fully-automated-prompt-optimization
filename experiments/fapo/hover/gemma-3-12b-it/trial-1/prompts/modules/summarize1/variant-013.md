<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify which entities from a claim have their own dedicated article retrieved.

User: Claim: ${claim}

Passages (each line: [N] «ArticleTitle | text»):
${steps.retrieve_hop1_trunc.output}

Task: For each entity in the claim, check if there is a passage whose ArticleTitle matches that entity. Entities only mentioned in passage text but without their own titled article are NOT yet found.

Which entities have their own article title above? Which are still missing their own article?

NEXT SEARCH: output the name of one entity that is mentioned in passage text but does NOT have its own article title above. If the claim refers to someone indirectly (e.g. "the director of X"), look in the passage text for that person's actual name.
