<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are analyzing retrieved Wikipedia passages to identify entities still needed to verify a multi-hop claim. Focus on what is STILL MISSING after two rounds of retrieval.

User: Claim: ${claim}

Prior analysis: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Analyze the new passages combined with prior knowledge. Output exactly this format:

FOUND ENTITIES: [list ALL specific Wikipedia article titles found across BOTH retrieval rounds that are relevant to the claim]
KEY FACTS: [2-3 new crucial facts from these passages]
STILL NEEDED: [list specific entity names or Wikipedia article titles that the claim references but have NOT been found in either retrieval round — if none, write "None"]
