<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are helping verify a multi-hop claim by finding all relevant Wikipedia articles. Your task is to analyze new passages (given prior knowledge) and identify entities that have not been retrieved yet.

User: Claim: ${claim}

Prior knowledge: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Instructions:
1. First, briefly state what new facts from these passages are relevant to the claim and what evidence is still missing (2-3 sentences).
2. Then, list Wikipedia article titles that are referenced or implied by the new passages and are NOT among the articles already retrieved. Focus on the specific entity that would complete the verification chain. List each on its own line prefixed with "ENTITY:" using the exact Wikipedia article title format.

Focus especially on: the final missing link — the specific person, event, work, or place that would connect all parts of the claim together.
