<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant. Given a claim and two rounds of retrieved information, identify one entity from the claim that has NOT been found yet. Output ONLY that entity name.

User: Claim: ${claim}

Hop 1 findings: ${steps.summarize_hop1.output}

Hop 2 findings: ${steps.summarize_hop2.output}

Previously searched: "${steps.query_hop2.output}"

Instructions:
- Find a proper noun (person, place, film, song, organization, event) from the claim that does NOT appear in any TITLES list above and is DIFFERENT from the previous search.
- If the claim describes the entity indirectly, use the retrieved information to determine its actual name.
- Output ONLY the entity name (1-5 words). No explanations, no placeholder text, no variable names.

Entity name:
