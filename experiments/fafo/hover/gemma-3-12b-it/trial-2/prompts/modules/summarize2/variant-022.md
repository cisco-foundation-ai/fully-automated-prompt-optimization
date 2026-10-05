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

IMPORTANT: Each passage has a TITLE shown as [N] «Title | ...». Only count an entity as FOUND if it appears as a passage TITLE. If an entity is merely mentioned inside another article's body text, it has NOT been found — its own dedicated article must still be retrieved.

Respond in this exact format:
FOUND: [List ALL passage titles found across both hops that are relevant to the claim — ONLY titles from «Title | ...» markers]
STILL MISSING: [The specific entity from the claim whose dedicated Wikipedia article has NOT been retrieved yet — even if it was mentioned inside another article's body]
CLUES: [Any names, dates, or details from the passages that could help locate the missing article — alternative names, related works, associated people]
NEXT TARGET: [The exact search term to try next, informed by the CLUES above]
