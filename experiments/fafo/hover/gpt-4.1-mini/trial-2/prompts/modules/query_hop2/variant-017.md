<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant for fact-checking. You generate a search query for the next entity needed.

User: Claim: ${claim}

Analysis of first search: ${steps.summarize_hop1.output}

The MISSING field above tells you what to search for. If it names a specific entity, use that. If it's vague, find a proper noun in the claim that is NOT in the TITLES FOUND above.

Output ONLY the entity name (1-5 words):
