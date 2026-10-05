<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are analyzing retrieved Wikipedia passages to help verify a claim. Extract key facts and identify what still needs to be found.

User: Claim: ${claim}

Previous analysis: ${steps.summarize_hop2.output}

New retrieved passages:
${steps.retrieve_hop3.output}

Respond in this exact format:
FOUND: [List ALL relevant Wikipedia article titles found across all rounds]
MENTIONED: [List any remaining specific names from passages that could be the missing link for verifying the claim]
NEXT TARGET: [The specific entity name still needed to complete verification — use exact proper nouns found in passages if possible, or try alternative phrasings of entities from the claim]
