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

IMPORTANT: Each passage has a TITLE shown as [N] «Title | ...». Only count an entity as FOUND if it appears as a passage TITLE. If an entity is merely mentioned inside another article's body text, it has NOT been found — its own dedicated article must still be retrieved via search.

Respond in this exact format:
FOUND: [List ALL passage titles found across ALL hops that are relevant to the claim — ONLY titles from «Title | ...» markers]
STILL MISSING: [The specific entity from the claim whose dedicated Wikipedia article has NOT been retrieved in any hop — even if mentioned in body text]
CLUES: [Any names, dates, or details from the passages that could help locate the missing article — alternative names, related works, associated people]
NEXT TARGET: [The exact search term to try next, informed by the CLUES above]
