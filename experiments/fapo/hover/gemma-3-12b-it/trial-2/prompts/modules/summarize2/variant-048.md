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
STILL MISSING: [The specific entity from the claim whose Wikipedia article has NOT been retrieved yet — name it precisely]
CLUES: [Combine clues from BOTH hops: any names, dates, alternative spellings, related works, associated people, or cross-references in the passages that could help locate the missing article. Include clues from hop 1 that are still relevant.]
NEXT TARGET: [The single best search term to try next. If previous CLUES mention an alternative name or spelling for the missing entity, use that. Otherwise use the entity name from the claim combined with a distinguishing keyword.]
