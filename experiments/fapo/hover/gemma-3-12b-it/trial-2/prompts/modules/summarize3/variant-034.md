<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are analyzing retrieved passages to verify a claim. This is hop 3 — identify what's still missing for the recovery search.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop3.output}

Previous findings:
- Hop 1: ${steps.summarize_hop1.output}
- Hop 2: ${steps.summarize_hop2.output}

Queries used so far:
- Query 2: ${steps.query_hop2.output}
- Query 3: ${steps.query_hop3.output}

Respond in this exact format:
FOUND: [List ALL Wikipedia article titles found across ALL hops that are relevant to the claim]
STILL MISSING: [The specific entity from the claim whose Wikipedia article has NOT been retrieved in any hop]
CLUES: [Alternative names, related works, associated people, dates, or details that could help find the missing entity]
FAILED APPROACHES: [Briefly note what search strategies have already been tried and failed]
NEXT TARGET: [The exact search term to try next — must be DIFFERENT from all previous queries]
