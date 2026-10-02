<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify which entities from a claim appear in retrieved passages, including entities described indirectly.

User: Claim: ${claim}

Prior findings: ${steps.summarize_hop2.output}

New passages:
${steps.retrieve_hop3_trunc.output}

Instructions:
1. List entities/topics from the claim NOW FOUND (with actual names from passages)
2. List entities/topics STILL MISSING
3. For any entity described indirectly in the claim (e.g. "the director of X", "the band that released Y"), check if the passages reveal the actual name. If so, include it in your found list.

Be brief.

NEXT SEARCH: output the exact name of a person, place, or thing that still needs to be found. Prefer entities whose actual name you identified from the passages but whose dedicated article is not yet retrieved.
