<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are helping verify a multi-hop claim by finding relevant Wikipedia articles via keyword search. Analyze new passages given prior context and identify articles still needed.

User: Claim: ${claim}

Prior analysis: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

First, in 2-3 sentences state what new information these passages provide and what specific connection in the claim remains unverified.

Then list up to 15 specific Wikipedia article titles mentioned or strongly implied by the new passages that have NOT already been retrieved and could help verify the remaining claim. Prioritize the specific entity that would complete the chain of evidence. List each on its own line as:
ENTITY: <exact Wikipedia article title>
