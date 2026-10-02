<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant. Given a claim and retrieved information, identify one person, place, event, or work mentioned in the claim that does NOT appear in the titles already found. Output ONLY that name as a search query.

User: Claim: ${claim}

Retrieved so far: ${steps.summarize_hop1.output}

Rules:
- Output exactly one entity name (1-5 words)
- It must be something referenced in the claim
- It must NOT already appear in the TITLES FOUND above
- Prefer proper nouns (person names, place names, work titles)

Search query:
