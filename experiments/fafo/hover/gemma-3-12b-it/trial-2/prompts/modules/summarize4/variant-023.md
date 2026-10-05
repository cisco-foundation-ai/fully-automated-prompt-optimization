<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are analyzing retrieved passages to verify a claim. This is hop 4 — determine if the recovery search found the missing article, and if not, prepare for one final attempt.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop4.output}

Previous findings:
- Hop 1: ${steps.summarize_hop1.output}
- Hop 2: ${steps.summarize_hop2.output}
- Hop 3: ${steps.summarize_hop3.output}

Respond in this exact format:
FOUND: [List ALL Wikipedia article titles found across ALL hops that are relevant to the claim]
STILL MISSING: [The specific entity from the claim whose Wikipedia article has NOT been retrieved in any hop — or "NONE" if all entities are found]
CLUES: [Any new names, dates, or details from hop 4 passages that could help locate the missing article — focus on alternative spellings, related works, associated people that haven't been tried]
FAILED APPROACHES: [Summarize what query strategies have already been tried and failed]
NEXT TARGET: [A completely different search angle to try — use descriptive keywords, broader categories, or related entities instead of the entity name itself]
