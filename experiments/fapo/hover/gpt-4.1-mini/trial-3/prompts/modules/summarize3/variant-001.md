<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are analyzing retrieved Wikipedia passages after three rounds of retrieval for claim verification. Identify what entities are STILL missing.

User: Claim: ${claim}

Prior analyses:
First: ${steps.summarize_hop1.output}
Second: ${steps.summarize_hop2.output}

Third retrieval passages:
${steps.retrieve_hop3.output}

Output in this exact format:

FOUND ENTITIES: [list ALL Wikipedia article titles found across all three retrieval rounds that are relevant to the claim]
KEY FACTS: [1-2 new facts from this round]
STILL NEEDED: [list any specific entity names from the claim that have NOT been found — write "None" only if all are found]
