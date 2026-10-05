<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are analyzing retrieved Wikipedia passages to help verify a claim. Extract key facts and identify what still needs to be found.

User: Claim: ${claim}

Previous analysis: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Respond in this exact format:
FOUND: [List ALL relevant Wikipedia article titles found across both rounds]
MENTIONED: [List specific names discovered in passages that connect to unverified parts of the claim — especially people, works, or events whose own Wikipedia articles haven't been found yet]
NEXT TARGET: [The most important entity name still needed — prefer a specific proper noun discovered in the passages rather than a vague description from the claim]
