<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify which entities from a claim appear in retrieved passages, including entities described indirectly.

User: Claim: ${claim}

Passages:
${steps.retrieve_hop1_trunc.output}

Instructions:
1. List entities/topics from the claim FOUND in passages (with their actual names from the passages)
2. List entities/topics MISSING (not yet found)
3. For any entity described indirectly in the claim (e.g. "the director of X", "the band that released Y"), check if the passages reveal the actual name. If so, include it in your found list.

Be brief.

NEXT SEARCH: output the exact name of a person, place, or thing that needs its own Wikipedia article found. Prefer entities whose actual name you identified from the passages but whose dedicated article is not yet retrieved.
