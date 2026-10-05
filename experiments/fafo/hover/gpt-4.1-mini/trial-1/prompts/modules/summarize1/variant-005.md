<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are helping verify a multi-hop claim by finding relevant Wikipedia articles via keyword search. Your job is to identify which Wikipedia articles mentioned in the passages would help verify parts of the claim that aren't yet confirmed.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

First, in 2-3 sentences state what the passages tell us about the claim and what connections are still unverified.

Then list up to 15 specific Wikipedia article titles that are mentioned or strongly implied by the passages and could help verify the remaining parts of the claim. These should be articles NOT already among the retrieved passages above. Prioritize entities that connect different parts of the claim. List each on its own line as:
ENTITY: <exact Wikipedia article title>
