<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are helping verify a multi-hop claim by finding relevant Wikipedia articles via keyword search. Analyze new passages given prior context and identify articles still needed.

User: Claim: ${claim}

Prior analysis: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Based on all the passages retrieved so far, identify which parts of the claim still lack direct Wikipedia article evidence. Then list entities that could fill those gaps.

Instructions:
1. In 2-3 sentences, state what connections in the claim remain unverified.
2. For each unverified connection, think about what specific Wikipedia article would confirm it. List each on its own line as:
ENTITY: <exact Wikipedia article title>

Focus on entities that are MENTIONED or DESCRIBED in the passages but may not have been directly retrieved yet. If a passage describes something (like "the company that acquired X") without naming it, provide the actual name if you know it.
