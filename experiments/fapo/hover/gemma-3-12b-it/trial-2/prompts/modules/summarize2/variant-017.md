<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are analyzing retrieved Wikipedia passages to help verify a claim. Extract key facts and identify what still needs to be found.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop2.output}

Previous findings from hop 1:
- ${steps.summarize_hop1.output}

Respond in this exact format:
FOUND: [List ALL Wikipedia article titles found across both hops that are relevant to the claim]
STILL MISSING: [The specific entity from the claim whose Wikipedia article has NOT been retrieved yet]
CLUES: [Any names, dates, or details from the passages that could help locate the missing article — alternative names, related works, associated people]
NEXT TARGET: [The exact search term to try next, informed by the CLUES above]
