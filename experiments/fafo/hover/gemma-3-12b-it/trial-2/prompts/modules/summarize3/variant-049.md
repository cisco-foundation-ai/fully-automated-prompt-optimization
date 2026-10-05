<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are analyzing retrieved passages to verify a claim. This is hop 3 — identify what's still missing for the FINAL recovery search.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop3.output}

Previous findings:
- Hop 1: ${steps.summarize_hop1.output}
- Hop 2: ${steps.summarize_hop2.output}

Respond in this exact format:
FOUND: [List ALL Wikipedia article titles found across ALL hops that are relevant to the claim]
STILL MISSING: [The specific entity from the claim whose Wikipedia article has NOT been retrieved in any hop — name it precisely]
CLUES: [Combine ALL clues from every hop: alternative names, spellings, translations, related works, associated people, dates, or cross-references that could help locate the missing article. Include any clue from hops 1 and 2 that is still relevant, plus new clues from hop 3 passages.]
NEXT TARGET: [The single best search term for the missing article. Prefer alternative names or spellings from CLUES over the obvious entity name which has already failed.]
