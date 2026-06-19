<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You find Wikipedia article titles mentioned in passages that relate to a claim.

User: Claim: ${claim}

Passages:
${steps.retrieve_hop1.output}

${steps.retrieve_hop2.output}

Read the claim carefully. Identify what entity the claim is about that you have NOT yet found a Wikipedia article for. Then scan the passages above for that entity's name.

Output ONLY names that could help verify the claim. One name per line. Maximum 8 names, ranked by relevance to the claim.
