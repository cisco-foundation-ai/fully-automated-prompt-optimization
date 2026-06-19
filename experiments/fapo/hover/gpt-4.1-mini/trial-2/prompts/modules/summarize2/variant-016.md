<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract article titles and relevant facts from Wikipedia search results to support multi-hop claim verification.

User: Claim: ${claim}

What was found in hop 1: ${steps.summarize_hop1.output}

New retrieved passages (hop 2):
${steps.retrieve_hop2.output}

Carefully scan ALL passages from both hops and extract:

TITLES FOUND: [list EVERY unique Wikipedia article title from hop 1 AND hop 2 — do not skip any]
KEY FACTS: [2-3 sentences of facts directly relevant to verifying the claim, especially about relationships between entities]
MISSING: [the exact proper noun from the claim that does NOT appear as a title above — must be a real name, not a description. Write "none" if all claim entities are covered]
