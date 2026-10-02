<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are analyzing retrieved passages to verify a claim. Extract structured information about what was found.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

IMPORTANT: Each passage has a TITLE shown as [N] «Title | ...». Only count an entity as FOUND if it appears as a passage TITLE. If an entity is merely mentioned inside another article's body text, it has NOT been found — it still needs its own article retrieved.

Respond in this exact format:
FOUND: [List ONLY the passage titles (from «Title | ...» markers) that are directly relevant to the claim]
MENTIONED: [List entity names from the claim that appear in passage body text but do NOT have their own article retrieved yet — these still need searching]
NEXT TARGET: [The most important entity from MENTIONED that needs to be searched next]
