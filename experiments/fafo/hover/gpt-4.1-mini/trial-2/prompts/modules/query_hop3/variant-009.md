<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant. Carefully compare the claim to what has been found. Identify one proper noun from the claim (person, place, film, album, event, organization) that is NOT in any TITLES list. Output ONLY that name.

User: Claim: ${claim}

Hop 1 results: ${steps.summarize_hop1.output}
Hop 2 results: ${steps.summarize_hop2.output}

What proper noun from the claim is still missing from the titles found? Output only the entity name (1-5 words):
